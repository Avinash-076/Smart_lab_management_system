"""
SLMS Interactive User Notification Companion (Phase 2 & 3 Architecture).

Runs in the active user's interactive desktop session (Session 1..N) with
standard unprivileged user rights.

Key Responsibilities:
1. Connects to the local-only named pipe \\\\.\\pipe\\SLMS_Notification_IPC.
2. Maintains connection with bounded exponential reconnect backoff.
3. Responds to service heartbeats (PING/PONG).
4. Strictly validates incoming NOTIFY frames and checks local deduplication.
5. Dispatches native interactive desktop dialogs on a dedicated UI worker thread
   so that the IPC receive loop remains completely responsive while dialogs are open.
6. Emits structured lifecycle acknowledgments back to the service:
   - ACCEPTED: Request validated, deduplicated, and queued.
   - DISPLAYED: Native message box actively rendered on screen.
   - DISMISSED: Interactive user clicked OK or dismissed the dialog.
   - REJECTED: Payload invalid, oversized, or duplicate.
   - FAILED: UI rendering failed.
7. Strictly rejects arbitrary commands, shell executions, or system modifications.
"""

from __future__ import annotations

import os
import random
import sys
import threading
import time
from typing import Any, Callable

from core.ipc import (
    DEFAULT_CONNECT_TIMEOUT,
    MAX_MESSAGE_LENGTH,
    MAX_TITLE_LENGTH,
    CommandDeduplicator,
    IPCMessageType,
    NotificationPipeClient,
    NotificationStatus,
    PIPE_NAME,
    query_session_lock_state,
    validate_lock_payload,
    validate_notify_payload,
)
from core.logger import logger


def default_lock_workstation() -> tuple[bool, int, str]:
    """
    Execute user32.LockWorkStation from interactive user session.
    Returns (success, win32_error, description).
    """
    if os.name != "nt":
        return True, 0, "Non-Windows mock lock"

    import ctypes
    u32 = getattr(ctypes.windll, "user32", None)
    if not u32:
        return False, -1, "user32 library unavailable"

    ret = u32.LockWorkStation()
    if ret:
        return True, 0, ""
    err = ctypes.GetLastError() if hasattr(ctypes, "GetLastError") else 0
    return False, err, f"LockWorkStation failed with Win32 error {err}"


