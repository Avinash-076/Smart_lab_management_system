"""
Comprehensive Automated Test Suite for Phase 3: Durable Local State / Outbox Subsystem.

Covers all 29 verification requirements:
1. Enqueue item
2. Retrieve pending item
3. Successful delivery
4. Retryable failure
5. Exponential backoff
6. Non-retryable failure
7. Maximum retry / dead-letter behavior
8. Idempotency key generation
9. Duplicate enqueue prevention
10. Response-loss retry scenario
11. Persistence after process restart
12. Persistence after reopening SQLite database
13. Queue capacity limit
14. Payload / storage limit
15. Concurrent producers
16. Delivery worker concurrency
17. Network unavailable
18. Network restored
19. Authentication refresh behavior
20. Telemetry durability
21. Issue durability
22. Usage-session durability
23. Command-result durability
24. Crash-safe transaction behavior
25. No access_token or client_secret stored in outbox
26. Service shutdown with pending records
27. Restart with pending records
28. Phase 1 regression verification
29. Phase 2 regression verification
"""

import json
import os
import sqlite3
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from core.outbox import (
    DEFAULT_MAX_ATTEMPTS_CRITICAL,
    DEFAULT_MAX_ATTEMPTS_TELEMETRY,
    DurableOutbox,
    ErrorClassification,
    OutboxDeliveryWorker,
    OutboxPriority,
    OutboxRecord,
    OutboxStatus,
    QueueFullError,
    calculate_backoff_delay,
    classify_exception,
    classify_http_status,
)


@pytest.fixture
def temp_outbox(tmp_path):
    """Provide a fresh DurableOutbox backed by an isolated temporary SQLite database."""
    db_file = str(tmp_path / "test_outbox.db")
    wake_event = threading.Event()
    outbox = DurableOutbox(db_path=db_file, wake_event=wake_event)
    yield outbox
    wake_event.set()


# ============================================================================
# 1-7: Basic Outbox Operations & Policies
# ============================================================================

class TestOutboxBasicOperations:

    def test_00_sqlite_wal_journal_mode(self, temp_outbox):
        """Verify outbox database connection is configured with WAL journal mode."""
        with temp_outbox._get_connection() as conn:
            cur = conn.execute("PRAGMA journal_mode;")
            mode = cur.fetchone()[0]
            assert str(mode).lower() == "wal"

    def test_01_enqueue_item(self, temp_outbox):
        """1. Verify enqueuing an item persists it in SQLite with PENDING status."""
        payload = {"cpu_usage": 55.0, "ram_usage": 40.0}
        rec = temp_outbox.enqueue(
            event_type="metrics",
            payload=payload,
            idempotency_key="key_test_01",
            priority=OutboxPriority.TELEMETRY,
        )

        assert rec.id is not None
        assert rec.event_type == "metrics"
        assert rec.status == OutboxStatus.PENDING
        assert rec.payload["cpu_usage"] == 55.0
        assert rec.attempt_count == 0
        assert temp_outbox.wake_event.is_set()

    def test_02_retrieve_pending_item(self, temp_outbox):
        """2. Verify retrieve pending batch claims items and transitions them to PROCESSING."""
        rec = temp_outbox.enqueue(
            event_type="metrics",
            payload={"test": 123},
            idempotency_key="key_test_02",
        )

        batch = temp_outbox.get_pending_batch(limit=10)
        assert len(batch) == 1
        assert batch[0].id == rec.id
        assert batch[0].status == OutboxStatus.PROCESSING

        # A second immediate call should return empty since item is now PROCESSING
        batch2 = temp_outbox.get_pending_batch(limit=10)
        assert len(batch2) == 0

    def test_03_successful_delivery(self, temp_outbox):
        """3. Verify successful delivery removes the record from SQLite."""
        temp_outbox.enqueue(
            event_type="metrics",
            payload={"test": 123},
            idempotency_key="key_test_03",
        )
        batch = temp_outbox.get_pending_batch(limit=1)
        assert len(batch) == 1

        temp_outbox.mark_delivered(batch[0].id)

        # Database must have 0 items
        stats = temp_outbox.get_stats()
        assert stats["total_count"] == 0

    def test_04_retryable_failure(self, temp_outbox):
        """4. Verify retryable failure increments attempt count and resets status to PENDING."""
        rec = temp_outbox.enqueue(
            event_type="metrics",
            payload={"test": 123},
            idempotency_key="key_test_04",
        )
        batch = temp_outbox.get_pending_batch(limit=1)
        item = batch[0]

        future_time = time.time() + 10.0
        temp_outbox.mark_retry(item.id, "503 Service Unavailable", future_time)

        # Item should not be retrievable now because next_attempt_at is in the future
        assert len(temp_outbox.get_pending_batch(limit=1, now=time.time())) == 0

        # But it should be retrievable at future_time + 1s
        future_batch = temp_outbox.get_pending_batch(limit=1, now=future_time + 1.0)
        assert len(future_batch) == 1
        assert future_batch[0].attempt_count == 1
        assert future_batch[0].last_error == "503 Service Unavailable"

    def test_05_exponential_backoff(self):
        """5. Verify calculate_backoff_delay computes bounded exponential backoff with jitter."""
        d1 = calculate_backoff_delay(1)
        d2 = calculate_backoff_delay(2)
        d3 = calculate_backoff_delay(3)
        d4 = calculate_backoff_delay(4)

        # Base expectation: ~2s, ~4s, ~8s, ~16s within ±20% jitter
        assert 1.5 <= d1 <= 2.5
        assert 3.0 <= d2 <= 5.0
        assert 6.0 <= d3 <= 10.0
        assert 12.0 <= d4 <= 20.0

        # Verify max cap
        d_large = calculate_backoff_delay(20, max_delay=60.0)
        assert d_large <= 75.0  # bounded by max_delay + jitter

    def test_06_non_retryable_failure(self, temp_outbox):
        """6. Verify non-retryable 4xx client errors move record directly to DEAD_LETTER."""
        rec = temp_outbox.enqueue(
            event_type="metrics",
            payload={"test": 123},
            idempotency_key="key_test_06",
        )
        batch = temp_outbox.get_pending_batch(limit=1)
        item = batch[0]

        temp_outbox.mark_dead_letter(item.id, "HTTP 400: Malformed JSON payload")

        stats = temp_outbox.get_stats()
        assert stats["status_counts"].get(OutboxStatus.DEAD_LETTER.value) == 1
        assert stats["status_counts"].get(OutboxStatus.PENDING.value, 0) == 0

    def test_07_maximum_retry_dead_letter_behavior(self, temp_outbox):
        """7. Verify reaching max_attempts automatically moves record to DEAD_LETTER."""
        rec = temp_outbox.enqueue(
            event_type="metrics",
            payload={"test": 123},
            idempotency_key="key_test_07",
            max_attempts=3,
        )

        # Attempt 1
        b1 = temp_outbox.get_pending_batch(limit=1)
        temp_outbox.mark_retry(b1[0].id, "Error 1", time.time())

        # Attempt 2
        b2 = temp_outbox.get_pending_batch(limit=1)
        temp_outbox.mark_retry(b2[0].id, "Error 2", time.time())

        # Attempt 3 -> exceeds max_attempts=3
        b3 = temp_outbox.get_pending_batch(limit=1)
        temp_outbox.mark_retry(b3[0].id, "Error 3", time.time())

        stats = temp_outbox.get_stats()
        assert stats["status_counts"].get(OutboxStatus.DEAD_LETTER.value) == 1
        assert stats["status_counts"].get(OutboxStatus.PENDING.value, 0) == 0

    def test_classify_transport_security_exceptions(self):
        """Verify InsecureHttpProhibitedError is RETRYABLE_FAILURE and InvalidServerUrlError is PERMANENT_FAILURE."""
        from core.security import InsecureHttpProhibitedError, InvalidServerUrlError

        insecure_err = InsecureHttpProhibitedError("Insecure HTTP URL is prohibited in production.")
        cls_insecure, msg_insecure = classify_exception(insecure_err)
        assert cls_insecure == ErrorClassification.RETRYABLE_FAILURE
        assert "Transport security policy" in msg_insecure

        invalid_url_err = InvalidServerUrlError("Server URL cannot be empty.")
        cls_invalid, msg_invalid = classify_exception(invalid_url_err)
        assert cls_invalid == ErrorClassification.PERMANENT_FAILURE
        assert "Invalid server URL configuration" in msg_invalid

        net_err = requests.ConnectionError("Connection timed out")
        cls_net, msg_net = classify_exception(net_err)
        assert cls_net == ErrorClassification.RETRYABLE_FAILURE


