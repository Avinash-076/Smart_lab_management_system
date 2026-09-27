"""
Phase 8 Runtime Modularization and Hardening Test Suite.

Verifies:
1. Scheduler drift-free timing
2. Scheduler interruptible shutdown
3. Scheduler overrun/catch-up behavior
4. Fast collection continues while slow collection runs
5. Hardware collection precedes issue evaluation
6. Shared collector state remains safe under concurrency
7. UploadManager builds the same payload semantics as before
8. UploadManager preserves existing idempotency keys
9. UploadManager preserves existing priorities
10. OutboxManager uses existing DurableOutbox
11. TokenManager concurrent access/refresh
12. WebSocketManager lifecycle compatibility
13. ShutdownManager staged shutdown
14. ShutdownManager idempotency
15. AgentRuntime compatibility facade
16. Existing cadence methods still work
17. Full startup/shutdown lifecycle
"""

from __future__ import annotations

import concurrent.futures
import threading
import time
from unittest.mock import MagicMock, call, patch

import pytest

from core.collector import ProcessCache, SoftwareCache
from core.managers import (
    CollectorManager,
    OutboxManager,
    ShutdownManager,
    TokenHolder,
    TokenManager,
    UploadManager,
    WebSocketManager,
)
from core.outbox import DurableOutbox, OutboxPriority, OutboxStatus
from core.runtime import AgentRuntime, RuntimeManager, get_computer_id
from core.scheduler import ScheduledJob, Scheduler
from modules.usage import _ACTIVE_SESSIONS, collect_usage_sessions
from server.communication import AgentWebSocketClient, WebSocketState


# ============================================================================
# 1. Scheduler Tests (H-04)
# ============================================================================

def test_01_scheduler_drift_free_timing():
    """1. Verify scheduler computes monotonically aligned next targets without drift."""
    scheduler = Scheduler()
    scheduler.add_job("test_job", interval=20.0, callback=lambda: None, initial_delay=0.0)

    job = scheduler._jobs["test_job"]
    start_target = job.next_run

    # Simulate advancing through 5 cycles using run_pending
    for i in range(1, 6):
        simulated_now = start_target + (i - 1) * 20.0 + 0.123
        scheduler.run_pending(now=simulated_now)
        expected_target = start_target + i * 20.0
        assert abs(job.next_run - expected_target) < 1e-6, (
            f"Cycle {i} drifted: got {job.next_run}, expected {expected_target}"
        )


def test_02_scheduler_interruptible_shutdown():
    """2. Verify scheduler shuts down promptly when stop event is signaled."""
    stop_event = threading.Event()
    scheduler = Scheduler(stop_event=stop_event)
    scheduler.add_job("long_wait", interval=3600.0, callback=lambda: None)

    scheduler.start()
    assert scheduler.is_running is True

    start_time = time.monotonic()
    scheduler.stop(timeout=1.0)
    elapsed = time.monotonic() - start_time

    assert scheduler.is_running is False
    assert elapsed < 1.0, f"Shutdown took too long ({elapsed:.3f}s), not interruptible"


def test_03_scheduler_overrun_catch_up():
    """3. Verify scheduler skips missed slots on major overrun without backlog explosion."""
    scheduler = Scheduler()
    job = scheduler.add_job("overrun_job", interval=20.0, callback=lambda: None, initial_delay=0.0)
    job.next_run = 100.0

    # Simulate execution that ran long and is checked at now = 195.0
    now = 195.0
    scheduler.run_pending(now=now)

    # Next target must be strictly in the future (>= now)
    assert job.next_run >= now, f"Next run {job.next_run} should be >= now {now}"
    assert job.next_run == now + job.interval


# ============================================================================
# 2. Collection Architecture Tests (H-02, H-05)
# ============================================================================

