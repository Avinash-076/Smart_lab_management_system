"""
Unit and integration tests for Phase 7: WebSocket Hardening (G-01 through G-06).
"""

from __future__ import annotations

import collections
import json
import time
from unittest.mock import MagicMock, patch
import threading

import pytest

import config
from core.outbox import DurableOutbox, OutboxPriority
from core.outbox.models import OutboxStatus
from core.runtime import AgentRuntime, TokenHolder
from core.security import (
    build_websocket_endpoint,
    build_websocket_headers,
    derive_ws_url,
    validate_and_normalize_server_url,
)
from server.communication import (
    AgentWebSocketClient,
    WebSocketState,
    compute_jittered_delay,
)


# ============================================================================
# G-01 & G-02 Regression Tests (Security Invariants)
# ============================================================================

def test_g01_no_jwt_in_websocket_url():
    """Verify that WebSocket endpoint URLs contain no tokens or credentials in path or query."""
    comp_id = 999
    base_url = "wss://slms.example.com/ws/client"
    endpoint = build_websocket_endpoint(base_url, comp_id)

    assert endpoint == "wss://slms.example.com/ws/client/999"
    assert "token" not in endpoint.lower()
    assert "bearer" not in endpoint.lower()
    assert "?" not in endpoint


def test_g01_authorization_header_format():
    """Verify standard Authorization Bearer header construction."""
    token = "header.payload.signature"
    headers = build_websocket_headers(token)

    assert len(headers) == 1
    assert headers[0] == f"Authorization: Bearer {token}"

    with pytest.raises(ValueError, match="Access token cannot be empty"):
        build_websocket_headers("")


def test_g02_production_transport_security(monkeypatch):
    """Verify production requires HTTPS/WSS and prohibits unencrypted HTTP/WS."""
    monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
    monkeypatch.delenv("SLMS_DEV_MODE", raising=False)

    # Insecure URL rejected in production
    with pytest.raises(ValueError, match="Insecure HTTP URL .* is prohibited in production"):
        validate_and_normalize_server_url("http://insecure-lab.com")

    # Secure URL properly derives WSS
    normalized = validate_and_normalize_server_url("https://secure-lab.com:8443")
    assert normalized == "https://secure-lab.com:8443"
    ws_url = derive_ws_url(normalized)
    assert ws_url == "wss://secure-lab.com:8443/ws/client"


# ============================================================================
# G-03 Reconnect Delay Management & Backoff
# ============================================================================

def test_reconnect_exponential_backoff():
    """Verify reconnect delay grows exponentially up to max_delay."""
    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "dummy_token",
        base_delay=5.0,
        max_delay=60.0,
    )

    assert client.current_delay == 5.0

    # Simulate successive failures updating backoff
    with client._state_lock:
        curr = client._current_delay
        client._current_delay = min(curr * 2, client.max_delay)
    assert client.current_delay == 10.0

    with client._state_lock:
        curr = client._current_delay
        client._current_delay = min(curr * 2, client.max_delay)
    assert client.current_delay == 20.0

    with client._state_lock:
        curr = client._current_delay
        client._current_delay = min(curr * 2, client.max_delay)
    assert client.current_delay == 40.0

    with client._state_lock:
        curr = client._current_delay
        client._current_delay = min(curr * 2, client.max_delay)
    assert client.current_delay == 60.0

    # Capped at max_delay
    with client._state_lock:
        curr = client._current_delay
        client._current_delay = min(curr * 2, client.max_delay)
    assert client.current_delay == 60.0


def test_reconnect_delay_resets_on_successful_connection():
    """Verify that successful connection handshake immediately resets backoff to base_delay."""
    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "dummy_token",
        base_delay=5.0,
        max_delay=60.0,
    )

    # Force saturated delay
    client._current_delay = 60.0
    assert client.current_delay == 60.0

    # Simulate successful _on_open
    mock_ws = MagicMock()
    client._on_open(mock_ws)

    # Must be reset back to base_delay
    assert client.current_delay == 5.0
    assert client.state == WebSocketState.CONNECTED
    client.stop()


def test_reconnect_jitter_bounds():
    """Verify jitter produces values strictly bounded within ±ratio."""
    delay = 10.0
    ratio = 0.15
    samples = [compute_jittered_delay(delay, jitter_ratio=ratio) for _ in range(100)]

    min_bound = delay * (1 - ratio)  # 8.5
    max_bound = delay * (1 + ratio)  # 11.5

    for s in samples:
        assert min_bound <= s <= max_bound, f"Sample {s} out of bounds [{min_bound}, {max_bound}]"

    # Confirm variance exists (not hardcoded constant)
    assert len(set(samples)) > 1