# ============================================================================
# 8-12: Idempotency & Persistence Across Restarts
# ============================================================================

class TestOutboxIdempotencyAndDurability:

    def test_08_idempotency_key_generation(self, temp_outbox):
        """8. Verify automatic generation of deterministic/unique idempotency keys."""
        rec = temp_outbox.enqueue(
            event_type="issue",
            payload={"title": "High Ram"},
        )
        assert rec.idempotency_key is not None
        assert rec.idempotency_key.startswith("issue_")

    def test_09_duplicate_enqueue_prevention(self, temp_outbox):
        """9. Verify enqueuing duplicate items with identical key returns existing record."""
        key = "idemp_test_09"
        rec1 = temp_outbox.enqueue(
            event_type="command_result",
            payload={"command_id": 101, "success": True},
            idempotency_key=key,
        )
        rec2 = temp_outbox.enqueue(
            event_type="command_result",
            payload={"command_id": 101, "success": True},
            idempotency_key=key,
        )

        assert rec1.id == rec2.id
        stats = temp_outbox.get_stats()
        assert stats["total_count"] == 1

    def test_10_response_loss_retry_scenario(self, temp_outbox):
        """
        10. Verify response-loss retry scenario:
        When server returns HTTP 409 Conflict (already submitted), worker marks it delivered.
        """
        rec = temp_outbox.enqueue(
            event_type="command_result",
            payload={"command_id": 202, "success": True, "message": "done"},
            idempotency_key="cmd_result_202",
        )

        # Simulate worker processing item when response is 409 Conflict
        worker = OutboxDeliveryWorker(
            outbox=temp_outbox,
            get_token=lambda: "fake.token",
        )

        # Mock send_command_result to raise HTTP 409
        mock_resp = MagicMock()
        mock_resp.status_code = 409
        mock_resp.text = "Command result already submitted"
        http_error = requests.HTTPError(response=mock_resp)

        with patch("core.outbox.worker.send_command_result", side_effect=http_error):
            worker.drain_once()

        # Should be marked delivered and deleted!
        stats = temp_outbox.get_stats()
        assert stats["total_count"] == 0

    def test_11_persistence_after_process_restart(self, tmp_path):
        """11. Verify outbox state survives closing and re-opening the outbox instance."""
        db_file = str(tmp_path / "restart_test.db")
        outbox1 = DurableOutbox(db_path=db_file)
        outbox1.enqueue(
            event_type="usage",
            payload={"sessions": [{"app": "excel.exe"}]},
            idempotency_key="usage_restart_key",
        )
        stats1 = outbox1.get_stats()
        assert stats1["total_count"] == 1

        # Simulate process termination: destroy instance and open new one
        del outbox1

        outbox2 = DurableOutbox(db_path=db_file)
        stats2 = outbox2.get_stats()
        assert stats2["total_count"] == 1

        batch = outbox2.get_pending_batch(limit=5)
        assert len(batch) == 1
        assert batch[0].idempotency_key == "usage_restart_key"

    def test_12_persistence_after_reopening_sqlite_database(self, tmp_path):
        """12. Verify SQLite database directly contains records using raw sqlite3 query."""
        db_file = str(tmp_path / "raw_sqlite_test.db")
        outbox = DurableOutbox(db_path=db_file)
        outbox.enqueue(
            event_type="metrics",
            payload={"cpu": 99.0},
            idempotency_key="raw_key_12",
        )

        # Query directly with independent sqlite3 connection
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM outbox_items WHERE idempotency_key = ?;", ("raw_key_12",))
        row = cur.fetchone()
        assert row is not None
        assert row["event_type"] == "metrics"
        assert row["status"] == OutboxStatus.PENDING.value
        conn.close()


