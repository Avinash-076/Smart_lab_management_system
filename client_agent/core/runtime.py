"""
SLMS Client Agent Runtime Module (Phase 8 Architecture).

Assembles modular runtime managers:
- RuntimeManager: High-level coordinator holding Scheduler, CollectorManager,
  UploadManager, WebSocketManager, TokenManager, OutboxManager, and ShutdownManager.
- AgentRuntime: Backwards-compatible facade preserving all public attributes,
  properties, cadence checks, and lifecycle methods for Windows Service, CLI, and tests.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import Any

from config import (
    CLEAR_SCREEN,
    EXPORT_JSON,
    MONITOR_INTERVAL,
    PROCESS_COLLECTION_INTERVAL,
    SHOW_CONSOLE,
    SOFTWARE_SCAN_INTERVAL,
)
from core.collector import collect_all_data
from core.credentials import get_credential_store
from core.exporter import export_to_json
from core.logger import logger
from core.managers import (
    CollectorManager,
    OutboxManager,
    ShutdownManager,
    TokenHolder,
    TokenManager,
    UploadManager,
    WebSocketManager,
)
from core.outbox import DurableOutbox, OutboxDeliveryWorker, OutboxPriority
from core.scheduler import Scheduler
from server.auth import get_access_token
from server.communication import AgentWebSocketClient, WebSocketState
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


def get_computer_id() -> int:
    """Retrieve enrolled computer ID from credential store."""
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
# RuntimeManager (H-01)
# ============================================================================

class RuntimeManager:
    """
    High-level runtime coordinator assembling modular managers:
    Scheduler, CollectorManager, UploadManager, WebSocketManager, TokenManager,
    OutboxManager, and ShutdownManager.
    """

    def __init__(
        self,
        stop_event: threading.Event | None = None,
        is_service: bool = False,
        outbox: DurableOutbox | None = None,
        enable_outbox: bool = True,
        process_interval: float = PROCESS_COLLECTION_INTERVAL,
        software_interval: float = SOFTWARE_SCAN_INTERVAL,
        software_state_file: str | None = None,
        issue_state_file: str | None = None,
    ):
        self.stop_event = stop_event or threading.Event()
        self.is_service = is_service
        self.enable_outbox = enable_outbox
        self.process_interval = process_interval
        self.software_interval = software_interval
        self.software_state_file = software_state_file
        self.issue_state_file = issue_state_file

        # Sub-managers
        self.token_manager = TokenManager(refresh_interval=TOKEN_REFRESH_INTERVAL)
        self.outbox_manager = OutboxManager(
            outbox=outbox,
            enable_outbox=enable_outbox,
            software_state_file=software_state_file,
            issue_state_file=issue_state_file,
        )
        self.websocket_manager = WebSocketManager()
        self.collector_manager = CollectorManager(max_workers=2)
        self.upload_manager = UploadManager()
        self.scheduler = Scheduler(stop_event=self.stop_event)
        self.shutdown_manager = ShutdownManager(stop_event=self.stop_event)

        self._last_process_collection: float | None = None
        self._last_software_scan: float | None = None
        self.computer_id: int | None = None
        self._is_running = False
        self._lifecycle_lock = threading.Lock()
        self.started_count = 0
        self.stopped_count = 0

    @property
    def is_running(self) -> bool:
        return self._is_running

    def due_for_process_collection(self, now: float | None = None) -> bool:
        """Check if process inventory collection is due based on cadence (E-01)."""
        if now is None:
            now = time.monotonic()
        if self._last_process_collection is None:
            return True
        return (now - self._last_process_collection) >= self.process_interval

    def due_for_software_scan(self, now: float | None = None) -> bool:
        """Check if software inventory scan is due based on cadence (E-05)."""
        if now is None:
            now = time.monotonic()
        if self._last_software_scan is None:
            return True
        return (now - self._last_software_scan) >= self.software_interval

    def _refresh_token_safe(self) -> str:
        """Refresh JWT access token and update token holder in-memory."""
        return self.token_manager.refresh()

    def _register_scheduled_jobs(self) -> None:
        """Register drift-free recurring monitoring tasks in the Scheduler."""

        # 1. Fast Telemetry (20s fixed cadence: hardware, network, usage, issues)
        def _telemetry_task():
            if self.stop_event.is_set():
                return
            if (
                not self.is_service
                and CLEAR_SCREEN
                and SHOW_CONSOLE
                and not getattr(sys, "frozen", False)
            ):
                os.system("cls")

            logger.info("Collecting system telemetry...")
            data = self.collector_manager.collect_telemetry(issue_state_file=self.issue_state_file)
            logger.info("System telemetry collection completed.")

            active_outbox = self.outbox_manager.outbox if self.outbox_manager.enabled else None
            import core.runtime as rt
            rt_upload_metrics = getattr(rt, "upload_metrics", None)
            if rt_upload_metrics is not None and rt_upload_metrics is not upload_metrics:
                rt_upload_metrics(data, self.token_manager.token_holder, outbox=active_outbox)
            else:
                self.upload_manager.upload_metrics(data, self.token_manager, self.outbox_manager)

            rt_upload_usage = getattr(rt, "upload_usage", None)
            if rt_upload_usage is not None and rt_upload_usage is not upload_usage:
                rt_upload_usage(data, self.token_manager.token_holder, outbox=active_outbox)
            else:
                self.upload_manager.upload_usage(data, self.token_manager, self.outbox_manager)

            rt_upload_issues = getattr(rt, "upload_issues", None)
            if rt_upload_issues is not None and rt_upload_issues is not upload_issues:
                rt_upload_issues(
                    data,
                    self.token_manager.token_holder,
                    outbox=active_outbox,
                    state_file=self.issue_state_file,
                )
            else:
                self.upload_manager.upload_issues(
                    data,
                    self.token_manager,
                    self.outbox_manager,
                    state_file=self.issue_state_file,
                )

            if EXPORT_JSON:
                try:
                    filepath = export_to_json(data)
                    logger.info(f"JSON exported: {filepath}")
                except Exception as e:
                    logger.exception(f"JSON export failed: {e}")

            if not self.is_service and SHOW_CONSOLE:
                display_console_data(data)
                print(f"\nNext scan in {MONITOR_INTERVAL} seconds...")

        # 2. Process Inventory (120s cadence)
        def _process_task():
            if self.stop_event.is_set():
                return
            now = time.monotonic()
            self._last_process_collection = now
            logger.info("Collecting running processes...")
            procs = self.collector_manager.collect_processes()
            self.upload_manager.upload_processes(procs, self.token_manager, self.outbox_manager)

        # 3. Software Inventory (900s cadence)
        def _software_task():
            if self.stop_event.is_set():
                return
            now = time.monotonic()
            self._last_software_scan = now
            logger.info("Collecting installed software inventory...")
            sw = self.collector_manager.collect_software()
            self.upload_manager.upload_software(
                sw,
                self.token_manager,
                self.outbox_manager,
                state_file=self.software_state_file,
            )

        # 4. Token Refresh (12m cadence)
        def _token_refresh_task():
            if self.stop_event.is_set():
                return
            self.token_manager.refresh_if_due()

        # Register jobs on drift-free scheduler (H-04)
        self.scheduler.add_job("telemetry", MONITOR_INTERVAL, _telemetry_task, initial_delay=0.0)
        self.scheduler.add_job("processes", self.process_interval, _process_task, initial_delay=0.0)
        self.scheduler.add_job("software", self.software_interval, _software_task, initial_delay=0.0)
        self.scheduler.add_job("token_refresh", TOKEN_REFRESH_INTERVAL, _token_refresh_task, initial_delay=TOKEN_REFRESH_INTERVAL)

    def start(self) -> None:
        """
        Initialize credentials, authenticate, wire sub-managers, start scheduler,
        and wait for shutdown.
        """
        with self._lifecycle_lock:
            if self._is_running or self.stop_event.is_set():
                logger.warning("RuntimeManager is already running or stopped.")
                return

        logger.info("=" * 60)
        logger.info("SLMS Agent Runtime Starting (Phase 8 Architecture)")
        logger.info(f"Execution Mode: {'Windows Service' if self.is_service else 'Interactive'}")
        logger.info("=" * 60)

        from paths import ensure_directories_exist
        ensure_directories_exist()

        # Enrollment Check
        import core.runtime as rt
        is_enrolled_fn = getattr(rt, "is_enrolled", is_enrolled)
        if not is_enrolled_fn():
            if self.is_service:
                error_msg = (
                    "SLMS Client Agent is not enrolled. Cannot start Windows Service "
                    "without prior enrollment. Please run interactive enrollment as Administrator."
                )
                logger.critical(error_msg)
                raise RuntimeError(error_msg)
            else:
                from gui.enrollment_window import show_enrollment_window
                logger.info("No SLMS enrollment found. Opening enrollment window...")
                show_enrollment_window()
                if not is_enrolled_fn():
                    raise RuntimeError("SLMS enrollment was not completed.")

        # Authenticate & Acquire Computer ID
        self.token_manager.refresh()
        comp_id_fn = getattr(rt, "get_computer_id", get_computer_id)
        self.computer_id = comp_id_fn()
        logger.info(f"Enrolled Computer ID: {self.computer_id}")

        with self._lifecycle_lock:
            if self.stop_event.is_set():
                return

            # Start Outbox Delivery Worker
            self.outbox_manager.start(self.token_manager, self.stop_event)

            # Start WebSocket Client
            if self.computer_id is not None:
                self.websocket_manager.start(self.computer_id, self.token_manager, self.outbox_manager)

            # Register jobs and start scheduler
            self._register_scheduled_jobs()
            self.scheduler.start()

            self._is_running = True
            self.started_count += 1

        try:
            # Block until shutdown is requested
            self.stop_event.wait()
        except Exception as e:
            logger.exception(f"Fatal error in agent runtime loop: {e}")
            raise
        finally:
            self._cleanup()

    def stop(self) -> None:
        """Signal runtime to terminate and trigger clean staged shutdown."""
        logger.info("Signaling RuntimeManager shutdown...")
        self.stop_event.set()
        self._cleanup()

    def _cleanup(self) -> None:
        """Execute staged teardown in safe dependency order."""
        with self._lifecycle_lock:
            was_running = self._is_running
            self._is_running = False

            self.shutdown_manager.shutdown(
                scheduler=self.scheduler,
                collector_manager=self.collector_manager,
                outbox_manager=self.outbox_manager,
                websocket_manager=self.websocket_manager,
            )

            if was_running:
                self.stopped_count += 1
                logger.info("SLMS Agent Runtime stopped cleanly.")


# ============================================================================
# AgentRuntime (Backwards Compatibility Facade)
# ============================================================================

class AgentRuntime(RuntimeManager):
    """
    Backwards-compatible facade preserving all public attributes, methods,
    and properties expected by ServiceLifecycle, tests, and CLI callers.
    """

    @property
    def token_holder(self) -> TokenHolder:
        return self.token_manager.token_holder

    @token_holder.setter
    def token_holder(self, holder: TokenHolder) -> None:
        self.token_manager.token_holder = holder

    @property
    def outbox(self) -> DurableOutbox | None:
        return self.outbox_manager.outbox

    @property
    def delivery_worker(self) -> OutboxDeliveryWorker | None:
        return self.outbox_manager.delivery_worker

    @delivery_worker.setter
    def delivery_worker(self, worker: OutboxDeliveryWorker | None) -> None:
        self.outbox_manager.delivery_worker = worker

    @property
    def ws_client(self) -> AgentWebSocketClient | None:
        return self.websocket_manager.ws_client

    @ws_client.setter
    def ws_client(self, client: AgentWebSocketClient | None) -> None:
        self.websocket_manager.ws_client = client

    @property
    def ws_state(self) -> WebSocketState | None:
        """Observable WebSocket connection state (Phase 7 G-06)."""
        return self.websocket_manager.state

    @property
    def is_connected(self) -> bool:
        return self.websocket_manager.is_connected

    @property
    def software_cache(self):
        return self.collector_manager.software_cache

    @property
    def process_cache(self):
        return self.collector_manager.process_cache


# ============================================================================
# Backwards-Compatible Telemetry Upload Helpers
# ============================================================================

def upload_metrics(
    data: dict[str, Any],
    token_holder: TokenHolder,
    outbox: DurableOutbox | None = None,
) -> bool:
    mgr = UploadManager()
    outbox_mgr = OutboxManager(outbox=outbox, enable_outbox=(outbox is not None))
    token_mgr = TokenManager(token_holder=token_holder)
    return mgr.upload_metrics(data, token_mgr, outbox_mgr)


def upload_software(
    data: dict[str, Any],
    token_holder: TokenHolder,
    outbox: DurableOutbox | None = None,
    state_file: str | None = None,
    force: bool = False,
) -> bool:
    mgr = UploadManager()
    outbox_mgr = OutboxManager(outbox=outbox, enable_outbox=(outbox is not None))
    token_mgr = TokenManager(token_holder=token_holder)
    return mgr.upload_software(data, token_mgr, outbox_mgr, state_file=state_file, force=force)


def upload_processes(
    data: dict[str, Any],
    token_holder: TokenHolder,
    outbox: DurableOutbox | None = None,
) -> bool:
    mgr = UploadManager()
    outbox_mgr = OutboxManager(outbox=outbox, enable_outbox=(outbox is not None))
    token_mgr = TokenManager(token_holder=token_holder)
    return mgr.upload_processes(data, token_mgr, outbox_mgr)


def upload_usage(
    data: dict[str, Any],
    token_holder: TokenHolder,
    outbox: DurableOutbox | None = None,
) -> bool:
    mgr = UploadManager()
    outbox_mgr = OutboxManager(outbox=outbox, enable_outbox=(outbox is not None))
    token_mgr = TokenManager(token_holder=token_holder)
    return mgr.upload_usage(data, token_mgr, outbox_mgr)


def upload_issues(
    data: dict[str, Any],
    token_holder: TokenHolder,
    outbox: DurableOutbox | None = None,
    state_file: str | None = None,
) -> bool:
    mgr = UploadManager()
    outbox_mgr = OutboxManager(outbox=outbox, enable_outbox=(outbox is not None))
    token_mgr = TokenManager(token_holder=token_holder)
    return mgr.upload_issues(data, token_mgr, outbox_mgr, state_file=state_file)


def display_console_data(data: dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("SMART LAB MANAGEMENT SYSTEM")
    print("=" * 60)
    for section, values in data.items():
        print(f"\n{section.upper()}\n" + "-" * 60)
        if hasattr(values, "is_failed") and values.is_failed:
            print(f"Collection failed: {values.error.message if values.error else 'Error'}")
            continue
        actual_val = values.data if hasattr(values, "data") else values
        if actual_val is None:
            print("Unable to collect data.")
            continue
        if isinstance(actual_val, dict):
            for k, v in actual_val.items():
                print(f"{k:20}: {v}")
        elif isinstance(actual_val, list):
            print(f"Total items: {len(actual_val)}")
