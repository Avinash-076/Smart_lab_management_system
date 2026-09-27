"""
SLMS Client Agent Runtime Module.

Encapsulates the core agent execution lifecycle (initialization, authentication,
WebSocket connection, periodic monitoring, and data upload).
Separates application runtime logic from the hosting environment (Windows Service
or interactive console).
"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import Any
import uuid

from requests.exceptions import HTTPError

from config import (
    CLEAR_SCREEN,
    ENABLE_ISSUE_REPORTING,
    ENABLE_PROCESS_INFO,
    ENABLE_SOFTWARE_INFO,
    ENABLE_USAGE_INFO,
    EXPORT_JSON,
    MONITOR_INTERVAL,
    SHOW_CONSOLE,
)
from core.collector import collect_all_data
from core.credentials import get_credential_store
from core.exporter import export_to_json
from core.logger import logger
from core.outbox import DurableOutbox, OutboxDeliveryWorker, OutboxPriority
from server.auth import get_access_token
from server.communication import AgentWebSocketClient
from server.enroll import is_enrolled
from server.sender import (
    build_metric_payload,
    send_issue,
    send_metrics,
    send_process_inventory,
    send_software_inventory,
    send_usage_sessions,
)

TOKEN_REFRESH_INTERVAL = 12 * 60  # 12 minutes


class TokenHolder:
    def __init__(self, token: str):
        self.token = token


def get_computer_id() -> int:
    """Retrieve enrolled computer ID from the active credential store."""
    store = get_credential_store()
    creds = store.get_enrolled_credentials()
    if not creds or creds.get("computer_id") is None:
        raise RuntimeError("Computer ID not found in credential store. Agent is not enrolled.")
    return int(creds["computer_id"])


def authenticate_agent() -> str:
    """Authenticate client agent and return fresh JWT access token."""
    logger.info("Authenticating client agent...")
    token = get_access_token()
    logger.info("Authentication successful.")
    return token


# ============================================================================
# Telemetry Upload Helpers
# ============================================================================

def upload_metrics(
    data: dict[str, Any],
    token_holder: TokenHolder,
    outbox: DurableOutbox | None = None,
) -> bool:
    if outbox is not None:
        try:
            metric_payload = build_metric_payload(data)
            comp_id = get_computer_id()
            key = f"metric_{comp_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            outbox.enqueue(
                event_type="metrics",
                payload=metric_payload,
                idempotency_key=key,
                priority=OutboxPriority.TELEMETRY,
            )
            logger.info("Metrics enqueued to durable outbox.")
            return True
        except Exception as e:
            logger.exception(f"Failed to enqueue metrics to outbox: {e}")
            return False

    try:
        send_metrics(data, token_holder.token)
        logger.info("Metrics sent successfully.")
        return True
    except HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            logger.warning("Access token expired during metrics upload. Re-authenticating...")
            try:
                token_holder.token = authenticate_agent()
                send_metrics(data, token_holder.token)
                logger.info("Metrics sent after re-authentication.")
                return True
            except Exception as retry_error:
                logger.exception(f"Metrics retry failed: {retry_error}")
        else:
            logger.exception(f"Metrics upload failed: {e}")
    except Exception as e:
        logger.exception(f"Metrics upload failed: {e}")
    return False


def upload_software(
    data: dict[str, Any],
    token_holder: TokenHolder,
    outbox: DurableOutbox | None = None,
) -> bool:
    if not ENABLE_SOFTWARE_INFO:
        return False
    software = data.get("software")
    if not software:
        return False

    if outbox is not None:
        try:
            comp_id = get_computer_id()
            key = f"software_{comp_id}_{int(time.time())}"
            outbox.enqueue(
                event_type="software",
                payload={"software": software},
                idempotency_key=key,
                priority=OutboxPriority.TELEMETRY,
            )
            logger.info("Software inventory enqueued to durable outbox.")
            return True
        except Exception as e:
            logger.exception(f"Failed to enqueue software to outbox: {e}")
            return False

    try:
        send_software_inventory(software, token_holder.token)
        logger.info("Software inventory sent successfully.")
        return True
    except HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            try:
                token_holder.token = authenticate_agent()
                send_software_inventory(software, token_holder.token)
                return True
            except Exception as retry_error:
                logger.exception(f"Software retry failed: {retry_error}")
        else:
            logger.exception(f"Software upload failed: {e}")
    except Exception as e:
        logger.exception(f"Software upload failed: {e}")
    return False


def upload_processes(
    data: dict[str, Any],
    token_holder: TokenHolder,
    outbox: DurableOutbox | None = None,
) -> bool:
    if not ENABLE_PROCESS_INFO:
        return False
    processes = data.get("processes")
    if not processes:
        return False

    if outbox is not None:
        try:
            comp_id = get_computer_id()
            key = f"processes_{comp_id}_{int(time.time())}"
            outbox.enqueue(
                event_type="processes",
                payload={"processes": processes},
                idempotency_key=key,
                priority=OutboxPriority.TELEMETRY,
            )
            logger.info("Process inventory enqueued to durable outbox.")
            return True
        except Exception as e:
            logger.exception(f"Failed to enqueue processes to outbox: {e}")
            return False

    try:
        send_process_inventory(processes, token_holder.token)
        logger.info("Process inventory sent successfully.")
        return True
    except HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            try:
                token_holder.token = authenticate_agent()
                send_process_inventory(processes, token_holder.token)
                return True
            except Exception as retry_error:
                logger.exception(f"Processes retry failed: {retry_error}")
        else:
            logger.exception(f"Processes upload failed: {e}")
    except Exception as e:
        logger.exception(f"Processes upload failed: {e}")
    return False


def upload_usage(
    data: dict[str, Any],
    token_holder: TokenHolder,
    outbox: DurableOutbox | None = None,
) -> bool:
    if not ENABLE_USAGE_INFO:
        return False
    usage = data.get("usage")
    if not usage:
        return False

    if outbox is not None:
        try:
            comp_id = get_computer_id()
            key = f"usage_{comp_id}_{int(time.time())}_{len(usage)}"
            outbox.enqueue(
                event_type="usage",
                payload={"usage": usage},
                idempotency_key=key,
                priority=OutboxPriority.USAGE,
            )
            logger.info("Usage sessions enqueued to durable outbox.")
            return True
        except Exception as e:
            logger.exception(f"Failed to enqueue usage to outbox: {e}")
            return False

    try:
        send_usage_sessions(usage, token_holder.token)
        logger.info("Usage sessions sent successfully.")
        return True
    except HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            try:
                token_holder.token = authenticate_agent()
                send_usage_sessions(usage, token_holder.token)
                return True
            except Exception as retry_error:
                logger.exception(f"Usage retry failed: {retry_error}")
        else:
            logger.exception(f"Usage upload failed: {e}")
    except Exception as e:
        logger.exception(f"Usage upload failed: {e}")
    return False


def upload_issues(
    data: dict[str, Any],
    token_holder: TokenHolder,
    outbox: DurableOutbox | None = None,
) -> bool:
    if not ENABLE_ISSUE_REPORTING:
        return False
    issues = data.get("issues")
    if not issues:
        return False

    if outbox is not None:
        all_enqueued = True
        for issue in issues:
            try:
                comp_id = get_computer_id()
                title_slug = issue.get("title", "").replace(" ", "_")[:32]
                key = f"issue_{comp_id}_{title_slug}_{int(time.time())}"
                outbox.enqueue(
                    event_type="issue",
                    payload=issue,
                    idempotency_key=key,
                    priority=OutboxPriority.ISSUE,
                )
                logger.info("Issue report enqueued to durable outbox.")
            except Exception as e:
                logger.exception(f"Failed to enqueue issue to outbox: {e}")
                all_enqueued = False
        return all_enqueued

    all_sent = True
    for issue in issues:
        try:
            send_issue(issue, token_holder.token)
            logger.info("Issue report sent successfully.")
        except Exception as e:
            logger.exception(f"Issue upload failed: {e}")
            all_sent = False
    return all_sent


def display_console_data(data: dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("SMART LAB MANAGEMENT SYSTEM")
    print("=" * 60)
    for section, values in data.items():
        print(f"\n{section.upper()}\n" + "-" * 60)
        if values is None:
            print("Unable to collect data.")
            continue
        if isinstance(values, dict):
            for k, v in values.items():
                print(f"{k:20}: {v}")
        elif isinstance(values, list):
            print(f"Total items: {len(values)}")


# ============================================================================
# AgentRuntime
# ============================================================================

class AgentRuntime:
    """
    Manages the lifecycle and execution of the SLMS monitoring runtime.
    Can be hosted inside a Windows Service or run in an interactive console.
    """

    def __init__(
        self,
        stop_event: threading.Event | None = None,
        is_service: bool = False,
        outbox: DurableOutbox | None = None,
        enable_outbox: bool = True,
    ):
        self.stop_event = stop_event or threading.Event()
        self.is_service = is_service
        self.enable_outbox = enable_outbox
        self.outbox = outbox if (outbox is not None or not enable_outbox) else DurableOutbox()
        self.delivery_worker: OutboxDeliveryWorker | None = None
        self.ws_client: AgentWebSocketClient | None = None
        self.token_holder: TokenHolder | None = None
        self.computer_id: int | None = None
        self._is_running = False
        self._lifecycle_lock = threading.Lock()
        self.started_count = 0
        self.stopped_count = 0

    @property
    def is_running(self) -> bool:
        return self._is_running

    def _refresh_token_safe(self) -> str:
        """Refresh JWT access token and update token holder in-memory."""
        token = authenticate_agent()
        if self.token_holder:
            self.token_holder.token = token
        return token

    def start(self) -> None:
        """
        Initialize credentials, authenticate, connect WebSocket, and execute
        the monitoring loop until the stop event is signaled.
        """
        with self._lifecycle_lock:
            if self._is_running or self.stop_event.is_set():
                logger.warning("AgentRuntime is already running or stopped.")
                return

        logger.info("=" * 60)
        logger.info("SLMS Agent Runtime Starting")
        logger.info(f"Execution Mode: {'Windows Service' if self.is_service else 'Interactive'}")
        logger.info("=" * 60)

        # Enrollment Check
        if not is_enrolled():
            if self.is_service:
                error_msg = (
                    "SLMS Client Agent is not enrolled. Cannot start Windows Service "
                    "without prior enrollment. Please run interactive enrollment as Administrator."
                )
                logger.critical(error_msg)
                raise RuntimeError(error_msg)
            else:
                # Interactive fallback: open enrollment window
                from gui.enrollment_window import show_enrollment_window
                logger.info("No SLMS enrollment found. Opening enrollment window...")
                show_enrollment_window()
                if not is_enrolled():
                    raise RuntimeError("SLMS enrollment was not completed.")

        # Authenticate
        access_token = authenticate_agent()
        self.token_holder = TokenHolder(access_token)
        self.computer_id = get_computer_id()

        logger.info(f"Enrolled Computer ID: {self.computer_id}")

        with self._lifecycle_lock:
            if self.stop_event.is_set():
                return

            # Start Outbox Delivery Worker
            if self.enable_outbox and self.outbox:
                self.delivery_worker = OutboxDeliveryWorker(
                    outbox=self.outbox,
                    get_token=lambda: self.token_holder.token if self.token_holder else "",
                    refresh_token=self._refresh_token_safe,
                    stop_event=self.stop_event,
                )
                self.delivery_worker.start()

            # Start WebSocket Client
            self.ws_client = AgentWebSocketClient(
                computer_id=self.computer_id,
                get_token=lambda: self.token_holder.token if self.token_holder else "",
                outbox=self.outbox if self.enable_outbox else None,
            )
            self.ws_client.start()

            self._is_running = True
            self.started_count += 1

        token_acquired_at = time.monotonic()

        try:
            while not self.stop_event.is_set():
                # ----------------------------------------------------
                # Token Refresh Check
                # ----------------------------------------------------
                if time.monotonic() - token_acquired_at > TOKEN_REFRESH_INTERVAL:
                    try:
                        logger.info("Refreshing access token...")
                        self.token_holder.token = authenticate_agent()
                        token_acquired_at = time.monotonic()
                    except Exception as e:
                        logger.exception(f"Periodic token refresh failed: {e}")

                # ----------------------------------------------------
                # Console Clear (Interactive Mode Only)
                # ----------------------------------------------------
                if (
                    not self.is_service
                    and CLEAR_SCREEN
                    and SHOW_CONSOLE
                    and not getattr(sys, "frozen", False)
                ):
                    os.system("cls")

                # ----------------------------------------------------
                # Data Collection
                # ----------------------------------------------------
                logger.info("Collecting system information...")
                data = collect_all_data()
                logger.info("Data collection completed.")

                # ----------------------------------------------------
                # Uploads
                # ----------------------------------------------------
                active_outbox = self.outbox if self.enable_outbox else None
                upload_metrics(data, self.token_holder, outbox=active_outbox)
                upload_software(data, self.token_holder, outbox=active_outbox)
                upload_processes(data, self.token_holder, outbox=active_outbox)
                upload_usage(data, self.token_holder, outbox=active_outbox)
                upload_issues(data, self.token_holder, outbox=active_outbox)

                if EXPORT_JSON:
                    try:
                        filepath = export_to_json(data)
                        logger.info(f"JSON exported: {filepath}")
                    except Exception as e:
                        logger.exception(f"JSON export failed: {e}")

                if not self.is_service and SHOW_CONSOLE:
                    display_console_data(data)
                    print(f"\nNext scan in {MONITOR_INTERVAL} seconds...")

                # Responsive wait: wakes up immediately if stop_event is signaled
                self.stop_event.wait(timeout=MONITOR_INTERVAL)

        except Exception as e:
            logger.exception(f"Fatal error in agent runtime loop: {e}")
            raise
        finally:
            self._cleanup()

    def stop(self) -> None:
        """Signal runtime to terminate and trigger clean resource shutdown."""
        logger.info("Signaling AgentRuntime shutdown...")
        self.stop_event.set()
        self._cleanup()

    def _cleanup(self) -> None:
        """Release WebSocket, outbox delivery worker, and mark runtime as stopped."""
        with self._lifecycle_lock:
            was_running = self._is_running
            self._is_running = False

            if self.delivery_worker:
                try:
                    self.delivery_worker.stop()
                except Exception:
                    pass
                self.delivery_worker = None

            if self.ws_client:
                try:
                    self.ws_client.stop()
                except Exception:
                    pass
                self.ws_client = None

            if was_running:
                self.stopped_count += 1
                logger.info("SLMS Agent Runtime stopped cleanly.")