# ============================================================================
# 13-16: Backpressure, Limits & Concurrency
# ============================================================================

class TestOutboxBackpressureAndLimits:

    def test_13_queue_capacity_limit(self, tmp_path):
        """13. Verify bounded queue prunes oldest telemetry when capacity limit is reached."""
        db_file = str(tmp_path / "capacity_test.db")
        outbox = DurableOutbox(db_path=db_file, max_records=4)

        # Fill queue with 4 telemetry records
        for i in range(4):
            outbox.enqueue(
                event_type="metrics",
                payload={"index": i},
                idempotency_key=f"metric_{i}",
                priority=OutboxPriority.TELEMETRY,
            )

        assert outbox.get_stats()["total_count"] == 4

        # Enqueue critical command result (priority 1)
        outbox.enqueue(
            event_type="command_result",
            payload={"command_id": 99},
            idempotency_key="cmd_crit_99",
            priority=OutboxPriority.COMMAND,
        )

        # Total count must remain bounded at 4
        stats = outbox.get_stats()
        assert stats["total_count"] == 4

        # Oldest telemetry (metric_0) must have been pruned, command result retained
        conn = sqlite3.connect(db_file)
        keys = [r[0] for r in conn.execute("SELECT idempotency_key FROM outbox_items;").fetchall()]
        conn.close()

        assert "cmd_crit_99" in keys
        assert "metric_0" not in keys

    def test_14_payload_storage_limit(self, tmp_path):
        """14. Verify max_bytes storage limit prunes old telemetry records."""
        db_file = str(tmp_path / "bytes_test.db")
        # 500 bytes max storage
        outbox = DurableOutbox(db_path=db_file, max_bytes=500)

        # Enqueue large telemetry payloads
        outbox.enqueue(
            event_type="processes",
            payload={"data": "A" * 200},
            idempotency_key="proc_1",
            priority=OutboxPriority.TELEMETRY,
        )
        outbox.enqueue(
            event_type="processes",
            payload={"data": "B" * 200},
            idempotency_key="proc_2",
            priority=OutboxPriority.TELEMETRY,
        )

        # Enqueue a high priority issue
        outbox.enqueue(
            event_type="issue",
            payload={"title": "High Temp"},
            idempotency_key="issue_crit",
            priority=OutboxPriority.ISSUE,
        )

        stats = outbox.get_stats()
        assert stats["total_bytes"] <= 500

    def test_15_concurrent_producers(self, tmp_path):
        """15. Verify concurrent producers enqueuing simultaneously have zero SQLite lock errors."""
        db_file = str(tmp_path / "concurrent_test.db")
        outbox = DurableOutbox(db_path=db_file, max_records=2000)

        num_threads = 8
        items_per_thread = 25
        errors = []

        def producer_worker(thread_id):
            for i in range(items_per_thread):
                try:
                    outbox.enqueue(
                        event_type="metrics",
                        payload={"thread": thread_id, "seq": i},
                        idempotency_key=f"t_{thread_id}_item_{i}",
                    )
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=producer_worker, args=(t,))
            for t in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        stats = outbox.get_stats()
        assert stats["total_count"] == num_threads * items_per_thread

    def test_16_delivery_worker_concurrency(self, tmp_path):
        """16. Verify delivery worker and producers can execute concurrently without deadlocks."""
        db_file = str(tmp_path / "worker_concurrency_test.db")
        outbox = DurableOutbox(db_path=db_file)
        stop_event = threading.Event()

        worker = OutboxDeliveryWorker(
            outbox=outbox,
            get_token=lambda: "test.token",
            poll_interval=0.05,
            stop_event=stop_event,
        )

        with patch("core.outbox.worker.send_metrics") as mock_send:
            worker.start()

            # Enqueue from another thread while worker runs
            for i in range(20):
                outbox.enqueue(
                    event_type="metrics",
                    payload={"index": i},
                    idempotency_key=f"conc_metric_{i}",
                )

            # Wait briefly for worker to drain
            time.sleep(0.3)
            worker.stop()

        stats = outbox.get_stats()
        assert stats["total_count"] == 0
        assert mock_send.call_count == 20


# ============================================================================
# 17-19: Network & Authentication Resilience
# ============================================================================