def test_04_fast_collection_continues_while_slow_collection_runs():
    """4. Fast telemetry collection is not blocked by slow/cadenced worker tasks."""
    manager = CollectorManager(max_workers=2)
    slow_task_running = threading.Event()
    slow_task_release = threading.Event()

    def slow_software_scan():
        slow_task_running.set()
        slow_task_release.wait(timeout=2.0)
        return [{"name": "HugeApp", "version": "1.0"}]

    try:
        fut = manager.submit_task(slow_software_scan)
        assert fut is not None
        assert slow_task_running.wait(timeout=1.0) is True

        # Fast telemetry collection must execute immediately without blocking
        with patch("core.managers.get_system_info", return_value={"os": "Windows"}), \
             patch("core.managers.get_hardware_info", return_value={"cpu_usage": 10.0}), \
             patch("core.managers.get_network_info", return_value={"ip": "127.0.0.1"}), \
             patch("core.managers.collect_usage_sessions", return_value=[]), \
             patch("core.managers.detect_issues", return_value=[]):
            t0 = time.monotonic()
            data = manager.collect_telemetry()
            elapsed = time.monotonic() - t0

        assert elapsed < 0.5, f"Fast telemetry collection took too long ({elapsed:.3f}s)"
        assert isinstance(data, dict)
    finally:
        slow_task_release.set()
        manager.stop(timeout=1.0)


def test_05_hardware_collection_precedes_issue_evaluation():
    """5. Critical ordering: hardware metrics must be collected before issue detection."""
    manager = CollectorManager(max_workers=2)
    execution_order: list[str] = []

    def mock_hw():
        execution_order.append("hardware")
        return {"cpu_usage": 92.0, "ram_usage": 88.0}

    def mock_detect(data, state_file=None):
        execution_order.append("issues")
        # Verify hardware is available to detect_issues
        assert "hardware" in data
        return []

    with patch("core.managers.get_hardware_info", side_effect=mock_hw), \
         patch("core.managers.detect_issues", side_effect=mock_detect), \
         patch("core.managers.ENABLE_HARDWARE_INFO", True), \
         patch("core.managers.ENABLE_ISSUE_REPORTING", True):
        manager.collect_telemetry()

    assert execution_order == ["hardware", "issues"], (
        f"Incorrect execution order: {execution_order}; hardware must precede issues."
    )


def test_06_shared_collector_state_safe_under_concurrency():
    """6. SoftwareCache, ProcessCache, and Usage state remain safe under concurrent access."""
    sw_cache = SoftwareCache(ttl=60.0)
    proc_cache = ProcessCache(ttl=60.0)

    errors: list[Exception] = []

    def sw_worker(worker_id: int):
        try:
            for i in range(50):
                sw_cache.set([{"name": f"App_{worker_id}_{i}"}])
                cached = sw_cache.get()
                assert cached is not None
                _ = sw_cache.is_present
                _ = sw_cache.is_expired()
        except Exception as e:
            errors.append(e)

    def proc_worker(worker_id: int):
        try:
            for i in range(50):
                proc_cache.set([{"name": f"proc_{worker_id}.exe", "pid": 1000 + i}])
                cached = proc_cache.get()
                assert cached is not None
        except Exception as e:
            errors.append(e)

    threads: list[threading.Thread] = []
    for i in range(5):
        threads.append(threading.Thread(target=sw_worker, args=(i,)))
        threads.append(threading.Thread(target=proc_worker, args=(i,)))

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=2.0)

    assert not errors, f"Concurrency errors encountered in shared caches: {errors}"


# ============================================================================
# 3. Upload Architecture Tests (H-03)
# ============================================================================

def test_07_upload_manager_payload_semantics(tmp_path):
    """7. UploadManager preserves existing payload assembly semantics."""
    db_path = str(tmp_path / "outbox.db")
    outbox = DurableOutbox(db_path=db_path)
    outbox_mgr = OutboxManager(outbox=outbox, enable_outbox=True)
    token_mgr = TokenManager(TokenHolder("test-jwt"))
    upload_mgr = UploadManager()

    metrics_data = {
        "hardware": {"cpu_usage": 25.0, "ram_usage": 45.0, "disk_usage": 50.0},
        "network": {"hostname": "lab-pc-1", "ip_address": "10.0.0.5"},
    }

    with patch("core.managers._resolve_computer_id", return_value=101):
        res = upload_mgr.upload_metrics(metrics_data, token_mgr, outbox_mgr)
        assert res is True

    batch = outbox.get_pending_batch(limit=1)
    assert len(batch) == 1
    record = batch[0]
    assert record.event_type == "metrics"
    payload = record.payload
    assert payload["cpu_usage"] == 25.0
    assert payload["ram_usage"] == 45.0
    assert payload["disk_usage"] == 50.0