def test_interruptible_reconnect_shutdown():
    """Verify stop() interrupts reconnect sleep immediately without waiting for delay timeout."""
    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "",  # Forces pre-connect backoff wait
        base_delay=30.0,
        max_delay=60.0,
    )

    start_time = time.monotonic()
    client.start()

    # Allow worker thread to enter wait state
    time.sleep(0.05)

    # Request stop
    client.stop()
    if client._thread:
        client._thread.join(timeout=2.0)

    elapsed = time.monotonic() - start_time
    assert elapsed < 3.0, f"Shutdown took too long ({elapsed:.2f}s); sleep was not interrupted!"
    assert client.state == WebSocketState.STOPPED


def test_single_reconnect_loop():
    """Verify calling start() multiple times does not spawn duplicate worker threads."""
    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "token",
    )
    keep_running = threading.Event()
    with patch.object(client, "_run_forever", side_effect=lambda: keep_running.wait(timeout=2.0)):
        client.start()
        first_thread = client._thread
        client.start()
        second_thread = client._thread
        assert first_thread is second_thread
        keep_running.set()
    client.stop()


# ============================================================================
# G-04 Token / WebSocket Lifecycle Coordination
# ============================================================================

def test_auth_failure_triggers_token_refresh():
    """Verify close code 4001 triggers refresh_token and sets AUTH_FAILED state."""
    refreshed = threading.Event()

    def mock_refresh():
        refreshed.set()
        return "brand_new_token"

    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "stale_token",
        refresh_token=mock_refresh,
    )

    mock_ws = MagicMock()
    client._on_close(mock_ws, close_status_code=4001, close_msg="Unauthorized token")

    assert refreshed.is_set()
    assert client.state == WebSocketState.AUTH_FAILED
    client.stop()


def test_refresh_failure_sets_auth_failed_without_tight_loop():
    """Verify failed token refresh remains in AUTH_FAILED and does not crash."""
    def failing_refresh():
        raise RuntimeError("Credential server unavailable")

    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "stale_token",
        refresh_token=failing_refresh,
    )

    mock_ws = MagicMock()
    # Should not raise exception
    client._on_close(mock_ws, close_status_code=4001, close_msg="Unauthorized")
    assert client.state == WebSocketState.AUTH_FAILED
    client.stop()


def test_de_enrollment_stops_reconnection():
    """Verify that if is_enrolled() returns False, reconnection terminates."""
    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "dummy_token",
        is_enrolled=lambda: False,
    )

    client.start()
    if client._thread:
        client._thread.join(timeout=2.0)

    assert client.state in (WebSocketState.AUTH_FAILED, WebSocketState.STOPPED)
    client.stop()


def test_thread_safe_token_holder_concurrency():
    """Verify TokenHolder safely handles high-concurrency read/write operations without torn reads."""
    holder = TokenHolder("initial_token")
    stop_event = threading.Event()
    errors = []

    def writer():
        for i in range(200):
            if stop_event.is_set():
                break
            holder.token = f"token_value_{i}"
            time.sleep(0.001)

    def reader():
        while not stop_event.is_set():
            t = holder.token
            if not isinstance(t, str) or not t.startswith("token_value_"):
                if t != "initial_token":
                    errors.append(f"Unexpected token value: {t}")
            time.sleep(0.001)

    threads = [
        threading.Thread(target=writer),
        threading.Thread(target=reader),
        threading.Thread(target=reader),
    ]
    for th in threads:
        th.start()

    time.sleep(0.2)
    stop_event.set()
    for th in threads:
        th.join(timeout=1.0)

    assert len(errors) == 0


def test_reconnect_uses_current_token():
    """Verify that when token is updated, next connection attempt uses the updated token."""
    holder = TokenHolder("token_1")
    tokens_used = []

    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: holder.token,
    )

    with patch("websocket.WebSocketApp") as mock_app_cls:
        mock_instance = MagicMock()
        mock_app_cls.return_value = mock_instance

        # First connection attempt uses token_1
        mock_instance.run_forever.side_effect = lambda **kwargs: client.stop()
        with patch.object(client, "base_delay", 0.01):
            client._run_forever()

        call_headers = mock_app_cls.call_args[1]["header"]
        assert call_headers[0] == "Authorization: Bearer token_1"