class TestOutboxNetworkAndAuth:

    def test_17_network_unavailable(self, temp_outbox):
        """17. Verify when network is unavailable, item is not lost and scheduled for retry."""
        temp_outbox.enqueue(
            event_type="metrics",
            payload={"metric": 1},
            idempotency_key="net_down_key",
        )

        worker = OutboxDeliveryWorker(
            outbox=temp_outbox,
            get_token=lambda: "test.token",
        )

        with patch("core.outbox.worker.send_metrics", side_effect=requests.ConnectionError("Connection refused")):
            worker.drain_once()

        stats = temp_outbox.get_stats()
        assert stats["total_count"] == 1

        # Check item has error recorded and attempt_count=1
        batch = temp_outbox.get_pending_batch(limit=1, now=time.time() + 1000.0)
        assert len(batch) == 1
        assert batch[0].attempt_count == 1
        assert "Connection refused" in (batch[0].last_error or "")

    def test_18_network_restored(self, temp_outbox):
        """18. Verify once network is restored, pending retry items are successfully delivered."""
        temp_outbox.enqueue(
            event_type="metrics",
            payload={"metric": 1},
            idempotency_key="net_restored_key",
        )

        worker = OutboxDeliveryWorker(
            outbox=temp_outbox,
            get_token=lambda: "test.token",
        )

        # 1. Outage
        with patch("core.outbox.worker.send_metrics", side_effect=requests.Timeout("Timeout")):
            worker.drain_once()
        assert temp_outbox.get_stats()["total_count"] == 1

        # 2. Restoration (simulate time passing past backoff delay)
        with patch("core.outbox.worker.send_metrics") as mock_ok, \
             patch("time.time", return_value=time.time() + 100.0):
            worker.drain_once()

        # Database is now empty
        assert temp_outbox.get_stats()["total_count"] == 0
        assert mock_ok.call_count == 1

    def test_19_authentication_refresh_behavior(self, temp_outbox):
        """19. Verify HTTP 401 triggers token refresh and immediate successful retry."""
        temp_outbox.enqueue(
            event_type="issue",
            payload={"title": "High CPU", "description": "99%", "severity": "high"},
            idempotency_key="auth_refresh_key",
        )

        token_state = {"current": "expired.jwt.token", "refreshed": False}

        def get_token():
            return token_state["current"]

        def refresh_token():
            token_state["current"] = "fresh.jwt.token"
            token_state["refreshed"] = True
            return "fresh.jwt.token"

        worker = OutboxDeliveryWorker(
            outbox=temp_outbox,
            get_token=get_token,
            refresh_token=refresh_token,
        )

        def mock_send_issue(payload, token):
            if token == "expired.jwt.token":
                mock_resp = MagicMock()
                mock_resp.status_code = 401
                mock_resp.text = "Signature has expired"
                raise requests.HTTPError(response=mock_resp)
            # Fresh token succeeds
            return {"id": 1, "title": payload["title"]}

        with patch("core.outbox.worker.send_issue", side_effect=mock_send_issue):
            worker.drain_once()

        assert token_state["refreshed"] is True
        assert temp_outbox.get_stats()["total_count"] == 0


# ============================================================================
# 20-23: Durability Across Event Types
# ============================================================================

class TestOutboxDeliveryPathsDurability:

    def test_20_telemetry_durability(self, temp_outbox):
        """20. Verify metrics, software, and processes can be queued and delivered."""
        temp_outbox.enqueue("metrics", {"cpu_usage": 10}, "key_m")
        temp_outbox.enqueue("software", [{"name": "Python"}], "key_s")
        temp_outbox.enqueue("processes", [{"pid": 1, "name": "system"}], "key_p")

        assert temp_outbox.get_stats()["total_count"] == 3

        worker = OutboxDeliveryWorker(outbox=temp_outbox, get_token=lambda: "tok")
        with patch("core.outbox.worker.send_metrics"), \
             patch("core.outbox.worker.send_software_inventory"), \
             patch("core.outbox.worker.send_process_inventory"):
            worker.drain_once()

        assert temp_outbox.get_stats()["total_count"] == 0

    def test_21_issue_durability(self, temp_outbox):
        """21. Verify issue durability through outbox."""
        temp_outbox.enqueue(
            "issue",
            {"title": "Disk Full", "description": "100%", "severity": "critical"},
            "key_issue",
            priority=OutboxPriority.ISSUE,
        )

        worker = OutboxDeliveryWorker(outbox=temp_outbox, get_token=lambda: "tok")
        with patch("core.outbox.worker.send_issue") as mock_issue:
            worker.drain_once()

        assert mock_issue.call_count == 1
        assert temp_outbox.get_stats()["total_count"] == 0

    def test_22_usage_session_durability(self, temp_outbox):
        """22. Verify usage session durability through outbox."""
        temp_outbox.enqueue(
            "usage",
            {"sessions": [{"application_name": "notepad.exe", "duration_seconds": 120}]},
            "key_usage",
            priority=OutboxPriority.USAGE,
        )

        worker = OutboxDeliveryWorker(outbox=temp_outbox, get_token=lambda: "tok")
        with patch("core.outbox.worker.send_usage_sessions") as mock_usage:
            worker.drain_once()

        assert mock_usage.call_count == 1
        assert temp_outbox.get_stats()["total_count"] == 0

    def test_23_command_result_durability(self, temp_outbox):
        """23. Verify command result durability through outbox."""
        temp_outbox.enqueue(
            "command_result",
            {"command_id": 55, "success": True, "message": "Reboot complete"},
            "key_cmd_55",
            priority=OutboxPriority.COMMAND,
        )

        worker = OutboxDeliveryWorker(outbox=temp_outbox, get_token=lambda: "tok")
        with patch("core.outbox.worker.send_command_result") as mock_cmd:
            worker.drain_once()

        assert mock_cmd.call_count == 1
        assert temp_outbox.get_stats()["total_count"] == 0


# ============================================================================
# 24-27: Safety, Crash Recovery & Service Lifecycle
# ============================================================================