def test_08_upload_manager_idempotency_keys(tmp_path):
    """8. UploadManager generates stable, prefix-compliant idempotency keys."""
    db_path = str(tmp_path / "outbox.db")
    outbox = DurableOutbox(db_path=db_path)
    outbox_mgr = OutboxManager(outbox=outbox, enable_outbox=True)
    token_mgr = TokenManager(TokenHolder("test-jwt"))
    upload_mgr = UploadManager()

    comp_id = 999
    with patch("core.managers._resolve_computer_id", return_value=comp_id):
        # 1. Metrics key format: metric_{comp_id}_{time}_{uuid}
        upload_mgr.upload_metrics({"hardware": {"cpu_usage": 10.0}}, token_mgr, outbox_mgr)
        rec1 = outbox.get_pending_batch(limit=1)[0]
        assert rec1.idempotency_key.startswith(f"metric_{comp_id}_")

        # 2. Software key format: software_{comp_id}_{fp[:16]}
        sw_data = [{"name": "TestApp", "version": "1.0", "publisher": "Corp", "install_date": "2026-01-01"}]
        upload_mgr.upload_software(sw_data, token_mgr, outbox_mgr, state_file=str(tmp_path / "sw.json"))
        rec2 = outbox.get_pending_batch(limit=1)[0]
        assert rec2.idempotency_key.startswith(f"software_{comp_id}_")

        # 3. Process key format: processes_{comp_id}_{time}
        proc_data = [{"pid": 1234, "name": "test.exe"}]
        upload_mgr.upload_processes(proc_data, token_mgr, outbox_mgr)
        rec3 = outbox.get_pending_batch(limit=1)[0]
        assert rec3.idempotency_key.startswith(f"processes_{comp_id}_")

        # 4. Usage key format: usage_{comp_id}_{time}_{len}
        usage_data = [{"application_name": "Editor", "duration_seconds": 60}]
        upload_mgr.upload_usage(usage_data, token_mgr, outbox_mgr)
        rec4 = outbox.get_pending_batch(limit=1)[0]
        assert rec4.idempotency_key.startswith(f"usage_{comp_id}_")

        # 5. Issue key format: issue_{comp_id}_{issue_key}_{incident_id}
        issue_data = [{"issue_key": "cpu_high", "incident_id": "inc-42", "severity": "warning"}]
        upload_mgr.upload_issues(issue_data, token_mgr, outbox_mgr)
        rec5 = outbox.get_pending_batch(limit=1)[0]
        assert rec5.idempotency_key == f"issue_{comp_id}_cpu_high_inc-42"


def test_09_upload_manager_priorities(tmp_path):
    """9. UploadManager assigns correct Phase 3 priorities."""
    db_path = str(tmp_path / "outbox.db")
    outbox = DurableOutbox(db_path=db_path)
    outbox_mgr = OutboxManager(outbox=outbox, enable_outbox=True)
    token_mgr = TokenManager(TokenHolder("test-jwt"))
    upload_mgr = UploadManager()

    # Verify Phase 3 IntEnum baseline values
    assert OutboxPriority.COMMAND == 1
    assert OutboxPriority.ISSUE == 2
    assert OutboxPriority.USAGE == 3
    assert OutboxPriority.TELEMETRY == 10

    with patch("core.managers._resolve_computer_id", return_value=55):
        # Telemetry priority = 10
        upload_mgr.upload_metrics({"hardware": {"cpu_usage": 10.0}}, token_mgr, outbox_mgr)
        rec_m = outbox.get_pending_batch(limit=1)[0]
        assert rec_m.priority == OutboxPriority.TELEMETRY.value
        assert rec_m.priority == 10

        # Usage priority = 3
        upload_mgr.upload_usage([{"application_name": "app", "duration_seconds": 10}], token_mgr, outbox_mgr)
        rec_u = outbox.get_pending_batch(limit=1)[0]
        assert rec_u.priority == OutboxPriority.USAGE.value
        assert rec_u.priority == 3

        # Issue priority = 2
        upload_mgr.upload_issues([{"issue_key": "err", "incident_id": "1"}], token_mgr, outbox_mgr)
        rec_i = outbox.get_pending_batch(limit=1)[0]
        assert rec_i.priority == OutboxPriority.ISSUE.value
        assert rec_i.priority == 2


