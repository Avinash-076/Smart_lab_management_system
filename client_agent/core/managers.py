"""
SLMS Client Agent Modular Runtime Managers.

Deconstructs monolithic runtime responsibilities (H-01, H-02, H-03, H-05) into
bounded, isolated, single-responsibility components:
- TokenManager: Thread-safe token acquisition, access, and periodic/on-demand refresh.
- OutboxManager: Encapsulates durable local SQLite outbox and delivery worker.
- WebSocketManager: Manages AgentWebSocketClient lifecycle and connection observability.
- CollectorManager: Bounded execution of fast vs. cadenced system data collectors (H-02).
- UploadManager: Telemetry payload serialization, priority, idempotency, and dispatch (H-03).
- ShutdownManager: Staged, idempotent, graceful shutdown coordination.
"""

from __future__ import annotations

import concurrent.futures
import threading
import time
from typing import Any, Callable
import uuid

from requests.exceptions import HTTPError

from config import (
    ENABLE_HARDWARE_INFO,
    ENABLE_ISSUE_REPORTING,
    ENABLE_NETWORK_INFO,
    ENABLE_PROCESS_INFO,
    ENABLE_SOFTWARE_INFO,
    ENABLE_SYSTEM_INFO,
    ENABLE_USAGE_INFO,
)
from core.collector import (
    _collect_processes,
    _collect_software,
    ProcessCache,
    SoftwareCache,
)
from core.credentials import get_credential_store
from core.health import safe_run
from core.logger import logger
from core.outbox import DurableOutbox, OutboxDeliveryWorker, OutboxPriority
from core.outbox.models import OutboxRecord, OutboxStatus
from modules.hardware import get_hardware_info
from modules.issues import (
    detect_issues,
    record_issue_delivered,
    record_issue_enqueued,
)
from modules.network import get_network_info
from modules.software import (
    compute_software_fingerprint,
    load_software_state,
    record_software_delivered,
    record_software_enqueued,
)
from modules.system_info import get_system_info
from modules.usage import collect_usage_sessions
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


def _resolve_computer_id() -> int:
    fn = None
    try:
        import core.runtime as rt
        fn = getattr(rt, "get_computer_id", None)
    except Exception:
        pass
    if fn is not None:
        return fn()
    return get_computer_id()


def _resolve_authenticate_agent() -> str:
    fn = None
    try:
        import core.runtime as rt
        fn = getattr(rt, "authenticate_agent", None)
    except Exception:
        pass
    if fn is not None:
        return fn()
    return authenticate_agent()


def _resolve_send_issue(issue: dict[str, Any], token: str) -> dict[str, Any]:
    fn = None
    try:
        import core.runtime as rt
        fn = getattr(rt, "send_issue", None)
    except Exception:
        pass
    if fn is not None:
        return fn(issue, token)
    return send_issue(issue, token)


def _resolve_send_software_inventory(software: list[dict[str, Any]], token: str) -> Any:
    fn = None
    try:
        import core.runtime as rt
        fn = getattr(rt, "send_software_inventory", None)
    except Exception:
        pass
    if fn is not None:
        return fn(software, token)
    return send_software_inventory(software, token)


def _resolve_send_process_inventory(processes: list[dict[str, Any]], token: str) -> Any:
    fn = None
    try:
        import core.runtime as rt
        fn = getattr(rt, "send_process_inventory", None)
    except Exception:
        pass
    if fn is not None:
        return fn(processes, token)
    return send_process_inventory(processes, token)


def _resolve_send_usage_sessions(sessions: list[dict[str, Any]], token: str) -> Any:
    fn = None
    try:
        import core.runtime as rt
        fn = getattr(rt, "send_usage_sessions", None)
    except Exception:
        pass
    if fn is not None:
        return fn(sessions, token)
    return send_usage_sessions(sessions, token)


def _resolve_send_metrics(payload: dict[str, Any], token: str) -> dict[str, Any]:
    fn = None
    try:
        import core.runtime as rt
        fn = getattr(rt, "send_metrics", None)
    except Exception:
        pass
    if fn is not None:
        return fn(payload, token)
    return send_metrics(payload, token)


# ============================================================================
# TokenManager
# ============================================================================