class TestOutboxSafetyAndLifecycle:

    def test_24_crash_safe_transaction_behavior(self, tmp_path):
        """24. Verify recover_stale_processing resets items stuck in PROCESSING after a crash."""
        db_file = str(tmp_path / "crash_test.db")
        outbox = DurableOutbox(db_path=db_file)

        outbox.enqueue("metrics", {"cpu": 50}, "key_crash")
        # Claim item -> status becomes PROCESSING
        claimed = outbox.get_pending_batch(limit=1)
        assert len(claimed) == 1
        assert claimed[0].status == OutboxStatus.PROCESSING

        # Simulate agent crash: time passes without mark_delivered
        # recover_stale_processing should reset it to PENDING
        recovered = outbox.recover_stale_processing(stale_threshold_seconds=0.0)
        assert recovered == 1

        # Now it is available again in pending batch
        reclaimed = outbox.get_pending_batch(limit=1)
        assert len(reclaimed) == 1
        assert reclaimed[0].id == claimed[0].id

    def test_25_no_credentials_stored_in_outbox(self, temp_outbox):
        """25. Verify SQLite database contains no tokens, client_secret, or passwords."""
        temp_outbox.enqueue(
            "metrics",
            {"cpu_usage": 45.0, "ram_usage": 50.0},
            idempotency_key="key_sec_check",
        )

        # Inspect database file content and schema
        conn = sqlite3.connect(temp_outbox.db_path)
        cur = conn.execute("SELECT * FROM outbox_items;")
        rows = cur.fetchall()
        conn.close()

        for row in rows:
            row_str = str(row)
            assert "Bearer" not in row_str
            assert "eyJ" not in row_str  # Common JWT prefix
            assert "client_secret" not in row_str
            assert "secret_hash" not in row_str
            assert "password" not in row_str

    def test_26_service_shutdown_with_pending_records(self, tmp_path):
        """26. Verify service shutdown preserves pending records in SQLite."""
        db_file = str(tmp_path / "shutdown_test.db")
        outbox = DurableOutbox(db_path=db_file)

        outbox.enqueue("issue", {"title": "Service Stopping"}, "key_shut")

        # Simulate shutdown of worker
        worker = OutboxDeliveryWorker(outbox=outbox, get_token=lambda: "token")
        worker.start()
        worker.stop()

        # Database must still have the pending record
        stats = outbox.get_stats()
        assert stats["total_count"] == 1

    def test_27_restart_with_pending_records(self, tmp_path):
        """27. Verify restart drains records left over from previous service runs."""
        db_file = str(tmp_path / "restart_drain_test.db")
        outbox1 = DurableOutbox(db_path=db_file)
        outbox1.enqueue("command_result", {"command_id": 999, "success": True}, "cmd_restart_999")
        del outbox1

        # Start up fresh outbox and worker
        outbox2 = DurableOutbox(db_path=db_file)
        worker = OutboxDeliveryWorker(outbox=outbox2, get_token=lambda: "token")

        with patch("core.outbox.worker.send_command_result") as mock_cmd:
            worker.drain_once()

        assert mock_cmd.call_count == 1
        assert outbox2.get_stats()["total_count"] == 0


# ============================================================================
# 28-29: Regressions (Phase 1 & Phase 2 Integration)
# ============================================================================