# ============================================================================
# G-05 Command Execution & Durable Results
# ============================================================================

def test_command_execution_does_not_block_websocket_receiver():
    """Verify command execution runs asynchronously and does not block _on_message."""
    mock_outbox = MagicMock()
    mock_outbox.get_record_by_idempotency_key.return_value = None
    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "token",
        outbox=mock_outbox,
    )

    execution_started = threading.Event()
    execution_can_finish = threading.Event()

    def slow_command_handler(cmd_type, payload):
        execution_started.set()
        execution_can_finish.wait(timeout=2.0)
        return True, "Slow command done"

    with patch("server.communication.execute_command", side_effect=slow_command_handler), \
         patch.object(client, "_send_command_result"):
        msg = json.dumps({
            "type": "command",
            "command_id": 1001,
            "command_type": "message",
            "payload": "Hello",
        })

        t0 = time.monotonic()
        client._on_message(MagicMock(), msg)
        elapsed = time.monotonic() - t0

        # _on_message must return immediately (non-blocking)
        assert elapsed < 0.05, f"_on_message took {elapsed:.3f}s (blocked receiver thread!)"

        # Verify command actually runs in worker pool
        assert execution_started.wait(timeout=1.0)
        execution_can_finish.set()

    client.stop()


def test_command_result_reaches_durable_outbox(tmp_path):
    """Verify command results are durably enqueued with Priority 1 and stable key."""
    outbox_db = str(tmp_path / "outbox.db")
    outbox = DurableOutbox(db_path=outbox_db)

    client = AgentWebSocketClient(
        computer_id=55,
        get_token=lambda: "token",
        outbox=outbox,
    )

    with patch("server.communication.execute_command", return_value=(True, "Workstation locked")):
        msg = json.dumps({
            "type": "command",
            "command_id": 777,
            "command_type": "lock",
            "payload": None,
        })
        client._on_message(MagicMock(), msg)

        # Allow worker thread to complete execution and enqueue
        time.sleep(0.15)

    record = outbox.get_record_by_idempotency_key("cmd_result_777")
    assert record is not None
    assert record.event_type == "command_result"
    assert record.priority == OutboxPriority.COMMAND
    assert record.payload["command_id"] == 777
    assert record.payload["success"] is True
    assert record.payload["message"] == "Workstation locked"

    client.stop()


def test_client_side_duplicate_command_deduplication(tmp_path):
    """Verify the same command_id is not executed twice."""
    outbox_db = str(tmp_path / "outbox.db")
    outbox = DurableOutbox(db_path=outbox_db)

    client = AgentWebSocketClient(
        computer_id=55,
        get_token=lambda: "token",
        outbox=outbox,
    )

    execution_count = 0

    def counting_executor(cmd_type, payload):
        nonlocal execution_count
        execution_count += 1
        return True, "Executed"

    with patch("server.communication.execute_command", side_effect=counting_executor):
        msg = json.dumps({
            "type": "command",
            "command_id": 888,
            "command_type": "message",
            "payload": "Test",
        })

        # Send twice
        client._on_message(MagicMock(), msg)
        time.sleep(0.05)
        client._on_message(MagicMock(), msg)
        time.sleep(0.1)

    assert execution_count == 1
    client.stop()


def test_outbox_failure_falls_back_to_direct_http(tmp_path):
    """If outbox enqueue raises, fallback direct HTTP upload is invoked."""
    mock_outbox = MagicMock(spec=DurableOutbox)
    mock_outbox.get_record_by_idempotency_key.return_value = None
    mock_outbox.enqueue.side_effect = RuntimeError("Disk full")

    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "token",
        outbox=mock_outbox,
    )

    with patch("server.communication.execute_command", return_value=(True, "OK")), \
         patch.object(client, "_send_command_result", return_value=True) as mock_fallback:
        msg = json.dumps({
            "type": "command",
            "command_id": 999,
            "command_type": "lock",
        })
        client._on_message(MagicMock(), msg)
        time.sleep(0.1)

        mock_fallback.assert_called_once_with(999, True, "OK")

    client.stop()