class TokenHolder:
    """Thread-safe container for the active JWT access token."""

    def __init__(self, token: str):
        self._lock = threading.Lock()
        self._token = token

    @property
    def token(self) -> str:
        with self._lock:
            return self._token

    @token.setter
    def token(self, value: str) -> None:
        with self._lock:
            self._token = value


class TokenManager:
    """
    Manages authentication token acquisition, thread-safe access,
    periodic refresh, and on-demand refresh coordination.
    """

    def __init__(
        self,
        token_holder: TokenHolder | None = None,
        refresh_interval: float = TOKEN_REFRESH_INTERVAL,
    ):
        self.token_holder = token_holder or TokenHolder("")
        self.refresh_interval = refresh_interval
        self._last_refresh: float = time.monotonic()
        self._lock = threading.Lock()

    @property
    def token(self) -> str:
        return self.token_holder.token

    def set_token(self, new_token: str) -> None:
        with self._lock:
            self.token_holder.token = new_token
            self._last_refresh = time.monotonic()

    def refresh(self) -> str:
        """Force synchronous authentication and update token holder."""
        with self._lock:
            token = _resolve_authenticate_agent()
            self.token_holder.token = token
            self._last_refresh = time.monotonic()
            return token

    def refresh_if_due(self, now: float | None = None) -> bool:
        """Check if token refresh interval has elapsed and refresh if needed."""
        if now is None:
            now = time.monotonic()
        with self._lock:
            if now - self._last_refresh > self.refresh_interval:
                try:
                    logger.info("Refreshing access token on scheduled cadence...")
                    token = _resolve_authenticate_agent()
                    self.token_holder.token = token
                    self._last_refresh = now
                    return True
                except Exception as exc:
                    logger.exception(f"Scheduled token refresh failed: {exc}")
                    return False
        return False


# ============================================================================
# OutboxManager
# ============================================================================

class OutboxManager:
    """
    Manages durable local persistence and background delivery workers.
    Wraps Phase 3 DurableOutbox and OutboxDeliveryWorker without modifying schemas.
    """

    def __init__(
        self,
        outbox: DurableOutbox | None = None,
        enable_outbox: bool = True,
        software_state_file: str | None = None,
        issue_state_file: str | None = None,
    ):
        self.enabled = enable_outbox
        self.outbox = outbox if (outbox is not None or not enable_outbox) else DurableOutbox()
        self.delivery_worker: OutboxDeliveryWorker | None = None
        self.software_state_file = software_state_file
        self.issue_state_file = issue_state_file
        self._lock = threading.Lock()

    @property
    def enable_outbox(self) -> bool:
        """Compatibility property for enable_outbox."""
        return self.enabled

    def start(
        self,
        token_manager: TokenManager,
        stop_event: threading.Event,
    ) -> None:
        """Start outbox delivery worker if outbox is enabled."""
        with self._lock:
            if not self.enabled or not self.outbox:
                return
            if self.delivery_worker is not None and self.delivery_worker.is_running:
                return

            def _handle_delivered(item: OutboxRecord) -> None:
                if item.event_type == "software":
                    software_list = item.payload.get("software")
                    if software_list is not None:
                        fp = compute_software_fingerprint(software_list)
                        record_software_delivered(fp, self.software_state_file)
                        logger.info(f"Software inventory delivery confirmed (fp={fp[:12]}...).")
                elif item.event_type == "issue":
                    issue_key = item.payload.get("issue_key")
                    incident_id = item.payload.get("incident_id")
                    if issue_key and incident_id:
                        record_issue_delivered(issue_key, incident_id, self.issue_state_file)
                        logger.info(f"Issue delivery confirmed (key={issue_key}, incident={incident_id}).")

            self.delivery_worker = OutboxDeliveryWorker(
                outbox=self.outbox,
                get_token=lambda: token_manager.token,
                refresh_token=token_manager.refresh,
                stop_event=stop_event,
                on_delivered=_handle_delivered,
            )
            self.delivery_worker.start()
            logger.info("OutboxManager delivery worker started.")

    def stop(self, timeout: float = 5.0) -> None:
        """Stop outbox delivery worker cleanly."""
        with self._lock:
            if self.delivery_worker:
                try:
                    self.delivery_worker.stop(timeout=timeout)
                except Exception as exc:
                    logger.warning(f"Error stopping delivery worker: {exc}")
                self.delivery_worker = None
            logger.info("OutboxManager delivery worker stopped.")