class TestOutboxRegressions:

    def test_28_phase_1_regression(self):
        """28. Verify Phase 1 TLS and authentication rules remain active and unaffected."""
        from core.security import is_insecure_http_allowed, validate_and_normalize_server_url
        with patch.dict(os.environ, {"SLMS_ALLOW_INSECURE_HTTP": "0", "SLMS_DEV_MODE": "0"}):
            assert is_insecure_http_allowed() is False
            with pytest.raises(ValueError):
                validate_and_normalize_server_url("http://insecure.slms.local")

    def test_29_phase_2_regression(self, tmp_path):
        """29. Verify AgentRuntime integrates cleanly with outbox and service lifecycle."""
        from core.runtime import AgentRuntime

        stop_event = threading.Event()
        test_outbox = DurableOutbox(db_path=str(tmp_path / "runtime_reg.db"))

        runtime = AgentRuntime(
            stop_event=stop_event,
            is_service=True,
            outbox=test_outbox,
            enable_outbox=True,
            enable_single_instance=False,
        )

        with patch("core.runtime.is_enrolled", return_value=True), \
             patch("core.runtime.authenticate_agent", return_value="fake.token"), \
             patch("core.runtime.get_computer_id", return_value=123), \
             patch("core.runtime.AgentWebSocketClient"), \
             patch("core.runtime.collect_all_data", return_value={"hardware": {"cpu_usage": 10}}):

            def stop_later():
                time.sleep(0.05)
                runtime.stop()

            threading.Thread(target=stop_later, daemon=True).start()
            runtime.start()

            assert runtime.started_count == 1
            assert runtime.stopped_count == 1
            assert runtime.is_running is False

    def test_30_idempotency_key_lifecycle_preserved_across_retries(self, temp_outbox):
        """
        30. Verify idempotency key is generated ONCE and preserved in SQLite across retries.
        Retries must never regenerate UUID, timestamp, or key.
        """
        initial_key = "metric_101_1727400000_deadbeef"
        payload = {"cpu_usage": 88.0, "ram_usage": 72.0}

        # Step 1: Enqueue event once
        rec = temp_outbox.enqueue(
            event_type="metrics",
            payload=payload,
            idempotency_key=initial_key,
            priority=OutboxPriority.TELEMETRY,
        )
        assert rec.idempotency_key == initial_key

        received_keys: list[str] = []

        def mock_send(p, tok):
            # Record the idempotency key passed to the sender
            received_keys.append(p.get("idempotency_key"))
            if len(received_keys) == 1:
                # First attempt fails with network error
                raise ConnectionError("Connection reset by peer")
            # Second attempt succeeds
            return {"id": 1}

        worker = OutboxDeliveryWorker(
            outbox=temp_outbox,
            get_token=lambda: "valid_token",
        )

        with patch("core.outbox.worker.send_metrics", side_effect=mock_send):
            # Attempt 1: Fails
            worker.drain_once()
            assert len(received_keys) == 1
            assert received_keys[0] == initial_key

            # Item must be in RETRY status with same key in SQLite
            conn = sqlite3.connect(temp_outbox.db_path)
            cur = conn.cursor()
            cur.execute("SELECT idempotency_key, attempt_count, status FROM outbox_items WHERE id = ?", (rec.id,))
            row = cur.fetchone()
            conn.close()
            assert row[0] == initial_key
            assert row[1] == 1
            assert row[2] == OutboxStatus.PENDING.value

            # Reset next_attempt_at so it is immediately eligible for retry
            conn = sqlite3.connect(temp_outbox.db_path)
            conn.execute("UPDATE outbox_items SET next_attempt_at = 0 WHERE id = ?", (rec.id,))
            conn.commit()
            conn.close()

            # Attempt 2: Retries with exact same key
            worker.drain_once()
            assert len(received_keys) == 2
            assert received_keys[1] == initial_key

        assert received_keys[0] == received_keys[1] == initial_key
        assert temp_outbox.get_stats()["total_count"] == 0

    def test_31_backpressure_queue_full_behavior(self, tmp_path):
        """
        31. Verify QueueFullError behavior:
        - When queue is saturated with critical events, lower/same priority enqueue raises QueueFullError
        - Producers log error, return False, do not raise unhandled exception, and no unbounded memory fallback occurs
        - Monitoring loop remains healthy
        """
        db_file = str(tmp_path / "queue_full.db")
        # Capacity of 3 records
        small_outbox = DurableOutbox(db_path=db_file, max_records=3)

        # Fill entirely with critical items
        for i in range(3):
            small_outbox.enqueue(
                event_type="command_result",
                payload={"command_id": i, "success": True},
                idempotency_key=f"cmd_{i}",
                priority=OutboxPriority.COMMAND,
            )

        assert small_outbox.get_stats()["total_count"] == 3

        # Saturated with critical items: new enqueue must raise QueueFullError
        with pytest.raises(QueueFullError):
            small_outbox.enqueue(
                event_type="metrics",
                payload={"cpu_usage": 99.0},
                idempotency_key="metric_overflow",
                priority=OutboxPriority.TELEMETRY,
            )

        # Verify producers catch QueueFullError, log, and return False safely
        from core.runtime import (
            upload_metrics,
            upload_software,
            upload_processes,
            upload_usage,
            upload_issues,
            TokenHolder,
        )

        token_holder = TokenHolder("dummy_token")
        data = {
            "hardware": {"cpu_usage": 50},
            "software": [{"name": "app"}],
            "processes": [{"pid": 1, "name": "proc"}],
            "usage": [{"application_name": "app.exe", "duration_seconds": 10}],
            "issues": [{"title": "Disk Full", "description": "Full", "severity": "high"}],
        }

        with patch("core.runtime.get_computer_id", return_value=123):
            assert upload_metrics(data, token_holder, outbox=small_outbox) is False
            assert upload_software(data, token_holder, outbox=small_outbox) is False
            assert upload_processes(data, token_holder, outbox=small_outbox) is False
            assert upload_usage(data, token_holder, outbox=small_outbox) is False
            assert upload_issues(data, token_holder, outbox=small_outbox) is False

        # Queue size must strictly remain capped at max_records (no unbounded fallback)
        assert small_outbox.get_stats()["total_count"] == 3


# ============================================================================
# Regression Tests: Outbox PROCESSING Recovery & Offline Token Drainage
# ============================================================================