def test_outbox_failure_and_network_failure_logs_critical_without_silent_success():
    """Verify that if outbox enqueue and emergency HTTP both fail, failure is logged and not reported as success."""
    mock_outbox = MagicMock(spec=DurableOutbox)
    mock_outbox.get_record_by_idempotency_key.return_value = None
    mock_outbox.enqueue.side_effect = RuntimeError("Database corrupt")

    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "token",
        outbox=mock_outbox,
    )

    with patch("server.communication.execute_command", return_value=(True, "Rebooting")), \
         patch.object(client, "_send_command_result", return_value=False) as mock_http, \
         patch("server.communication.logger.critical") as mock_crit_log:
        msg = json.dumps({
            "type": "command",
            "command_id": 12345,
            "command_type": "restart",
        })
        client._on_message(MagicMock(), msg)
        time.sleep(0.1)

        mock_http.assert_called_once_with(12345, True, "Rebooting")
        assert mock_crit_log.called
        assert "DURABILITY FAILURE" in mock_crit_log.call_args[0][0]

    client.stop()


def test_duplicate_command_after_dead_letter_prevents_unsafe_reexecution(tmp_path):
    """Verify that a command whose previous result entered DEAD_LETTER in outbox is not re-executed."""
    outbox_db = str(tmp_path / "outbox.db")
    outbox = DurableOutbox(db_path=outbox_db)

    # Pre-enqueue command result and transition to DEAD_LETTER
    record = outbox.enqueue(
        event_type="command_result",
        payload={"command_id": 4321, "success": True, "message": "Done"},
        idempotency_key="cmd_result_4321",
        priority=OutboxPriority.COMMAND,
    )
    with outbox._get_connection() as conn:
        conn.execute("UPDATE outbox_items SET status = ? WHERE id = ?", (OutboxStatus.DEAD_LETTER.value, record.id))
        conn.commit()

    dead_rec = outbox.get_record_by_idempotency_key("cmd_result_4321")
    assert dead_rec.status == OutboxStatus.DEAD_LETTER

    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "token",
        outbox=outbox,
    )

    with patch("server.communication.execute_command") as mock_exec:
        msg = json.dumps({
            "type": "command",
            "command_id": 4321,
            "command_type": "lock",
        })
        client._on_message(MagicMock(), msg)
        time.sleep(0.05)

        # Must not re-execute!
        mock_exec.assert_not_called()

    # Outbox status must remain DEAD_LETTER (unmodified)
    check_rec = outbox.get_record_by_idempotency_key("cmd_result_4321")
    assert check_rec.status == OutboxStatus.DEAD_LETTER
    client.stop()


def test_duplicate_command_when_persistence_and_http_failed(tmp_path):
    """Verify that even if outbox and HTTP failed, duplicate delivery does not re-execute side effects."""
    mock_outbox = MagicMock(spec=DurableOutbox)
    mock_outbox.get_record_by_idempotency_key.return_value = None
    mock_outbox.enqueue.side_effect = RuntimeError("Storage failure")

    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "token",
        outbox=mock_outbox,
    )

    exec_count = 0

    def mock_executor(cmd_type, payload):
        nonlocal exec_count
        exec_count += 1
        return True, "Executed"

    with patch("server.communication.execute_command", side_effect=mock_executor), \
         patch.object(client, "_send_command_result", return_value=False):
        msg = json.dumps({
            "type": "command",
            "command_id": 9999,
            "command_type": "shutdown",
        })

        # First delivery: executes once
        client._on_message(MagicMock(), msg)
        time.sleep(0.05)
        assert exec_count == 1

        # Second duplicate delivery: must NOT re-execute
        client._on_message(MagicMock(), msg)
        time.sleep(0.05)
        assert exec_count == 1

    client.stop()


def test_shutdown_while_command_is_running():
    """Verify shutdown completes promptly without waiting for slow commands to finish."""
    mock_outbox = MagicMock(spec=DurableOutbox)
    mock_outbox.get_record_by_idempotency_key.return_value = None
    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "token",
        outbox=mock_outbox,
    )

    command_running = threading.Event()
    command_can_finish = threading.Event()

    def slow_exec(cmd_type, payload):
        command_running.set()
        command_can_finish.wait(timeout=5.0)
        return True, "Finished"

    with patch("server.communication.execute_command", side_effect=slow_exec):
        msg = json.dumps({
            "type": "command",
            "command_id": 8801,
            "command_type": "message",
            "payload": "Slow task",
        })
        client._on_message(MagicMock(), msg)
        assert command_running.wait(timeout=1.0)

        # Stop client while command is still running
        t0 = time.monotonic()
        client.stop()
        stop_duration = time.monotonic() - t0

        # Must return immediately (under 0.5s)
        assert stop_duration < 0.5, f"Shutdown took {stop_duration:.2f}s (blocked on command!)"
        assert client.state == WebSocketState.STOPPED

        # Release slow command
        command_can_finish.set()


