# ==========================================
# Smart Lab Management System
# Client Agent - Hardened WebSocket Client (Phase 7)
# ==========================================

from __future__ import annotations

import collections
import concurrent.futures
from enum import Enum
import json
import logging
import random
import threading
import time
from typing import Any, Callable

import requests
import websocket

from config import (
    WS_PING_INTERVAL_SECONDS,
    WS_RECONNECT_BASE_DELAY,
    WS_RECONNECT_JITTER_RATIO,
    WS_RECONNECT_MAX_DELAY,
    get_api_base_url,
    get_ws_base_url,
)
from core.logger import logger
from core.outbox.models import OutboxPriority
from core.security import (
    build_websocket_endpoint,
    build_websocket_headers,
    create_secure_session,
    get_ca_bundle_path,
)
from server.command_handler import execute_command


# ==========================================
# Observable WebSocket States (G-06)
# ==========================================

class WebSocketState(str, Enum):
    """
    Explicit observable states for the client agent WebSocket lifecycle.
    """
    DISCONNECTED = "DISCONNECTED"      # Initial state or socket disconnected
    CONNECTING = "CONNECTING"          # Resolving endpoint and establishing TCP handshake
    AUTHENTICATING = "AUTHENTICATING"  # Building headers and verifying credentials
    CONNECTED = "CONNECTED"            # WebSocket handshake successful, client online
    RECONNECTING = "RECONNECTING"      # Connection lost, waiting out backoff delay
    AUTH_FAILED = "AUTH_FAILED"        # Authentication rejected (4001/4003) or token invalid
    CLOSING = "CLOSING"                # Graceful termination in progress
    STOPPED = "STOPPED"                # Worker thread terminated cleanly


def compute_jittered_delay(delay: float, jitter_ratio: float = 0.15) -> float:
    """
    Apply bounded symmetric random jitter to a reconnect delay (G-03).
    Formula: delay * (1 + uniform(-jitter_ratio, jitter_ratio)).
    Guarantees sleep >= 0.1 seconds.
    """
    ratio = max(0.0, min(0.5, jitter_ratio))
    jitter = random.uniform(-ratio, ratio) * delay
    return max(0.1, delay + jitter)


# ==========================================
# Hardened WebSocket Client Manager
# ==========================================