class TestOutboxProcessingRecoveryAndOfflineDrain:
    """Regression tests for Task 4 & Task 1 outbox delivery invariants."""

    def test_33_worker_startup_recovers_stale_processing_immediately(self, tmp_path):
        """
        Verify that when OutboxDeliveryWorker starts up, any records stranded
        in PROCESSING status (from a previous crashed process) are recovered to PENDING
        immediately, even if less than 60 seconds have elapsed.
        """
        db_file = str(tmp_path / "proc_recovery.db")
        outbox = DurableOutbox(db_path=db_file)

        # 1. Enqueue 5 items
        for i in range(5):
            outbox.enqueue("metrics", {"i": i}, f"key_rec_{i}")

        # 2. Claim all 5 into PROCESSING
        batch = outbox.get_pending_batch(limit=10)
        assert len(batch) == 5
        assert all(item.status == OutboxStatus.PROCESSING for item in batch)
        assert outbox.get_stats()["status_counts"].get(OutboxStatus.PROCESSING.value, 0) == 5
        assert outbox.get_stats()["status_counts"].get(OutboxStatus.PENDING.value, 0) == 0

        # 3. Start a new worker (simulating service restart after crash)
        stop_event = threading.Event()
        delivered_count = 0

        def mock_delivered(item):
            nonlocal delivered_count
            delivered_count += 1

        worker = OutboxDeliveryWorker(
            outbox=outbox,
            get_token=lambda: "valid.jwt.token",
            stop_event=stop_event,
            on_delivered=mock_delivered,
            poll_interval=0.05,
        )

        with patch("core.outbox.worker.send_metrics") as mock_send:
            worker.start()
            # Give worker brief time to run loop startup recovery and drain
            time.sleep(0.3)
            worker.stop()

        # All 5 items should have been recovered and delivered
        assert delivered_count == 5
        assert mock_send.call_count == 5
        stats = outbox.get_stats()
        assert stats["total_count"] == 0
        assert stats["status_counts"].get(OutboxStatus.PROCESSING.value, 0) == 0

    def test_34_outbox_offline_token_recovery_drains_pending(self, tmp_path):
        """
        Verify that items enqueued while token is empty are held with backoff,
        and as soon as refresh_token succeeds, the outbox worker drains all buffered items.
        """
        db_file = str(tmp_path / "offline_token_drain.db")
        outbox = DurableOutbox(db_path=db_file)

        # Enqueue 3 items
        for i in range(3):
            outbox.enqueue("metrics", {"val": i}, f"offline_key_{i}")

        token_state = {"token": "", "backend_online": False}

        def get_token():
            return token_state["token"]

        def refresh_token():
            if not token_state["backend_online"]:
                raise requests.ConnectionError("Backend still offline")
            token_state["token"] = "recovered.token.123"
            return token_state["token"]

        worker = OutboxDeliveryWorker(
            outbox=outbox,
            get_token=get_token,
            refresh_token=refresh_token,
        )

        # First drain: backend offline -> items marked for retry
        with patch("core.outbox.worker.send_metrics"):
            worker.drain_once()

        stats = outbox.get_stats()
        assert stats["total_count"] == 3

        # Simulate backend returning online
        token_state["backend_online"] = True

        with patch("core.outbox.worker.send_metrics") as mock_send, \
             patch("time.time", return_value=time.time() + 1000.0):
            worker.drain_once()

        assert mock_send.call_count == 3
        assert token_state["token"] == "recovered.token.123"
        assert outbox.get_stats()["total_count"] == 0

    def test_35_historical_dead_letter_records_preserved_during_recovery(self, tmp_path):
        """
        Verify recover_stale_processing strictly preserves existing DEAD_LETTER records
        and only affects PROCESSING rows.
        """
        db_file = str(tmp_path / "dead_letter_preserve.db")
        outbox = DurableOutbox(db_path=db_file)

        # Create 2 DEAD_LETTER items
        rec1 = outbox.enqueue("metrics", {"a": 1}, "dl_1")
        rec2 = outbox.enqueue("metrics", {"a": 2}, "dl_2")
        outbox.mark_dead_letter(rec1.id, "Permanent 400 Bad Request")
        outbox.mark_dead_letter(rec2.id, "Permanent 404 Not Found")

        # Create 1 PROCESSING item
        outbox.enqueue("metrics", {"a": 3}, "proc_1")
        claimed = outbox.get_pending_batch(limit=1)
        assert len(claimed) == 1

        stats_before = outbox.get_stats()
        assert stats_before["status_counts"].get(OutboxStatus.DEAD_LETTER.value, 0) == 2
        assert stats_before["status_counts"].get(OutboxStatus.PROCESSING.value, 0) == 1

        # Run recovery
        recovered = outbox.recover_stale_processing(stale_threshold_seconds=0.0)
        assert recovered == 1

        stats_after = outbox.get_stats()
        # DEAD_LETTER count must remain untouched at 2
        assert stats_after["status_counts"].get(OutboxStatus.DEAD_LETTER.value, 0) == 2
        assert stats_after["status_counts"].get(OutboxStatus.PROCESSING.value, 0) == 0
        assert stats_after["status_counts"].get(OutboxStatus.PENDING.value, 0) == 1