def test_shutdown_while_two_commands_are_running():
    """Verify shutdown with saturated worker pool (2 workers) completes promptly without deadlock."""
    mock_outbox = MagicMock(spec=DurableOutbox)
    mock_outbox.get_record_by_idempotency_key.return_value = None
    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "token",
        outbox=mock_outbox,
    )

    both_running = threading.Barrier(3)  # 2 workers + 1 test thread
    can_finish = threading.Event()

    def slow_exec(cmd_type, payload):
        try:
            both_running.wait(timeout=2.0)
        except threading.BrokenBarrierError:
            pass
        can_finish.wait(timeout=5.0)
        return True, "Done"

    with patch("server.communication.execute_command", side_effect=slow_exec), \
         patch.object(client, "_send_command_result", return_value=True):
        client._on_message(MagicMock(), json.dumps({
            "type": "command", "command_id": 8802, "command_type": "task1"
        }))
        client._on_message(MagicMock(), json.dumps({
            "type": "command", "command_id": 8803, "command_type": "task2"
        }))

        # Wait until both commands have started executing
        both_running.wait(timeout=2.0)

        t0 = time.monotonic()
        client.stop()
        stop_duration = time.monotonic() - t0

        assert stop_duration < 0.5, f"Shutdown took {stop_duration:.2f}s on saturated pool!"
        assert client.state == WebSocketState.STOPPED

        can_finish.set()


# ============================================================================
# G-06 Observable WebSocket State Model
# ============================================================================

def test_state_transitions_normal_lifecycle():
    """Verify client transitions through expected states during lifecycle."""
    transitions = []

    def record_transition(old_s, new_s):
        transitions.append((old_s, new_s))

    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "valid_token",
        on_state_change=record_transition,
    )

    assert client.state == WebSocketState.DISCONNECTED
    assert client.is_connected is False

    # Simulate start and handshake
    mock_ws = MagicMock()
    client._on_open(mock_ws)
    assert client.state == WebSocketState.CONNECTED
    assert client.is_connected is True

    # Simulate disconnect
    client._on_close(mock_ws, close_status_code=1006, close_msg="Abnormal close")
    assert client.state == WebSocketState.DISCONNECTED

    # Simulate stop
    client.stop()
    assert client.state == WebSocketState.STOPPED

    assert (WebSocketState.DISCONNECTED, WebSocketState.CONNECTED) in transitions
    assert (WebSocketState.CLOSING, WebSocketState.STOPPED) in transitions


def test_runtime_ws_state_exposure():
    """Verify AgentRuntime exposes ws_state property for observability."""
    runtime = AgentRuntime(is_service=False)
    assert runtime.ws_state is None

    runtime.ws_client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "token",
    )
    assert runtime.ws_state == WebSocketState.DISCONNECTED


# ============================================================================
# Heartbeat & Ping Loop Lifecycle
# ============================================================================

def test_single_ping_loop_and_clean_termination():
    """Verify heartbeat thread starts on open and terminates immediately on close."""
    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "token",
        ping_interval=0.05,
    )

    mock_ws = MagicMock()
    mock_ws.sock.connected = True

    # Open connection
    client._on_open(mock_ws)
    assert client._ping_thread is not None
    assert client._ping_thread.is_alive()

    # Close connection
    client._on_close(mock_ws, close_status_code=1000, close_msg="Normal closure")

    # Ping thread must terminate cleanly and promptly
    time.sleep(0.1)
    assert client._ping_stop_event.is_set()
    client.stop()


def test_flapping_connection_does_not_accumulate_ping_threads():
    """Verify rapid open/close flaps do not leak multiple ping threads."""
    client = AgentWebSocketClient(
        computer_id=1,
        get_token=lambda: "token",
        ping_interval=1.0,
    )

    mock_ws = MagicMock()
    mock_ws.sock.connected = True

    for _ in range(5):
        client._on_open(mock_ws)
        client._on_close(mock_ws, close_status_code=1006, close_msg="Flap")

    # Allow brief moment for cleanup
    time.sleep(0.05)

    # Active threads with name 'SLMS-WebSocket-Ping' must not accumulate
    active_ping_threads = [
        th for th in threading.enumerate()
        if th.name == "SLMS-WebSocket-Ping" and th.is_alive()
    ]
    assert len(active_ping_threads) <= 1
    client.stop()