class AgentWebSocketClient:
    """
    Manages the persistent WebSocket connection between the client agent and SLMS server.

    Responsibilities:
    - G-03: Reconnect backoff with reset-on-success, bounded jitter, and interruptible wait.
    - G-04: Token lifecycle coordination, refresh on 4001 auth failure, and de-enrollment detection.
    - G-05: Decoupled command execution, client-side deduplication, and durable outbox enqueue.
    - G-06: Thread-safe observable state model with callbacks and diagnostic inspection.
    - Heartbeat: Single managed ping loop tied strictly to connection lifecycle.
    - G-01/G-02: Strict WSS/TLS transport and header-based Bearer authentication (no query tokens).
    """

    def __init__(
        self,
        computer_id: int,
        get_token: Callable[[], str],
        refresh_token: Callable[[], str] | None = None,
        outbox: Any | None = None,
        is_enrolled: Callable[[], bool] | None = None,
        on_state_change: Callable[[WebSocketState, WebSocketState], None] | None = None,
        base_delay: float = WS_RECONNECT_BASE_DELAY,
        max_delay: float = WS_RECONNECT_MAX_DELAY,
        jitter_ratio: float = WS_RECONNECT_JITTER_RATIO,
        ping_interval: float = WS_PING_INTERVAL_SECONDS,
    ):
        self.computer_id = computer_id
        self.get_token = get_token
        self.refresh_token = refresh_token
        self.outbox = outbox
        self.is_enrolled = is_enrolled
        self.on_state_change = on_state_change

        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_ratio = jitter_ratio
        self.ping_interval = ping_interval

        # State model (G-06)
        self._state = WebSocketState.DISCONNECTED
        self._state_lock = threading.RLock()

        # Reconnect state (G-03) - owned by instance
        self._current_delay = self.base_delay

        # Core thread and stop coordination
        self._ws_app: websocket.WebSocketApp | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        # Heartbeat loop management (single instance)
        self._ping_stop_event = threading.Event()
        self._ping_thread: threading.Thread | None = None
        self._ping_lock = threading.Lock()

        # Command execution decoupling (G-05)
        self._command_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="SLMS-CmdWorker",
        )
        self._recent_commands_lock = threading.Lock()
        self._recent_command_ids: set[int] = set()
        self._recent_commands_order: collections.deque[int] = collections.deque(maxlen=500)

    # ==========================================
    # State Inspection & Observability (G-06)
    # ==========================================

    @property
    def state(self) -> WebSocketState:
        """Observable connection state (thread-safe)."""
        with self._state_lock:
            return self._state

    @property
    def is_connected(self) -> bool:
        """True if the WebSocket is currently open and authenticated."""
        with self._state_lock:
            return self._state == WebSocketState.CONNECTED

    @property
    def current_delay(self) -> float:
        """Current reconnect backoff delay in seconds (G-03)."""
        with self._state_lock:
            return self._current_delay

    def _set_state(self, new_state: WebSocketState, reason: str = "") -> None:
        """Thread-safe state transition with logging and optional observer notification."""
        with self._state_lock:
            old_state = self._state
            if old_state == new_state:
                return

            # Prevent transition out of STOPPED unless restarting
            if old_state == WebSocketState.STOPPED and new_state != WebSocketState.CONNECTING:
                return

            self._state = new_state
            msg = f"WebSocket state changed: {old_state.value} -> {new_state.value}"
            if reason:
                msg += f" ({reason})"
            logger.info(msg)

            if self.on_state_change:
                try:
                    self.on_state_change(old_state, new_state)
                except Exception as cb_err:
                    logger.warning(f"Error in on_state_change callback: {cb_err}")

    # ==========================================
    # Lifecycle: Start & Stop
    # ==========================================

    def start(self) -> None:
        """Start the background WebSocket worker loop."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("AgentWebSocketClient is already running.")
            return

        self._stop_event.clear()
        self._set_state(WebSocketState.CONNECTING, "Starting client worker")

        self._thread = threading.Thread(
            target=self._run_forever,
            daemon=True,
            name="SLMS-WebSocket",
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal clean and immediate termination of all WebSocket operations."""
        self._set_state(WebSocketState.CLOSING, "Stop requested")
        self._stop_event.set()

        # Stop heartbeat loop immediately
        self._stop_ping_loop()

        # Close active WebSocket connection
        if self._ws_app is not None:
            try:
                self._ws_app.close()
            except Exception:
                pass

        # Terminate command executor
        try:
            self._command_executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass

        self._set_state(WebSocketState.STOPPED, "Client stopped")

    # ==========================================
    # Reconnect Loop (G-03, G-04)
    # ==========================================

    def _run_forever(self) -> None:
        """
        Main worker loop managing connection attempts, exponential backoff,
        controlled jitter, and authentication renewal.
        """
        while not self._stop_event.is_set():
            # Check de-enrollment condition (G-04)
            if self.is_enrolled and not self.is_enrolled():
                self._set_state(WebSocketState.AUTH_FAILED, "Agent is not enrolled")
                logger.warning("Agent is not enrolled; stopping WebSocket reconnect attempts.")
                break

            try:
                self._set_state(WebSocketState.CONNECTING)
                self._set_state(WebSocketState.AUTHENTICATING)

                # Acquire current access token (G-04)
                token = self.get_token() if self.get_token else ""
                if not token and self.refresh_token:
                    try:
                        logger.info("Access token missing; attempting refresh before connecting...")
                        token = self.refresh_token()
                    except Exception as ref_err:
                        logger.warning(f"Pre-connect token refresh failed: {ref_err}")
                        token = ""

                if not token:
                    self._set_state(WebSocketState.AUTH_FAILED, "No valid access token available")
                    logger.error("Cannot connect WebSocket: No access token available.")
                    sleep_dur = compute_jittered_delay(self._current_delay, self.jitter_ratio)
                    with self._state_lock:
                        self._current_delay = min(self._current_delay * 2, self.max_delay)
                    if self._stop_event.wait(timeout=sleep_dur):
                        break
                    continue

                # Build clean URL and header (G-01, G-02)
                ws_base = get_ws_base_url()
                url = build_websocket_endpoint(ws_base, self.computer_id)
                headers = build_websocket_headers(token)

                sslopt: dict[str, Any] = {}
                ca_bundle = get_ca_bundle_path()
                if ca_bundle:
                    sslopt["ca_certs"] = ca_bundle

                logger.info(f"Connecting to SLMS WebSocket at {url}...")

                self._ws_app = websocket.WebSocketApp(
                    url,
                    header=headers,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )

                # Blocks until socket disconnects or closes
                self._ws_app.run_forever(
                    ping_interval=None,
                    ping_timeout=None,
                    sslopt=sslopt if sslopt else None,
                )

                if self._stop_event.is_set():
                    break

                logger.warning("WebSocket connection ended.")

            except Exception as error:
                if self._stop_event.is_set():
                    break
                logger.exception(f"WebSocket connection attempt failed: {error}")
                self._set_state(WebSocketState.DISCONNECTED, f"Connection error: {error}")

            if self._stop_event.is_set():
                break

            # Compute backoff with jitter and advance exponential growth (G-03)
            with self._state_lock:
                curr_delay = self._current_delay
                self._current_delay = min(curr_delay * 2, self.max_delay)

            sleep_duration = compute_jittered_delay(curr_delay, self.jitter_ratio)
            self._set_state(
                WebSocketState.RECONNECTING,
                f"Backoff {sleep_duration:.1f}s (base={curr_delay:.1f}s)",
            )
            logger.info(f"Reconnecting WebSocket in {sleep_duration:.1f} seconds...")

            # Interruptible wait (G-03): Wakes up immediately if stop_event is set
            if self._stop_event.wait(timeout=sleep_duration):
                break

        self._stop_ping_loop()
        if not self._stop_event.is_set():
            self._set_state(WebSocketState.STOPPED, "Worker loop exited")
        logger.info("WebSocket worker stopped.")

    # ==========================================
    # Callbacks: Open, Close, Error
    # ==========================================

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        """
        Invoked upon successful WebSocket handshake.
        G-03: Resets reconnect delay to base delay.
        G-06: Transitions state to CONNECTED.
        Heartbeat: Starts single managed ping loop.
        """
        logger.info("WebSocket connected. Client is now ONLINE.")

        # Reset reconnect delay after a verified successful connection (G-03)
        with self._state_lock:
            self._current_delay = self.base_delay

        self._set_state(WebSocketState.CONNECTED, "Handshake verified")

        # Start single managed heartbeat loop
        self._start_ping_loop(ws)

    def _on_close(
        self,
        ws: websocket.WebSocketApp,
        close_status_code: int | None,
        close_msg: str | None,
    ) -> None:
        """
        Invoked when the WebSocket connection closes.
        Handles G-04 authentication rejection (codes 4001, 4003, 4004) and stops pinging.
        """
        logger.warning(f"WebSocket closed (code={close_status_code}, message={close_msg})")

        # Immediately stop heartbeat for this closed connection
        self._stop_ping_loop()

        if self._stop_event.is_set():
            return

        # G-04: Authentication failure handling
        if close_status_code in (4001, 4003):
            self._set_state(
                WebSocketState.AUTH_FAILED,
                f"Server rejected credentials (code={close_status_code})",
            )
            if self.refresh_token:
                try:
                    logger.info("Triggering token refresh following WebSocket auth rejection...")
                    new_token = self.refresh_token()
                    if new_token:
                        logger.info("Token refresh succeeded; ready for reconnect with renewed credentials.")
                    else:
                        logger.error("Token refresh returned empty token.")
                except Exception as refresh_err:
                    logger.exception(f"Token refresh failed following WebSocket auth rejection: {refresh_err}")
        elif close_status_code == 4004:
            self._set_state(
                WebSocketState.AUTH_FAILED,
                "Computer not found on server (code=4004)",
            )
        else:
            self._set_state(
                WebSocketState.DISCONNECTED,
                f"Closed with code {close_status_code}",
            )

    def _on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        """Log WebSocket errors."""
        logger.error(f"WebSocket error: {error}")

    # ==========================================
    # Heartbeat Management (Single Loop)
    # ==========================================

    def _start_ping_loop(self, ws: websocket.WebSocketApp) -> None:
        """Start exactly one interruptible heartbeat ping loop."""
        with self._ping_lock:
            self._stop_ping_loop_locked()
            self._ping_stop_event.clear()

            self._ping_thread = threading.Thread(
                target=self._ping_loop,
                args=(ws,),
                daemon=True,
                name="SLMS-WebSocket-Ping",
            )
            self._ping_thread.start()

    def _stop_ping_loop(self) -> None:
        """Stop active heartbeat loop thread."""
        with self._ping_lock:
            self._stop_ping_loop_locked()

    def _stop_ping_loop_locked(self) -> None:
        """Internal helper to signal ping loop termination."""
        self._ping_stop_event.set()
        self._ping_thread = None

    def _ping_loop(self, ws: websocket.WebSocketApp) -> None:
        """
        Send periodic text 'ping' frames.
        Terminates cleanly when connection drops or stop event is signaled.
        """
        while not self._stop_event.is_set() and not self._ping_stop_event.is_set():
            try:
                if ws.sock is None or not ws.sock.connected:
                    break
                ws.send("ping")
                logger.debug("WebSocket heartbeat sent.")
            except Exception as error:
                logger.warning(f"WebSocket ping failed: {error}")
                break

            # Interruptible sleep for ping interval
            if self._ping_stop_event.wait(timeout=self.ping_interval):
                break

    # ==========================================
    # Command Reception & Decoupled Execution (G-05)
    # ==========================================

    def _on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """
        Parse and validate incoming commands, deduplicate, and dispatch
        asynchronously to prevent blocking the WebSocket frame receiver thread.
        """
        logger.info(f"WebSocket message received: {message}")

        try:
            data = json.loads(message)
        except (ValueError, TypeError):
            logger.warning("Received invalid WebSocket JSON.")
            return

        if not isinstance(data, dict) or data.get("type") != "command":
            return

        command_id = data.get("command_id")
        command_type = data.get("command_type")
        payload = data.get("payload")

        if command_id is None:
            logger.warning("Received command without command_id.")
            return

        if not command_type:
            logger.warning("Received command without command_type.")
            return

        # Client-side deduplication (G-05)
        with self._recent_commands_lock:
            if command_id in self._recent_command_ids:
                logger.warning(f"Command {command_id} already received recently; skipping duplicate execution.")
                return

            # Check durable outbox if available
            if self.outbox is not None:
                idempotency_key = f"cmd_result_{command_id}"
                existing_record = self.outbox.get_record_by_idempotency_key(idempotency_key)
                if existing_record is not None:
                    logger.info(
                        f"Command {command_id} already present in outbox (status={existing_record.status.value}); "
                        "skipping re-execution."
                    )
                    return

            self._recent_command_ids.add(command_id)
            if len(self._recent_commands_order) == self._recent_commands_order.maxlen:
                evicted = self._recent_commands_order.popleft()
                self._recent_command_ids.discard(evicted)
            self._recent_commands_order.append(command_id)

        if self._stop_event.is_set():
            logger.warning(f"Skipping command {command_id} dispatch due to active shutdown.")
            return

        # Dispatch command execution asynchronously outside the WebSocket frame thread
        try:
            self._command_executor.submit(
                self._execute_and_enqueue_command,
                command_id,
                command_type,
                payload,
            )
        except Exception as submit_err:
            if self._stop_event.is_set():
                logger.warning(f"Command {command_id} dropped: client is stopping.")
                return
            logger.error(f"Failed to dispatch command {command_id} to worker pool: {submit_err}")
            self._execute_and_enqueue_command(command_id, command_type, payload)

    def _execute_and_enqueue_command(
        self,
        command_id: int,
        command_type: str,
        payload: Any,
    ) -> None:
        """
        Execute command on worker thread and durably persist result to outbox (G-05).
        """
        if self._stop_event.is_set():
            logger.warning(f"Skipping command {command_id} execution due to active shutdown.")
            return

        logger.info(f"Executing remote command: id={command_id}, type={command_type}")
        try:
            success, result_message = execute_command(command_type, payload)
        except Exception as exc:
            logger.exception(f"Unexpected error executing command {command_id}: {exc}")
            success, result_message = False, f"Internal execution error: {exc}"

        # Persist result to durable outbox (Priority 1 = COMMAND)
        if self.outbox is not None:
            try:
                self.outbox.enqueue(
                    event_type="command_result",
                    payload={
                        "command_id": command_id,
                        "success": success,
                        "message": result_message,
                    },
                    idempotency_key=f"cmd_result_{command_id}",
                    priority=OutboxPriority.COMMAND,
                    max_attempts=10,
                )
                logger.info(f"Command result durably enqueued to outbox: command_id={command_id}")
            except Exception as outbox_error:
                logger.error(
                    f"CRITICAL: Failed to enqueue command result {command_id} to durable outbox: {outbox_error}. "
                    "Attempting emergency best-effort synchronous HTTP fallback (durability NOT guaranteed)."
                )
                delivered = self._send_command_result(command_id, success, result_message)
                if not delivered:
                    logger.critical(
                        f"DURABILITY FAILURE: Command result for command_id={command_id} could not be persisted "
                        "to local outbox nor delivered via emergency HTTP."
                    )
        else:
            self._send_command_result(command_id, success, result_message)

    def _send_command_result(
        self,
        command_id: int,
        success: bool,
        message: str,
    ) -> bool:
        """
        Emergency best-effort direct synchronous HTTP submission when outbox is disabled or unavailable.
        WARNING: This does NOT guarantee durability if the network is unavailable or request fails.
        Returns True if delivered, False otherwise.
        """
        try:
            token = self.get_token() if self.get_token else ""
            api_url = get_api_base_url()
            session = create_secure_session()

            response = session.post(
                f"{api_url}/api/commands/{command_id}/result",
                json={
                    "success": success,
                    "message": message,
                },
                headers={
                    "Authorization": f"Bearer {token}"
                },
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Command result delivered via emergency best-effort HTTP: command_id={command_id}")
            return True
        except requests.HTTPError as error:
            logger.error(
                f"Emergency direct HTTP fallback failed with HTTP error for command {command_id}: {error}. "
                "Result could not be persisted to outbox or delivered to server!"
            )
            return False
        except Exception as error:
            logger.error(
                f"Emergency direct HTTP fallback network error for command {command_id}: {error}. "
                "Result could not be persisted to outbox or delivered to server!"
            )
            return False