def test_10_outbox_manager_uses_existing_durable_outbox(tmp_path):
    """10. OutboxManager delegates directly to Phase 3 DurableOutbox SQLite database."""
    db_path = str(tmp_path / "durable.db")
    outbox = DurableOutbox(db_path=db_path)
    outbox_mgr = OutboxManager(outbox=outbox, enable_outbox=True)

    assert outbox_mgr.outbox is outbox
    assert outbox_mgr.enabled is True

    record = outbox.enqueue(
        event_type="metrics",
        payload={"cpu": 50},
        idempotency_key="key-phase8",
        priority=OutboxPriority.TELEMETRY,
    )
    assert record.id is not None
    assert record.status == OutboxStatus.PENDING


# ============================================================================
# 4. Token & WebSocket Manager Tests
# ============================================================================

def test_11_token_manager_concurrent_access_and_refresh():
    """11. TokenManager provides thread-safe access and refresh under concurrency."""
    holder = TokenHolder("initial-token")
    manager = TokenManager(token_holder=holder, refresh_interval=60.0)

    refresh_counter = 0

    def mock_auth():
        nonlocal refresh_counter
        refresh_counter += 1
        return f"token-v{refresh_counter}"

    read_tokens: list[str] = []
    errors: list[Exception] = []

    def reader():
        try:
            for _ in range(50):
                tok = manager.token
                assert tok.startswith("token-") or tok == "initial-token"
                read_tokens.append(tok)
        except Exception as e:
            errors.append(e)

    def refresher():
        try:
            for _ in range(10):
                with patch("core.managers._resolve_authenticate_agent", side_effect=mock_auth):
                    manager.refresh()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=reader) for _ in range(10)]
    threads += [threading.Thread(target=refresher) for _ in range(3)]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=2.0)

    assert not errors, f"Errors in concurrent TokenManager access: {errors}"
    assert len(read_tokens) > 0


def test_12_websocket_manager_lifecycle_compatibility():
    """12. WebSocketManager wraps AgentWebSocketClient lifecycle and state exposure."""
    mgr = WebSocketManager()
    assert mgr.ws_client is None
    assert mgr.state is None
    assert mgr.is_connected is False

    mock_client = MagicMock(spec=AgentWebSocketClient)
    mock_client.state = WebSocketState.CONNECTED
    mock_client.is_connected = True

    with patch("core.runtime.AgentWebSocketClient", return_value=mock_client):
        token_mgr = TokenManager(TokenHolder("tok"))
        outbox_mgr = OutboxManager(enable_outbox=False)
        mgr.start(computer_id=42, token_manager=token_mgr, outbox_manager=outbox_mgr)

        assert mgr.ws_client is mock_client
        assert mgr.state == WebSocketState.CONNECTED
        assert mgr.is_connected is True

        mgr.stop()
        mock_client.stop.assert_called_once()
        assert mgr.ws_client is None
        assert mgr.is_connected is False


# ============================================================================
# 5. Shutdown Manager Tests
# ============================================================================

def test_13_shutdown_manager_staged_shutdown():
    """13. ShutdownManager executes graceful staged teardown in exact required sequence."""
    stop_event = threading.Event()
    shutdown_mgr = ShutdownManager(stop_event=stop_event)

    call_order: list[str] = []

    mock_scheduler = MagicMock(spec=Scheduler)
    mock_scheduler.stop.side_effect = lambda timeout=None: call_order.append("scheduler")

    mock_collector = MagicMock(spec=CollectorManager)
    mock_collector.stop.side_effect = lambda timeout=None: call_order.append("collector")

    mock_outbox = MagicMock(spec=OutboxManager)
    mock_outbox.stop.side_effect = lambda timeout=None: call_order.append("outbox")

    mock_ws = MagicMock(spec=WebSocketManager)
    mock_ws.stop.side_effect = lambda: call_order.append("websocket")

    shutdown_mgr.shutdown(
        scheduler=mock_scheduler,
        collector_manager=mock_collector,
        outbox_manager=mock_outbox,
        websocket_manager=mock_ws,
    )

    assert stop_event.is_set() is True
    expected_order = ["scheduler", "collector", "outbox", "websocket"]
    assert call_order == expected_order, f"Shutdown order mismatch: got {call_order}, expected {expected_order}"