class TestAuthenticationRetryStormPrevention:
    """Tests verifying prevention of authentication retry storms and attempt count preservation."""

    def test_token_manager_exponential_backoff_and_cooldown(self):
        """Verify TokenManager throttles failed authentications with exponential backoff."""
        from core.managers import TokenManager
        from core.security import InsecureHttpProhibitedError

        tm = TokenManager(
            refresh_interval=60.0,
            initial_backoff=2.0,
            max_backoff=30.0,
            backoff_factor=2.0,
            jitter_ratio=0.0,  # deterministic for test
        )

        auth_mock = MagicMock(side_effect=InsecureHttpProhibitedError("Insecure HTTP prohibited"))

        with patch("core.managers._resolve_authenticate_agent", auth_mock):
            # Attempt 1: Fails
            with pytest.raises(InsecureHttpProhibitedError):
                tm.refresh()

            assert tm.consecutive_failures == 1
            assert tm.is_in_cooldown() is True
            assert 1.5 <= tm.cooldown_remaining() <= 2.5
            assert auth_mock.call_count == 1

            # Immediate repeat: Blocked by cooldown without calling auth again
            with pytest.raises(InsecureHttpProhibitedError):
                tm.refresh()
            assert auth_mock.call_count == 1  # Still 1!

            # Advance past first cooldown (2s)
            with patch("time.monotonic", return_value=time.monotonic() + 3.0):
                assert tm.is_in_cooldown() is False
                with pytest.raises(InsecureHttpProhibitedError):
                    tm.refresh()
                assert auth_mock.call_count == 2
                assert tm.consecutive_failures == 2
                # Next backoff: ~4s
                assert 3.5 <= tm.cooldown_remaining() <= 4.5

    def test_successful_auth_resets_backoff(self):
        """Verify successful authentication resets consecutive failures and cooldown."""
        from core.managers import TokenManager

        tm = TokenManager(initial_backoff=2.0, jitter_ratio=0.0)

        # Trigger failure
        with patch("core.managers._resolve_authenticate_agent", side_effect=RuntimeError("Auth error")):
            with pytest.raises(RuntimeError):
                tm.refresh()
            assert tm.consecutive_failures == 1
            assert tm.is_in_cooldown() is True

        # Successful auth
        with patch("core.managers._resolve_authenticate_agent", return_value="fresh.jwt.token"):
            token = tm.refresh(force=True)
            assert token == "fresh.jwt.token"
            assert tm.token == "fresh.jwt.token"
            assert tm.consecutive_failures == 0
            assert tm.is_in_cooldown() is False
            assert tm.cooldown_remaining() == 0.0

    def test_multiple_outbox_items_no_token_single_auth_and_no_attempt_burn(self, tmp_path):
        """
        CRITICAL TEST: When token is missing, multiple pending outbox items must NOT
        cause multiple auth requests or burn individual item attempt_count counters.
        """
        from core.managers import TokenManager
        from core.security import InsecureHttpProhibitedError

        db_file = str(tmp_path / "no_storm.db")
        outbox = DurableOutbox(db_path=db_file)

        # Enqueue 10 telemetry items
        for i in range(10):
            outbox.enqueue("metrics", {"metric_idx": i}, f"key_{i}")

        tm = TokenManager(initial_backoff=5.0, jitter_ratio=0.0)
        auth_mock = MagicMock(side_effect=InsecureHttpProhibitedError("HTTP URL prohibited"))

        worker = OutboxDeliveryWorker(
            outbox=outbox,
            get_token=lambda: tm.token,
            refresh_token=tm.refresh,
        )

        with patch("core.managers._resolve_authenticate_agent", auth_mock), \
             patch("core.outbox.worker.send_metrics") as mock_send:

            # Drain once
            has_more = worker.drain_once()
            assert has_more is False
            # Exactly 1 auth request attempted despite 10 items in queue
            assert auth_mock.call_count == 1
            assert mock_send.call_count == 0

            # Drain again immediately (cooldown active)
            worker.drain_once()
            assert auth_mock.call_count == 1  # Still exactly 1!

        # Verify ALL 10 items remain in PENDING status with attempt_count == 0 (NO BURNING)
        stats = outbox.get_stats()
        assert stats["total_count"] == 10
        assert stats["status_counts"].get(OutboxStatus.PENDING.value) == 10
        assert stats["status_counts"].get(OutboxStatus.DEAD_LETTER.value, 0) == 0

        batch = outbox.get_pending_batch(limit=10)
        for item in batch:
            assert item.attempt_count == 0

    def test_auth_recovery_delivers_all_buffered_items(self, tmp_path):
        """Verify that once auth recovers, all buffered outbox items are delivered cleanly."""
        from core.managers import TokenManager

        db_file = str(tmp_path / "recovery.db")
        outbox = DurableOutbox(db_path=db_file)

        for i in range(5):
            outbox.enqueue("metrics", {"data": i}, f"rec_key_{i}")

        tm = TokenManager()
        worker = OutboxDeliveryWorker(
            outbox=outbox,
            get_token=lambda: tm.token,
            refresh_token=tm.refresh,
        )

        # 1. Auth fails
        with patch("core.managers._resolve_authenticate_agent", side_effect=ConnectionError("Offline")):
            worker.drain_once()
            assert outbox.get_stats()["total_count"] == 5

        # 2. Auth recovers
        with patch("core.managers._resolve_authenticate_agent", return_value="valid.jwt.token"), \
             patch("core.outbox.worker.send_metrics") as mock_send:
            tm.refresh(force=True)
            worker.drain_once()
            assert mock_send.call_count == 5

        assert outbox.get_stats()["total_count"] == 0

    def test_http_401_mid_batch_auth_failure_releases_all_items_without_attempt_burn(self, tmp_path):
        """
        Regression test: When an item delivery encounters HTTP 401 and re-authentication
        fails, the failed item and all remaining batch items must be released back to
        PENDING without incrementing attempt_count, and batch processing must stop immediately.
        """
        from core.managers import TokenManager

        db_file = str(tmp_path / "mid_batch_401.db")
        outbox = DurableOutbox(db_path=db_file)

        # Enqueue 3 items
        for i in range(3):
            outbox.enqueue("metrics", {"idx": i}, f"key_401_{i}")

        tm = TokenManager()
        tm.set_token("initial.valid.token")

        worker = OutboxDeliveryWorker(
            outbox=outbox,
            get_token=lambda: tm.token,
            refresh_token=tm.refresh,
            batch_size=10,
        )

        # First item raises 401 Unauthorized
        mock_401_resp = requests.Response()
        mock_401_resp.status_code = 401
        http_401_err = requests.HTTPError("401 Unauthorized", response=mock_401_resp)

        send_mock = MagicMock(side_effect=http_401_err)
        auth_mock = MagicMock(side_effect=ConnectionError("Backend unreachable during re-auth"))

        with patch("core.outbox.worker.send_metrics", send_mock), \
             patch("core.managers._resolve_authenticate_agent", auth_mock):

            has_more = worker.drain_once()
            assert has_more is False

            # Exactly 1 send attempt made (for first item)
            assert send_mock.call_count == 1
            # Exactly 1 re-auth attempt made
            assert auth_mock.call_count == 1

        # Verify all 3 items are returned to PENDING and attempt_count is 0 for ALL of them
        stats = outbox.get_stats()
        assert stats["total_count"] == 3
        assert stats["status_counts"].get(OutboxStatus.PENDING.value) == 3
        assert stats["status_counts"].get(OutboxStatus.PROCESSING.value, 0) == 0
        assert stats["status_counts"].get(OutboxStatus.DEAD_LETTER.value, 0) == 0

        batch = outbox.get_pending_batch(limit=10)
        assert len(batch) == 3
        for item in batch:
            assert item.attempt_count == 0