# ============================================================================
# WebSocketManager
# ============================================================================

class WebSocketManager:
    """
    Orchestrates the Phase 7 AgentWebSocketClient lifecycle and state visibility.
    """

    def __init__(self):
        self.ws_client: AgentWebSocketClient | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> WebSocketState | None:
        with self._lock:
            return self.ws_client.state if self.ws_client else None

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self.ws_client.is_connected if self.ws_client else False

    def start(
        self,
        computer_id: int,
        token_manager: TokenManager,
        outbox_manager: OutboxManager,
    ) -> None:
        """Instantiate and start the WebSocket client."""
        with self._lock:
            if self.ws_client is not None and self.ws_client.is_connected:
                return

            import core.runtime as rt
            ws_cls = getattr(rt, "AgentWebSocketClient", AgentWebSocketClient)
            is_enrolled_fn = getattr(rt, "is_enrolled", is_enrolled)

            client = ws_cls(
                computer_id=computer_id,
                get_token=lambda: token_manager.token,
                refresh_token=token_manager.refresh,
                outbox=outbox_manager.outbox if outbox_manager.enabled else None,
                is_enrolled=is_enrolled_fn,
            )
            if client is not None:
                client.start()
            self.ws_client = client
            logger.info("WebSocketManager started client.")

    def stop(self) -> None:
        """Stop WebSocket client connection and workers."""
        with self._lock:
            if self.ws_client:
                try:
                    self.ws_client.stop()
                except Exception as exc:
                    logger.warning(f"Error stopping WebSocket client: {exc}")
                self.ws_client = None
            logger.info("WebSocketManager stopped client.")


# ============================================================================
# CollectorManager (H-02, H-05)
# ============================================================================