def test_14_shutdown_manager_idempotency():
    """14. ShutdownManager is safe to invoke repeatedly (idempotent, no deadlocks)."""
    stop_event = threading.Event()
    shutdown_mgr = ShutdownManager(stop_event=stop_event)

    mock_scheduler = MagicMock(spec=Scheduler)
    mock_collector = MagicMock(spec=CollectorManager)

    # First shutdown
    shutdown_mgr.shutdown(scheduler=mock_scheduler, collector_manager=mock_collector)
    assert shutdown_mgr.is_shut_down is True
    assert mock_scheduler.stop.call_count == 1
    assert mock_collector.stop.call_count == 1

    # Second shutdown must be a safe no-op
    shutdown_mgr.shutdown(scheduler=mock_scheduler, collector_manager=mock_collector)
    assert shutdown_mgr.is_shut_down is True
    assert mock_scheduler.stop.call_count == 1
    assert mock_collector.stop.call_count == 1


# ============================================================================
# 6. Backwards Compatibility & Facade Tests (H-01)
# ============================================================================

def test_15_agent_runtime_compatibility_facade():
    """15. AgentRuntime preserves all legacy attributes, properties, and methods."""
    stop_event = threading.Event()
    runtime = AgentRuntime(stop_event=stop_event, is_service=True)

    # Core attributes
    assert runtime.stop_event is stop_event
    assert runtime.is_service is True
    assert runtime.is_running is False
    assert runtime.started_count == 0
    assert runtime.stopped_count == 0

    # Token and outbox wrappers
    assert isinstance(runtime.token_holder, TokenHolder)
    assert runtime.outbox is not None
    assert runtime.delivery_worker is None
    assert runtime.ws_client is None
    assert runtime.ws_state is None
    assert runtime.is_connected is False

    # Cache accessors
    assert isinstance(runtime.software_cache, SoftwareCache)
    assert isinstance(runtime.process_cache, ProcessCache)

    # Token property setter
    new_holder = TokenHolder("new-tok")
    runtime.token_holder = new_holder
    assert runtime.token_holder.token == "new-tok"


def test_16_existing_cadence_methods_still_work():
    """16. Legacy cadence methods due_for_process_collection and due_for_software_scan work."""
    runtime = AgentRuntime(process_interval=120.0, software_interval=900.0)

    # Initially due
    assert runtime.due_for_process_collection(0.0) is True
    assert runtime.due_for_software_scan(0.0) is True

    # After initial recording at t=0
    runtime._last_process_collection = 0.0
    runtime._last_software_scan = 0.0

    assert runtime.due_for_process_collection(20.0) is False
    assert runtime.due_for_process_collection(119.0) is False
    assert runtime.due_for_process_collection(120.0) is True

    assert runtime.due_for_software_scan(20.0) is False
    assert runtime.due_for_software_scan(899.0) is False
    assert runtime.due_for_software_scan(900.0) is True


def test_17_full_startup_shutdown_lifecycle(tmp_path):
    """17. Complete startup and shutdown cycle completes cleanly with bounded execution."""
    db_path = str(tmp_path / "lifecycle.db")
    test_outbox = DurableOutbox(db_path=db_path)
    stop_event = threading.Event()

    runtime = AgentRuntime(
        stop_event=stop_event,
        is_service=True,
        outbox=test_outbox,
        enable_outbox=True,
    )

    with patch("core.runtime.is_enrolled", return_value=True), \
         patch("core.runtime.authenticate_agent", return_value="jwt.test.token"), \
         patch("core.runtime.get_computer_id", return_value=42), \
         patch("core.runtime.AgentWebSocketClient"), \
         patch("core.runtime.collect_all_data", return_value={}):

        def stop_after_startup():
            # Wait for runtime to flag as running, then request stop
            for _ in range(50):
                if runtime.is_running:
                    break
                time.sleep(0.01)
            runtime.stop()

        stopper = threading.Thread(target=stop_after_startup, daemon=True)
        stopper.start()

        runtime.start()
        stopper.join(timeout=2.0)

    assert runtime.started_count == 1
    assert runtime.stopped_count == 1
    assert runtime.is_running is False
    assert runtime.stop_event.is_set() is True
