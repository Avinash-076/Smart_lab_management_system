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
    ENABLE_HARDWARE_INFO,
    ENABLE_ISSUE_REPORTING,
    ENABLE_NETWORK_INFO,
    ENABLE_PROCESS_INFO,
    ENABLE_SOFTWARE_INFO,
    ENABLE_USAGE_INFO,
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
from core.outbox import DurableOutbox, OutboxDeliveryWorker, OutboxPriority
from core.outbox.models import OutboxRecord, OutboxStatus
from modules.issues import (
    record_issue_delivered,
    record_issue_enqueued,
)
from modules.software import (
    compute_software_fingerprint,
    load_software_state,
    record_software_delivered,
    record_software_enqueued,
    save_software_state,
)
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
    if not ENABLE_HARDWARE_INFO and not ENABLE_NETWORK_INFO:
        return False

    hardware_entry = data.get("hardware")
    if hasattr(hardware_entry, "is_failed") and hardware_entry.is_failed:
        logger.warning(f"Skipping metrics upload: hardware collector reported failure ({hardware_entry.error})")
        return False
    if hardware_entry is None and ENABLE_HARDWARE_INFO:
        logger.warning("Skipping metrics upload: hardware data is None.")
        return False

    try:
        metric_payload = build_metric_payload(data)
    except Exception as e:
        logger.warning(f"Skipping metrics upload: cannot build metric payload ({e})")
        return False

    if outbox is not None:
        try:
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
        send_metrics(metric_payload, token_holder.token)
        logger.info("Metrics sent successfully.")
        return True
    except HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            logger.warning("Access token expired during metrics upload. Re-authenticating...")
            try:
                token_holder.token = authenticate_agent()
                send_metrics(metric_payload, token_holder.token)
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
    state_file: str | None = None,
    force: bool = False,
) -> bool:
    if not ENABLE_SOFTWARE_INFO:
        return False
    software_entry = data.get("software")
    if software_entry is None:
        return False
    if hasattr(software_entry, "is_failed") and software_entry.is_failed:
        logger.warning(f"Skipping software upload: software collector reported failure ({software_entry.error})")
        return False
    software = software_entry.data if hasattr(software_entry, "data") else software_entry
    if software is None:
        return False

    # E-06: Compute deterministic fingerprint
    fingerprint = compute_software_fingerprint(software)
    state = load_software_state(state_file)
    last_delivered = state.get("last_delivered_fingerprint")

    # If this exact inventory has already been successfully delivered, skip upload
    if not force and last_delivered is not None and last_delivered == fingerprint:
        logger.info(
            f"Software inventory unchanged (already delivered, fingerprint={fingerprint[:12]}...); skipping upload."
        )
        return False

    # Asynchronous outbox delivery mode
    if outbox is not None:
        try:
            comp_id = get_computer_id()
            key = f"software_{comp_id}_{fingerprint[:16]}"

            # Check if record already exists in outbox
            existing_record = outbox.get_record_by_idempotency_key(key)
            if existing_record is not None:
                from core.outbox.models import OutboxStatus
                if existing_record.status == OutboxStatus.DEAD_LETTER:
                    logger.warning(
                        f"Software inventory outbox record {existing_record.id} was DEAD_LETTER; "
                        "requeuing for active delivery."
                    )
                    outbox.requeue_dead_letter(existing_record.id)
                    record_software_enqueued(fingerprint, state_file)
                    return True
                elif existing_record.status in (OutboxStatus.PENDING, OutboxStatus.PROCESSING):
                    logger.info(
                        f"Software inventory already pending in outbox (id={existing_record.id}, "
                        f"fingerprint={fingerprint[:12]}...); awaiting delivery."
                    )
                    record_software_enqueued(fingerprint, state_file)
                    return False

            outbox.enqueue(
                event_type="software",
                payload={"software": software},
                idempotency_key=key,
                priority=OutboxPriority.TELEMETRY,
            )
            logger.info("Software inventory enqueued to durable outbox.")
            record_software_enqueued(fingerprint, state_file)
            return True
        except Exception as e:
            logger.exception(f"Failed to enqueue software to outbox: {e}")
            return False

    # Direct synchronous upload mode (outbox is None)
    try:
        send_software_inventory(software, token_holder.token)
        logger.info("Software inventory sent successfully.")
        record_software_delivered(fingerprint, state_file)
        return True
    except HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            try:
                token_holder.token = authenticate_agent()
                send_software_inventory(software, token_holder.token)
                record_software_delivered(fingerprint, state_file)
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
    processes_entry = data.get("processes")
    if processes_entry is None:
        return False
    if hasattr(processes_entry, "is_failed") and processes_entry.is_failed:
        logger.warning(f"Skipping process upload: process collector reported failure ({processes_entry.error})")
        return False
    processes = processes_entry.data if hasattr(processes_entry, "data") else processes_entry
    if processes is None:
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
    usage_entry = data.get("usage")
    if hasattr(usage_entry, "is_failed") and usage_entry.is_failed:
        logger.warning(f"Skipping usage upload: usage collector reported failure ({usage_entry.error})")
        return False
    usage = usage_entry.data if hasattr(usage_entry, "data") else usage_entry
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
    state_file: str | None = None,
) -> bool:
    if not ENABLE_ISSUE_REPORTING:
        return False
    issues_entry = data.get("issues")
    if hasattr(issues_entry, "is_failed") and issues_entry.is_failed:
        logger.warning(f"Skipping issue upload: issue detector reported failure ({issues_entry.error})")
        return False
    issues = issues_entry.data if hasattr(issues_entry, "data") else issues_entry
    if not issues:
        return False

    if outbox is not None:
        all_enqueued = True
        for issue in issues:
            try:
                comp_id = get_computer_id()
                issue_key = issue.get("issue_key", "unknown")
                incident_id = issue.get("incident_id") or "legacy"
                key = f"issue_{comp_id}_{issue_key}_{incident_id}"
                issue["idempotency_key"] = key

                # Check if record already exists in outbox (F-02)
                existing_record = outbox.get_record_by_idempotency_key(key)
                if existing_record is not None:
                    if existing_record.status == OutboxStatus.DEAD_LETTER:
                        logger.warning(
                            f"Issue outbox record {existing_record.id} ({key}) was DEAD_LETTER; "
                            "requeuing for active delivery."
                        )
                        outbox.requeue_dead_letter(existing_record.id)
                        record_issue_enqueued(issue_key, incident_id, state_file)
                        continue
                    elif existing_record.status in (OutboxStatus.PENDING, OutboxStatus.PROCESSING):
                        logger.info(
                            f"Issue already pending in outbox (id={existing_record.id}, key={key}); "
                            "awaiting delivery."
                        )
                        record_issue_enqueued(issue_key, incident_id, state_file)
                        continue
                    elif existing_record.status == OutboxStatus.DELIVERED:
                        logger.info(
                            f"Issue already delivered according to outbox (id={existing_record.id}, key={key})."
                        )
                        record_issue_delivered(issue_key, incident_id, state_file)
                        continue

                outbox.enqueue(
                    event_type="issue",
                    payload=issue,
                    idempotency_key=key,
                    priority=OutboxPriority.ISSUE,
                )
                logger.info(f"Issue report enqueued to durable outbox (key={key}).")
                record_issue_enqueued(issue_key, incident_id, state_file)
            except Exception as e:
                logger.exception(f"Failed to enqueue issue to outbox: {e}")
                all_enqueued = False
        return all_enqueued

    all_sent = True
    for issue in issues:
        try:
            comp_id = get_computer_id()
            issue_key = issue.get("issue_key", "unknown")
            incident_id = issue.get("incident_id") or "legacy"
            key = f"issue_{comp_id}_{issue_key}_{incident_id}"
            issue["idempotency_key"] = key
            send_issue(issue, token_holder.token)
            logger.info(f"Issue report sent successfully (key={key}).")
            record_issue_delivered(issue_key, incident_id, state_file)
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
        process_interval: float = PROCESS_COLLECTION_INTERVAL,
        software_interval: float = SOFTWARE_SCAN_INTERVAL,
        software_state_file: str | None = None,
        issue_state_file: str | None = None,
    ):
        self.stop_event = stop_event or threading.Event()
        self.is_service = is_service
        self.enable_outbox = enable_outbox
        self.outbox = outbox if (outbox is not None or not enable_outbox) else DurableOutbox()
        self.process_interval = process_interval
        self.software_interval = software_interval
        self.software_state_file = software_state_file
        self.issue_state_file = issue_state_file
        self._last_process_collection: float | None = None
        self._last_software_scan: float | None = None
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

    def due_for_process_collection(self, now: float | None = None) -> bool:
        """
        Check if process inventory collection is due based on cadence (E-01).
        Triggers on initial run, then every process_interval seconds.
        """
        if now is None:
            now = time.monotonic()
        if self._last_process_collection is None:
            return True
        return (now - self._last_process_collection) >= self.process_interval

    def due_for_software_scan(self, now: float | None = None) -> bool:
        """
        Check if software inventory scan is due based on cadence (E-05).
        Triggers on initial run, then every software_interval seconds.
        """
        if now is None:
            now = time.monotonic()
        if self._last_software_scan is None:
            return True
        return (now - self._last_software_scan) >= self.software_interval

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

            # Delivery confirmation callback
            def _handle_outbox_delivered(item: OutboxRecord) -> None:
                if item.event_type == "software":
                    software_list = item.payload.get("software")
                    if software_list is not None:
                        fp = compute_software_fingerprint(software_list)
                        record_software_delivered(fp, self.software_state_file)
                        logger.info(
                            f"Software inventory delivery confirmed by outbox (fingerprint={fp[:12]}...)."
                        )
                elif item.event_type == "issue":
                    issue_key = item.payload.get("issue_key")
                    incident_id = item.payload.get("incident_id")
                    if issue_key and incident_id:
                        record_issue_delivered(issue_key, incident_id, self.issue_state_file)
                        logger.info(
                            f"Issue delivery confirmed by outbox (key={issue_key}, incident={incident_id})."
                        )

            # Start Outbox Delivery Worker
            if self.enable_outbox and self.outbox:
                self.delivery_worker = OutboxDeliveryWorker(
                    outbox=self.outbox,
                    get_token=lambda: self.token_holder.token if self.token_holder else "",
                    refresh_token=self._refresh_token_safe,
                    stop_event=self.stop_event,
                    on_delivered=_handle_outbox_delivered,
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
                loop_now = time.monotonic()

                # ----------------------------------------------------
                # Token Refresh Check
                # ----------------------------------------------------
                if loop_now - token_acquired_at > TOKEN_REFRESH_INTERVAL:
                    try:
                        logger.info("Refreshing access token...")
                        self.token_holder.token = authenticate_agent()
                        token_acquired_at = loop_now
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
                # Cadence Gating (E-01, E-05)
                # ----------------------------------------------------
                due_proc = self.due_for_process_collection(loop_now)
                due_sw = self.due_for_software_scan(loop_now)

                # ----------------------------------------------------
                # Data Collection
                # ----------------------------------------------------
                logger.info("Collecting system information...")
                data = collect_all_data(
                    include_processes=due_proc,
                    include_software=due_sw,
                    issue_state_file=self.issue_state_file,
                )
                logger.info("Data collection completed.")

                if due_proc:
                    self._last_process_collection = loop_now
                if due_sw:
                    self._last_software_scan = loop_now

                # ----------------------------------------------------
                # Uploads
                # ----------------------------------------------------
                active_outbox = self.outbox if self.enable_outbox else None
                upload_metrics(data, self.token_holder, outbox=active_outbox)
                if due_sw:
                    upload_software(
                        data,
                        self.token_holder,
                        outbox=active_outbox,
                        state_file=self.software_state_file,
                    )
                if due_proc:
                    upload_processes(data, self.token_holder, outbox=active_outbox)
                upload_usage(data, self.token_holder, outbox=active_outbox)
                upload_issues(
                    data,
                    self.token_holder,
                    outbox=active_outbox,
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