class CollectorManager:
    """
    Manages collector execution via a bounded worker pool.
    Separates fast real-time telemetry from slow cadenced scans (H-02).
    Enforces hardware -> issue evaluation dependency sequence.
    """

    def __init__(self, max_workers: int = 2):
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="SLMS-Collector",
        )
        self.software_cache = SoftwareCache()
        self.process_cache = ProcessCache()
        self._lock = threading.Lock()
        self._is_stopped = False

    def collect_telemetry(self, issue_state_file: str | None = None) -> dict[str, Any]:
        """
        Execute fast real-time 20-second telemetry collection.
        CRITICAL: Evaluates hardware collection before issue detection.
        """
        import core.runtime as rt
        collect_fn = getattr(rt, "collect_all_data", None)
        from core.collector import collect_all_data as default_collect
        if collect_fn is not None and collect_fn is not default_collect:
            return collect_fn(
                include_software=False,
                include_processes=False,
                software_cache=self.software_cache,
                process_cache=self.process_cache,
                issue_state_file=issue_state_file,
            )

        data: dict[str, Any] = {}

        if ENABLE_SYSTEM_INFO:
            data["system"] = safe_run("System Information", get_system_info)

        if ENABLE_HARDWARE_INFO:
            data["hardware"] = safe_run("Hardware Information", get_hardware_info)

        if ENABLE_NETWORK_INFO:
            data["network"] = safe_run("Network Information", get_network_info)

        if ENABLE_USAGE_INFO:
            data["usage"] = safe_run("Application Usage", collect_usage_sessions)

        # Issue detection strictly AFTER hardware collection has populated metrics
        if ENABLE_ISSUE_REPORTING:
            data["issues"] = safe_run(
                "Problem Detection",
                lambda: detect_issues(data, state_file=issue_state_file),
            )

        return data

    def collect_processes(self) -> list[dict[str, Any]]:
        """Collect running process inventory using bounded process cache."""
        res = safe_run("Running Processes", lambda: _collect_processes(cache=self.process_cache))
        if hasattr(res, "data"):
            return res.data or []
        return res if isinstance(res, list) else []

    def collect_software(self) -> list[dict[str, Any]]:
        """Collect installed software inventory using bounded software cache."""
        res = safe_run("Installed Software", lambda: _collect_software(cache=self.software_cache))
        if hasattr(res, "data"):
            return res.data or []
        return res if isinstance(res, list) else []

    def submit_task(
        self,
        fn: Callable[..., Any],
        *args: Any,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> concurrent.futures.Future | None:
        """Submit background collection task to bounded thread pool."""
        with self._lock:
            if self._is_stopped:
                logger.warning("CollectorManager is stopped; rejecting task submission.")
                return None

            def _task_wrapper():
                try:
                    result = fn(*args)
                    if on_success:
                        on_success(result)
                    return result
                except Exception as exc:
                    logger.exception(f"Error in background collector task: {exc}")
                    if on_error:
                        on_error(exc)
                    raise

            try:
                return self._executor.submit(_task_wrapper)
            except Exception as submit_err:
                logger.error(f"Failed to submit task to CollectorManager executor: {submit_err}")
                return None

    def stop(self, timeout: float = 3.0) -> None:
        """Shutdown worker thread pool cleanly."""
        with self._lock:
            self._is_stopped = True
        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except Exception as exc:
            logger.warning(f"Error shutting down CollectorManager executor: {exc}")
        logger.info("CollectorManager stopped.")


# ============================================================================
# UploadManager (H-03)
# ============================================================================

class UploadManager:
    """
    Manages telemetry payload formatting, priority assignment, idempotency keys,
    and dispatch to OutboxManager (or direct HTTP fallback).
    """

    def upload_metrics(
        self,
        data: dict[str, Any],
        token_manager: TokenManager,
        outbox_manager: OutboxManager,
    ) -> bool:
        """Assemble and enqueue metrics telemetry."""
        if not ENABLE_HARDWARE_INFO and not ENABLE_NETWORK_INFO:
            return False

        hardware_entry = data.get("hardware")
        if hardware_entry is not None and getattr(hardware_entry, "is_failed", False):
            err = getattr(hardware_entry, "error", "unknown error")
            logger.warning(f"Skipping metrics upload: hardware collector reported failure ({err})")
            return False
        if hardware_entry is None and ENABLE_HARDWARE_INFO:
            logger.warning("Skipping metrics upload: hardware data is None.")
            return False

        try:
            metric_payload = build_metric_payload(data)
        except Exception as e:
            logger.warning(f"Skipping metrics upload: cannot build metric payload ({e})")
            return False

        if outbox_manager.enabled and outbox_manager.outbox is not None:
            try:
                comp_id = _resolve_computer_id()
                key = f"metric_{comp_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                outbox_manager.outbox.enqueue(
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

        # Synchronous HTTP fallback
        try:
            _resolve_send_metrics(metric_payload, token_manager.token)
            logger.info("Metrics sent successfully via direct HTTP.")
            return True
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                try:
                    token_manager.refresh()
                    _resolve_send_metrics(metric_payload, token_manager.token)
                    logger.info("Metrics sent after re-authentication.")
                    return True
                except Exception as retry_err:
                    logger.exception(f"Metrics retry failed: {retry_err}")
            else:
                logger.exception(f"Metrics upload failed: {e}")
        except Exception as e:
            logger.exception(f"Metrics upload failed: {e}")
        return False

    def upload_software(
        self,
        software: list[dict[str, Any]] | Any,
        token_manager: TokenManager,
        outbox_manager: OutboxManager,
        state_file: str | None = None,
        force: bool = False,
    ) -> bool:
        """Assemble and enqueue installed software inventory."""
        if not ENABLE_SOFTWARE_INFO:
            return False
        if isinstance(software, dict) and "software" in software:
            software = software["software"]
        software = getattr(software, "data", software)
        if not software or not isinstance(software, list):
            return False

        fingerprint = compute_software_fingerprint(software)
        state = load_software_state(state_file)
        last_delivered = state.get("last_delivered_fingerprint")

        if not force and last_delivered is not None and last_delivered == fingerprint:
            logger.info(f"Software inventory unchanged (already delivered, fp={fingerprint[:12]}...); skipping upload.")
            return False

        if outbox_manager.enabled and outbox_manager.outbox is not None:
            try:
                comp_id = _resolve_computer_id()
                key = f"software_{comp_id}_{fingerprint[:16]}"
                existing_record = outbox_manager.outbox.get_record_by_idempotency_key(key)
                if existing_record is not None:
                    if existing_record.status == OutboxStatus.DEAD_LETTER:
                        logger.warning(f"Software inventory record {existing_record.id} was DEAD_LETTER; requeuing.")
                        outbox_manager.outbox.requeue_dead_letter(existing_record.id)
                        record_software_enqueued(fingerprint, state_file)
                        return True
                    elif existing_record.status in (OutboxStatus.PENDING, OutboxStatus.PROCESSING):
                        logger.info(f"Software inventory already pending in outbox (id={existing_record.id}).")
                        record_software_enqueued(fingerprint, state_file)
                        return False

                outbox_manager.outbox.enqueue(
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

        # Direct HTTP fallback
        try:
            _resolve_send_software_inventory(software, token_manager.token)
            logger.info("Software inventory sent successfully.")
            record_software_delivered(fingerprint, state_file)
            return True
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                try:
                    token_manager.refresh()
                    _resolve_send_software_inventory(software, token_manager.token)
                    record_software_delivered(fingerprint, state_file)
                    return True
                except Exception as retry_err:
                    logger.exception(f"Software retry failed: {retry_err}")
            else:
                logger.exception(f"Software upload failed: {e}")
        except Exception as e:
            logger.exception(f"Software upload failed: {e}")
        return False

    def upload_processes(
        self,
        processes: list[dict[str, Any]] | Any,
        token_manager: TokenManager,
        outbox_manager: OutboxManager,
    ) -> bool:
        """Assemble and enqueue running process inventory."""
        if not ENABLE_PROCESS_INFO:
            return False
        if isinstance(processes, dict) and "processes" in processes:
            processes = processes["processes"]
        processes = getattr(processes, "data", processes)
        if not processes or not isinstance(processes, list):
            return False

        if outbox_manager.enabled and outbox_manager.outbox is not None:
            try:
                comp_id = _resolve_computer_id()
                key = f"processes_{comp_id}_{int(time.time())}"
                outbox_manager.outbox.enqueue(
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

        # Direct HTTP fallback
        try:
            _resolve_send_process_inventory(processes, token_manager.token)
            logger.info("Process inventory sent successfully.")
            return True
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                try:
                    token_manager.refresh()
                    _resolve_send_process_inventory(processes, token_manager.token)
                    return True
                except Exception as retry_err:
                    logger.exception(f"Processes retry failed: {retry_err}")
            else:
                logger.exception(f"Processes upload failed: {e}")
        except Exception as e:
            logger.exception(f"Processes upload failed: {e}")
        return False

    def upload_usage(
        self,
        usage: list[dict[str, Any]] | Any,
        token_manager: TokenManager,
        outbox_manager: OutboxManager,
    ) -> bool:
        """Assemble and enqueue application usage sessions."""
        if not ENABLE_USAGE_INFO:
            return False
        if isinstance(usage, dict) and "usage" in usage:
            usage = usage["usage"]
        usage = getattr(usage, "data", usage)
        if not usage or not isinstance(usage, list):
            return False

        if outbox_manager.enabled and outbox_manager.outbox is not None:
            try:
                comp_id = _resolve_computer_id()
                key = f"usage_{comp_id}_{int(time.time())}_{len(usage)}"
                outbox_manager.outbox.enqueue(
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

        # Direct HTTP fallback
        try:
            _resolve_send_usage_sessions(usage, token_manager.token)
            logger.info("Usage sessions sent successfully.")
            return True
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                try:
                    token_manager.refresh()
                    _resolve_send_usage_sessions(usage, token_manager.token)
                    return True
                except Exception as retry_err:
                    logger.exception(f"Usage retry failed: {retry_err}")
            else:
                logger.exception(f"Usage upload failed: {e}")
        except Exception as e:
            logger.exception(f"Usage upload failed: {e}")
        return False

    def upload_issues(
        self,
        issues: list[dict[str, Any]] | Any,
        token_manager: TokenManager,
        outbox_manager: OutboxManager,
        state_file: str | None = None,
    ) -> bool:
        """Assemble and enqueue detected problem issues."""
        if not ENABLE_ISSUE_REPORTING:
            return False
        if isinstance(issues, dict) and "issues" in issues:
            issues = issues["issues"]
        issues = getattr(issues, "data", issues)
        if not issues or not isinstance(issues, list):
            return False

        if outbox_manager.enabled and outbox_manager.outbox is not None:
            all_enqueued = True
            for issue in issues:
                try:
                    comp_id = _resolve_computer_id()
                    issue_key = issue.get("issue_key", "unknown")
                    incident_id = issue.get("incident_id") or "legacy"
                    key = f"issue_{comp_id}_{issue_key}_{incident_id}"
                    issue["idempotency_key"] = key

                    existing_record = outbox_manager.outbox.get_record_by_idempotency_key(key)
                    if existing_record is not None:
                        if existing_record.status == OutboxStatus.DEAD_LETTER:
                            outbox_manager.outbox.requeue_dead_letter(existing_record.id)
                            record_issue_enqueued(issue_key, incident_id, state_file)
                            continue
                        elif existing_record.status in (OutboxStatus.PENDING, OutboxStatus.PROCESSING):
                            record_issue_enqueued(issue_key, incident_id, state_file)
                            continue
                        elif existing_record.status == "DELIVERED":
                            record_issue_delivered(issue_key, incident_id, state_file)
                            continue

                    outbox_manager.outbox.enqueue(
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

        # Direct HTTP fallback
        all_sent = True
        for issue in issues:
            try:
                comp_id = _resolve_computer_id()
                issue_key = issue.get("issue_key", "unknown")
                incident_id = issue.get("incident_id") or "legacy"
                key = f"issue_{comp_id}_{issue_key}_{incident_id}"
                issue["idempotency_key"] = key
                _resolve_send_issue(issue, token_manager.token)
                logger.info(f"Issue report sent successfully (key={key}).")
                record_issue_delivered(issue_key, incident_id, state_file)
            except Exception as e:
                logger.exception(f"Issue upload failed: {e}")
                all_sent = False
        return all_sent

    def dispatch_telemetry(
        self,
        data: dict[str, Any],
        token_manager: TokenManager,
        outbox_manager: OutboxManager,
        issue_state_file: str | None = None,
    ) -> None:
        """Dispatch fast telemetry package (metrics, usage, issues) to outbox."""
        self.upload_metrics(data, token_manager, outbox_manager)

        usage = data.get("usage")
        if usage:
            self.upload_usage(usage, token_manager, outbox_manager)

        issues = data.get("issues")
        if issues:
            self.upload_issues(issues, token_manager, outbox_manager, state_file=issue_state_file)


# ============================================================================
# ShutdownManager
# ============================================================================

class ShutdownManager:
    """
    Coordinates staged, idempotent, graceful shutdown of all agent sub-managers.
    Execution order:
    1. Signal stop event
    2. Stop scheduler
    3. Stop collector manager
    4. Stop outbox delivery worker
    5. Stop WebSocket client
    """

    def __init__(self, stop_event: threading.Event):
        self.stop_event = stop_event
        self._lock = threading.Lock()
        self._has_shutdown = False

    @property
    def is_shut_down(self) -> bool:
        with self._lock:
            return self._has_shutdown

    def shutdown(
        self,
        scheduler: Any | None = None,
        collector_manager: CollectorManager | None = None,
        outbox_manager: OutboxManager | None = None,
        websocket_manager: WebSocketManager | None = None,
        timeout: float = 5.0,
    ) -> None:
        """Execute staged teardown in safe dependency order."""
        with self._lock:
            if self._has_shutdown:
                return
            self._has_shutdown = True

        logger.info("ShutdownManager: Beginning staged agent shutdown...")

        # 1. Signal stop event
        self.stop_event.set()

        # 2. Stop scheduler
        if scheduler:
            try:
                scheduler.stop(timeout=timeout)
            except Exception as exc:
                logger.warning(f"ShutdownManager: Error stopping scheduler: {exc}")

        # 3. Stop collector worker pool
        if collector_manager:
            try:
                collector_manager.stop(timeout=timeout)
            except Exception as exc:
                logger.warning(f"ShutdownManager: Error stopping collector manager: {exc}")

        # 4. Stop outbox delivery worker
        if outbox_manager:
            try:
                outbox_manager.stop(timeout=timeout)
            except Exception as exc:
                logger.warning(f"ShutdownManager: Error stopping outbox manager: {exc}")

        # 5. Stop WebSocket manager
        if websocket_manager:
            try:
                websocket_manager.stop()
            except Exception as exc:
                logger.warning(f"ShutdownManager: Error stopping websocket manager: {exc}")

        logger.info("ShutdownManager: All managers stopped cleanly.")