def default_desktop_message_box(
    title: str,
    message: str,
    on_displayed: Callable[[], None] | None = None,
) -> bool:
    """
    Display a native Windows modal dialog on the interactive desktop.
    Uses Win32 user32.MessageBoxW with:
    - MB_OK (0x0)
    - MB_ICONINFORMATION (0x40)
    - MB_TOPMOST (0x40000)
    - MB_SETFOREGROUND (0x10000)
    - MB_SYSTEMMODAL (0x1000)
    Uses a thread-local WH_CBT hook to confirm actual window activation before blocking.
    Returns True when dismissed by the user.
    """
    if os.name != "nt":
        if on_displayed:
            try:
                on_displayed()
            except Exception:
                pass
        return True

    import ctypes
    from ctypes import wintypes

    u32 = ctypes.windll.user32
    k32 = ctypes.windll.kernel32
    # Style: MB_OK (0) | MB_ICONINFORMATION (0x40) | MB_TOPMOST (0x40000) | MB_SETFOREGROUND (0x10000) | MB_SYSTEMMODAL (0x1000)
    MB_STYLE = 0x00000000 | 0x00000040 | 0x00040000 | 0x00010000 | 0x00001000

    u32.MessageBoxW.argtypes = [
        wintypes.HWND,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.UINT,
    ]
    u32.MessageBoxW.restype = ctypes.c_int

    hook_handle = None
    if on_displayed is not None:
        try:
            WH_CBT = 5
            HCBT_ACTIVATE = 5
            HCBT_CREATEWND = 3

            HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

            u32.SetWindowsHookExW.argtypes = [
                ctypes.c_int,
                HOOKPROC,
                wintypes.HINSTANCE,
                wintypes.DWORD,
            ]
            u32.SetWindowsHookExW.restype = wintypes.HHOOK

            u32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
            u32.UnhookWindowsHookEx.restype = wintypes.BOOL

            u32.CallNextHookEx.argtypes = [
                wintypes.HHOOK,
                ctypes.c_int,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            u32.CallNextHookEx.restype = ctypes.c_long

            notified = False

            def _cbt_hook(nCode: int, wParam: Any, lParam: Any) -> int:
                nonlocal notified
                if not notified and nCode in (HCBT_ACTIVATE, HCBT_CREATEWND):
                    notified = True
                    try:
                        on_displayed()
                    except Exception:
                        pass
                return u32.CallNextHookEx(hook_handle, nCode, wParam, lParam)

            c_hook = HOOKPROC(_cbt_hook)
            hook_handle = u32.SetWindowsHookExW(
                WH_CBT,
                c_hook,
                None,
                k32.GetCurrentThreadId(),
            )
        except Exception as hook_err:
            logger.debug(f"Could not install CBT hook for display tracking: {hook_err}")
            try:
                on_displayed()
            except Exception:
                pass

    try:
        ret = u32.MessageBoxW(0, message, title, MB_STYLE)
        return ret != 0
    finally:
        if hook_handle:
            try:
                u32.UnhookWindowsHookEx(hook_handle)
            except Exception:
                pass


class NotificationCompanion:
    """
    Interactive desktop notification companion client.
    """

    def __init__(
        self,
        pipe_name: str = PIPE_NAME,
        session_id: int | None = None,
        display_fn: Callable[[str, str], bool] | None = None,
        lock_fn: Callable[[], tuple[bool, int, str]] | None = None,
        base_reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 15.0,
    ):
        self.pipe_name = pipe_name
        self.session_id = session_id
        self.display_fn = display_fn or default_desktop_message_box
        self.lock_fn = lock_fn or default_lock_workstation
        self.base_reconnect_delay = base_reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay

        self._client: NotificationPipeClient | None = None
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None
        self._deduplicator = CommandDeduplicator()
        self._active_ui_threads: list[threading.Thread] = []
        self._ui_threads_lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._worker_thread is not None and self._worker_thread.is_alive()

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    def start(self) -> None:
        """Start the companion background worker thread."""
        if self.is_running:
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._run_loop,
            name="SLMS_NotificationCompanion",
            daemon=True,
        )
        self._worker_thread.start()
        logger.info(f"SLMS Notification Companion started (session {self.session_id or 'auto'}).")

    def stop(self) -> None:
        """Stop the companion and disconnect from IPC pipe."""
        self._stop_event.set()
        if self._client:
            self._client.disconnect()
        if self._worker_thread and self._worker_thread.is_alive():
            try:
                self._worker_thread.join(timeout=2.0)
            except RuntimeError:
                pass
        logger.info("SLMS Notification Companion stopped.")

    def run_forever(self) -> None:
        """Run blocking companion loop until interrupted."""
        self.start()
        try:
            while not self._stop_event.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Companion received keyboard interrupt. Shutting down...")
        finally:
            self.stop()

    def _run_loop(self) -> None:
        """Main connection and message processing loop with auto-reconnection."""
        retry_count = 0

        while not self._stop_event.is_set():
            client = NotificationPipeClient(pipe_name=self.pipe_name, session_id=self.session_id)
            self._client = client

            logger.info(f"Connecting to SLMS Notification IPC at {self.pipe_name}...")
            connected = client.connect(timeout_sec=DEFAULT_CONNECT_TIMEOUT)

            if not connected or not client.is_connected:
                if self._stop_event.is_set():
                    break

                # Exponential backoff with random jitter
                retry_count += 1
                backoff = min(self.max_reconnect_delay, self.base_reconnect_delay * (2 ** (retry_count - 1)))
                jitter = backoff * random.uniform(0.0, 0.2)
                sleep_sec = round(backoff + jitter, 2)

                logger.debug(f"IPC pipe connection failed. Retrying in {sleep_sec}s (attempt {retry_count})...")
                self._stop_event.wait(timeout=sleep_sec)
                continue

            # Connection successful
            logger.info("Successfully connected and authenticated with SLMS Service.")
            retry_count = 0

            try:
                self._service_connected_pipe(client)
            except Exception as exc:
                logger.warning(f"Error servicing pipe connection: {exc}")
            finally:
                client.disconnect()
                if not self._stop_event.is_set():
                    logger.info("Service disconnected. Will attempt reconnection...")
                    time.sleep(1.0)

    def _service_connected_pipe(self, client: NotificationPipeClient) -> None:
        """Receive and process notification requests from the service."""
        while not self._stop_event.is_set() and client.is_connected:
            msg = client.read_notification(timeout_sec=1.0)
            if not client.is_connected:
                break
            if msg is None:
                continue

            msg_type = msg.get("type")

            # Heartbeat PING
            if msg_type == IPCMessageType.PING.value:
                client.send_ack("ping", NotificationStatus.ACCEPTED, details="PONG")
                continue

            # Notification Request
            if msg_type == IPCMessageType.NOTIFY.value:
                self._handle_notify_request(client, msg)
            elif msg_type == IPCMessageType.LOCK_WORKSTATION.value:
                self._handle_lock_request(client, msg)
            else:
                logger.warning(f"Companion received unexpected message type: {msg_type}")

    def _handle_lock_request(self, client: NotificationPipeClient, data: dict[str, Any]) -> None:
        """
        Validate and execute a narrowly scoped LOCK_WORKSTATION request in the user session.
        Invokes user32.LockWorkStation(), captures return value and error code,
        and verifies whether the locked state is independently confirmed.
        """
        cmd_id = data.get("command_id", "")

        # 1. Strict schema and boundary validation
        valid, err = validate_lock_payload(data)
        if not valid:
            logger.warning(f"Rejected invalid LOCK_WORKSTATION payload: {err}")
            client.send_ack(cmd_id, NotificationStatus.REJECTED, details=f"Schema validation failed: {err}")
            return

        # 2. Local deduplication check
        if self._deduplicator.is_duplicate(cmd_id):
            logger.warning(f"Duplicate lock command {cmd_id} suppressed by companion deduplicator.")
            client.send_ack(cmd_id, NotificationStatus.REJECTED, details="Duplicate command already processed")
            return

        # 3. Call LockWorkStation in the active interactive user session
        logger.info(f"Executing workstation lock for command {cmd_id} in session {self.session_id}...")
        try:
            ok, err_code, err_msg = self.lock_fn()
            if not ok:
                logger.warning(f"LockWorkStation failed for {cmd_id}: {err_msg} (error code {err_code})")
                client.send_ack(
                    cmd_id,
                    NotificationStatus.FAILED,
                    details=f"user32.LockWorkStation returned 0: Win32 error {err_code}",
                )
                return

            # LockWorkStation returned non-zero (Windows accepted the call).
            # Verify whether the locked desktop state is independently confirmed.
            confirmed = False
            t0 = time.monotonic()
            while time.monotonic() - t0 < 1.0:
                lock_state = query_session_lock_state(self.session_id)
                if lock_state == 0:  # WTS_SESSIONSTATE_LOCK
                    confirmed = True
                    break
                time.sleep(0.05)

            if confirmed:
                logger.info(f"Workstation lock independently confirmed for command {cmd_id}.")
                client.send_ack(
                    cmd_id,
                    NotificationStatus.LOCK_CONFIRMED,
                    details="Workstation lock confirmed (session state: locked)",
                )
            else:
                logger.warning(
                    f"Workstation lock accepted by Windows for {cmd_id}, but locked state not confirmed."
                )
                client.send_ack(
                    cmd_id,
                    NotificationStatus.REQUEST_ACCEPTED,
                    details="Windows accepted LockWorkStation, but locked state was not independently confirmed",
                )

        except Exception as exc:
            logger.exception(f"Exception during workstation lock execution for {cmd_id}: {exc}")
            client.send_ack(cmd_id, NotificationStatus.FAILED, details=f"Lock exception: {exc}")

    def _handle_notify_request(self, client: NotificationPipeClient, data: dict[str, Any]) -> None:
        """Validate, acknowledge, and asynchronously render an alert."""
        cmd_id = data.get("command_id", "")

        # 1. Strict schema and boundary validation
        valid, err = validate_notify_payload(data)
        if not valid:
            logger.warning(f"Rejected invalid NOTIFY payload: {err}")
            client.send_ack(cmd_id, NotificationStatus.REJECTED, details=f"Schema validation failed: {err}")
            return

        # 2. Local deduplication check
        if self._deduplicator.is_duplicate(cmd_id):
            logger.warning(f"Duplicate notification {cmd_id} suppressed by companion deduplicator.")
            client.send_ack(cmd_id, NotificationStatus.REJECTED, details="Duplicate command already displayed")
            return

        title = str(data.get("title", "SLMS Administrator Notice"))[:MAX_TITLE_LENGTH]
        message = str(data.get("message", ""))[:MAX_MESSAGE_LENGTH]

        # 3. Immediately acknowledge receipt and validation (ACCEPTED)
        client.send_ack(cmd_id, NotificationStatus.ACCEPTED, details="Notification accepted and queued for display")

        # 4. Launch modal dialog on background UI thread so pipe receiver remains responsive
        ui_thread = threading.Thread(
            target=self._render_notification_worker,
            args=(client, cmd_id, title, message),
            name=f"SLMS_UI_{cmd_id}",
            daemon=True,
        )

        with self._ui_threads_lock:
            # Clean terminated threads
            self._active_ui_threads = [t for t in self._active_ui_threads if t.is_alive()]
            self._active_ui_threads.append(ui_thread)

        ui_thread.start()

    def _render_notification_worker(
        self,
        client: NotificationPipeClient,
        cmd_id: str,
        title: str,
        message: str,
    ) -> None:
        """Display the message on the interactive desktop and track DISPLAYED/DISMISSED states."""
        displayed_sent = False

        def mark_displayed():
            nonlocal displayed_sent
            if not displayed_sent:
                displayed_sent = True
                client.send_ack(cmd_id, NotificationStatus.DISPLAYED, details="Dialog rendered on active desktop")

        try:
            logger.info(f"Displaying notice {cmd_id} on desktop: '{title}'")
            import inspect
            sig = inspect.signature(self.display_fn)
            if "on_displayed" in sig.parameters:
                success = self.display_fn(title, message, on_displayed=mark_displayed)
            else:
                mark_displayed()
                success = self.display_fn(title, message)

            if success:
                logger.info(f"User acknowledged notice {cmd_id}.")
                client.send_ack(cmd_id, NotificationStatus.DISMISSED, details="User acknowledged and dismissed alert")
            else:
                logger.warning(f"Display function returned false for notice {cmd_id}.")
                client.send_ack(cmd_id, NotificationStatus.FAILED, details="Display function returned false")

        except Exception as exc:
            logger.exception(f"Exception during notification display for {cmd_id}: {exc}")
            client.send_ack(cmd_id, NotificationStatus.FAILED, details=f"Display exception: {exc}")
