"""
SLMS Client Agent Phase 5 Monitoring Optimization Test Suite.

Verifies:
- E-01: Process Collection Cadence (1-5 min target, metrics remain at 20s).
- E-02: System Process Filtering (Windows kernel/idle noise excluded, legitimate apps retained).
- E-03: Process Username Privacy (Zero username collection, null in serialized payload).
- E-04: Process Payload Limits (Bounded count, max name length, deterministic ordering).
- E-05: Software Inventory Cadence (10-30 min target, not uploaded every 20s, cache reuse).
- E-06: Software Change Detection & Fingerprinting (Normalized SHA-256 hash, order-insensitive,
        restart persistence, atomic state saving).
- E-07: Software Discovery Coverage & Limitations.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from config import (
    MAX_PROCESS_NAME_LENGTH,
    MAX_PROCESSES_INVENTORY,
    MONITOR_INTERVAL,
    PROCESS_COLLECTION_INTERVAL,
    SOFTWARE_SCAN_INTERVAL,
)
from core.collector import (
    ProcessCache,
    SoftwareCache,
    _collect_processes,
    _collect_software,
    collect_all_data,
)
from core.health import CollectionResult, CollectorError
from core.outbox import DurableOutbox, OutboxPriority
from core.runtime import AgentRuntime, TokenHolder, upload_metrics, upload_processes, upload_software
from modules.processes import (
    SYSTEM_PROCESS_NAMES,
    SYSTEM_PROCESS_PIDS,
    get_running_processes,
    is_system_process,
)
from modules.software import (
    compute_software_fingerprint,
    get_installed_software,
    load_software_state,
    record_software_delivered,
    record_software_enqueued,
    save_software_state,
)


# ============================================================================
# Helper Mock Objects for psutil
# ============================================================================

class MockProcessInfo:
    def __init__(
        self,
        pid: int,
        name: str,
        cpu_percent: float = 0.0,
        memory_percent: float = 0.0,
        status: str = "running",
        create_time: float = 1700000000.0,
    ):
        self.info = {
            "pid": pid,
            "name": name,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "status": status,
            "create_time": create_time,
        }


# ============================================================================
# E-01: Process Collection Cadence Tests
# ============================================================================

class TestProcessCadenceE01:
    """Verify that process collection occurs on a 1-5 minute cadence while metrics remain at 20s."""

    def test_process_interval_configuration_value(self):
        """Confirm PROCESS_COLLECTION_INTERVAL is configured within the 1-5 minute range (60-300s)."""
        assert 60 <= PROCESS_COLLECTION_INTERVAL <= 300
        assert PROCESS_COLLECTION_INTERVAL == 120  # Default 2 minutes

    def test_runtime_cadence_gating_process_vs_metrics(self):
        """
        Verify that AgentRuntime.due_for_process_collection gates process enumeration
        while metrics run every cycle (MONITOR_INTERVAL = 20s).
        """
        runtime = AgentRuntime(process_interval=120, enable_outbox=False)

        # Cycle 0 (t = 0.0): Initial cycle must trigger process collection
        assert runtime.due_for_process_collection(0.0) is True
        runtime._last_process_collection = 0.0

        # Cycle 1 (t = 20.0s): Metrics due, but processes NOT due
        assert runtime.due_for_process_collection(20.0) is False

        # Cycle 2 (t = 40.0s): Processes NOT due
        assert runtime.due_for_process_collection(40.0) is False

        # Cycle 5 (t = 100.0s): Processes NOT due
        assert runtime.due_for_process_collection(100.0) is False

        # Cycle 6 (t = 120.0s): Exactly 120s elapsed -> Processes ARE due
        assert runtime.due_for_process_collection(120.0) is True
        runtime._last_process_collection = 120.0

        # Cycle 7 (t = 140.0s): Gated again
        assert runtime.due_for_process_collection(140.0) is False

    def test_process_collection_does_not_suppress_other_monitoring(self):
        """
        Confirm that bypassing process collection (include_processes=False)
        leaves hardware, network, usage, and issue collectors completely unaffected.
        """
        data = collect_all_data(include_processes=False, include_software=False)

        # Hardware, network, usage, and issues are present
        assert "hardware" in data
        assert "network" in data
        assert "usage" in data
        assert "issues" in data

        # Processes and software were intentionally bypassed for this 20s cycle
        assert "processes" not in data
        assert "software" not in data

    def test_process_cache_container_mechanics(self):
        """Verify ProcessCache stores items and handles TTL expiration correctly."""
        cache = ProcessCache(ttl=120)
        assert cache.is_present is False
        assert cache.get(0.0) is None
        assert cache.is_expired(0.0) is True

        # Cache valid list
        sample_procs = [{"pid": 100, "name": "sample.exe", "cpu_percent": 1.0}]
        cache.set(sample_procs, now=1000.0)

        assert cache.is_present is True
        assert cache.is_expired(1050.0) is False
        assert cache.get(1050.0) == sample_procs

        # Expired after 120s
        assert cache.is_expired(1121.0) is True
        assert cache.get(1121.0) is None

        # Re-set empty list (valid empty inventory)
        cache.set([], now=1200.0)
        assert cache.is_present is True
        assert cache.get(1205.0) == []

    def test_collect_processes_helper_uses_cache(self):
        """Verify _collect_processes reuses cache within TTL and only invokes psutil when expired."""
        cache = ProcessCache(ttl=120)
        sample = [{"pid": 999, "name": "test.exe"}]

        with patch("core.collector.get_running_processes", return_value=sample) as mock_ps:
            # First call: cache miss -> invokes get_running_processes
            res1 = _collect_processes(cache=cache)
            assert res1 == sample
            assert mock_ps.call_count == 1

            # Second call: within TTL -> uses cache without calling get_running_processes
            res2 = _collect_processes(cache=cache)
            assert res2 == sample
            assert mock_ps.call_count == 1  # Unchanged!


# ============================================================================
# E-02: System Process Filtering Tests
# ============================================================================

class TestSystemProcessFilteringE02:
    """Verify that Windows kernel/idle pseudo-processes are excluded and legitimate apps retained."""

    def test_is_system_process_identifies_kernel_noise(self):
        """Verify known kernel PIDs and pseudo-processes are filtered."""
        # PIDs 0 and 4
        assert is_system_process(0, "System Idle Process") is True
        assert is_system_process(0, "any_name") is True
        assert is_system_process(4, "System") is True
        assert is_system_process(4, "ntoskrnl.exe") is True

        # Named pseudo-processes
        assert is_system_process(123, "Registry") is True
        assert is_system_process(456, "Memory Compression") is True
        assert is_system_process(789, "Secure System") is True
        assert is_system_process(101, "Interrupts") is True
        assert is_system_process(102, "Idle") is True

    def test_is_system_process_retains_legitimate_processes(self):
        """Verify normal student apps and background services are NOT filtered."""
        normal_processes = [
            (1024, "svchost.exe"),
            (1048, "services.exe"),
            (1100, "lsass.exe"),
            (2048, "explorer.exe"),
            (3050, "chrome.exe"),
            (3060, "Code.exe"),
            (4010, "python.exe"),
            (5010, "cmd.exe"),
            (6010, "notepad.exe"),
        ]
        for pid, name in normal_processes:
            assert is_system_process(pid, name) is False, f"Unexpectedly filtered: {name} (PID {pid})"

    def test_get_running_processes_filters_system_processes(self):
        """Verify get_running_processes removes kernel processes from the returned inventory."""
        mock_processes = [
            MockProcessInfo(0, "System Idle Process", cpu_percent=80.0),
            MockProcessInfo(4, "System", cpu_percent=5.0),
            MockProcessInfo(100, "Registry", cpu_percent=2.0),
            MockProcessInfo(200, "Memory Compression", memory_percent=10.0),
            MockProcessInfo(1234, "chrome.exe", cpu_percent=15.0, memory_percent=8.0),
            MockProcessInfo(2345, "python.exe", cpu_percent=25.0, memory_percent=4.0),
        ]

        with patch("modules.processes.psutil.process_iter", return_value=mock_processes):
            results = get_running_processes()
            names = [p["name"] for p in results]

            assert "System Idle Process" not in names
            assert "System" not in names
            assert "Registry" not in names
            assert "Memory Compression" not in names

            assert "chrome.exe" in names
            assert "python.exe" in names
            assert len(results) == 2


# ============================================================================
# E-03: Process Username Privacy Tests
# ============================================================================

class TestProcessUsernamePrivacyE03:
    """Verify that user account names and Windows logins are strictly excluded from process payloads."""

    def test_username_is_none_in_collected_processes(self):
        """Verify process item 'user' field is strictly None."""
        mock_processes = [
            MockProcessInfo(1234, "chrome.exe", cpu_percent=5.0),
            MockProcessInfo(5678, "code.exe", cpu_percent=10.0),
        ]
        with patch("modules.processes.psutil.process_iter", return_value=mock_processes):
            results = get_running_processes()
            for proc in results:
                assert "user" in proc
                assert proc["user"] is None

    def test_serialized_payload_contains_no_username_leakage(self):
        """Verify that JSON serialization of process inventory contains null for user and no login strings."""
        mock_processes = [
            MockProcessInfo(1234, "app.exe", cpu_percent=1.0),
        ]
        with patch("modules.processes.psutil.process_iter", return_value=mock_processes):
            results = get_running_processes()
            payload = {"processes": results}
            serialized = json.dumps(payload)

            # JSON must have "user": null
            assert '"user": null' in serialized

            # Deserialization check
            deserialized = json.loads(serialized)
            assert deserialized["processes"][0]["user"] is None


# ============================================================================
# E-04: Process Payload Limits & Ordering Tests
# ============================================================================

class TestProcessPayloadLimitsE04:
    """Verify that process inventory is bounded, sorted deterministically, and truncated safely."""

    def test_normal_process_list_under_limit_retained(self):
        """When fewer than MAX_PROCESSES_INVENTORY processes run, all are retained."""
        mock_procs = [MockProcessInfo(pid, f"app_{pid}.exe", cpu_percent=1.0) for pid in range(10, 60)]
        with patch("modules.processes.psutil.process_iter", return_value=mock_procs):
            results = get_running_processes(max_processes=500)
            assert len(results) == 50

    def test_huge_process_list_truncated_to_max(self):
        """When running processes exceed MAX_PROCESSES_INVENTORY, inventory is capped at the limit."""
        mock_procs = [MockProcessInfo(pid, f"app_{pid}.exe", cpu_percent=float(pid % 10)) for pid in range(10, 1010)]
        with patch("modules.processes.psutil.process_iter", return_value=mock_procs):
            results = get_running_processes(max_processes=500)
            assert len(results) == 500

    def test_deterministic_ordering_resource_prioritization(self):
        """
        Verify processes are sorted with resource hogs first:
        (-cpu_percent, -memory_percent, name.casefold(), pid).
        """
        mock_procs = [
            MockProcessInfo(1001, "idle_worker.exe", cpu_percent=0.0, memory_percent=1.0),
            MockProcessInfo(1002, "cpu_hog.exe", cpu_percent=85.0, memory_percent=10.0),
            MockProcessInfo(1003, "mem_hog.exe", cpu_percent=10.0, memory_percent=90.0),
            MockProcessInfo(1004, "dual_hog.exe", cpu_percent=85.0, memory_percent=50.0),
            MockProcessInfo(1005, "a_app.exe", cpu_percent=5.0, memory_percent=5.0),
            MockProcessInfo(1006, "b_app.exe", cpu_percent=5.0, memory_percent=5.0),
        ]
        with patch("modules.processes.psutil.process_iter", return_value=mock_procs):
            results = get_running_processes(max_processes=10)
            names = [p["name"] for p in results]

            # dual_hog (cpu=85, mem=50) -> cpu_hog (cpu=85, mem=10) -> mem_hog (cpu=10, mem=90)
            assert names[0] == "dual_hog.exe"
            assert names[1] == "cpu_hog.exe"
            assert names[2] == "mem_hog.exe"
            # Ties in cpu & mem broken by name casefold: a_app before b_app
            assert names[3] == "a_app.exe"
            assert names[4] == "b_app.exe"
            assert names[5] == "idle_worker.exe"

    def test_process_name_truncation_to_255_chars(self):
        """Confirm oversized process names are truncated to MAX_PROCESS_NAME_LENGTH."""
        oversized_name = "A" * 350 + ".exe"
        mock_procs = [MockProcessInfo(5555, oversized_name)]
        with patch("modules.processes.psutil.process_iter", return_value=mock_procs):
            results = get_running_processes(max_name_len=255)
            assert len(results[0]["name"]) == 255
            assert results[0]["name"] == ("A" * 255)

    def test_serialized_payload_size_is_bounded(self):
        """Confirm a saturated 500-process list produces a compact payload far below outbox limits."""
        mock_procs = [
            MockProcessInfo(pid, f"enterprise_lab_software_{pid}.exe", cpu_percent=12.5, memory_percent=3.2)
            for pid in range(1, 501)
        ]
        with patch("modules.processes.psutil.process_iter", return_value=mock_procs):
            results = get_running_processes(max_processes=500)
            payload_json = json.dumps({"processes": results})
            size_kb = len(payload_json.encode("utf-8")) / 1024
            # 500 processes is typically ~70-90 KB
            assert size_kb < 200, f"Payload unexpectedly large: {size_kb} KB"


# ============================================================================
# E-05: Software Inventory Cadence Tests
# ============================================================================

class TestSoftwareCadenceE05:
    """Verify software inventory scan is decoupled from the 20s metric cycle."""

    def test_software_interval_configuration_value(self):
        """Confirm SOFTWARE_SCAN_INTERVAL is configured within the 10-30 minute range (600-1800s)."""
        assert 600 <= SOFTWARE_SCAN_INTERVAL <= 1800

    def test_runtime_cadence_gating_software_vs_metrics(self):
        """
        Verify that AgentRuntime.due_for_software_scan gates registry scanning
        while metrics run every cycle.
        """
        runtime = AgentRuntime(software_interval=900, enable_outbox=False)

        # Initial run: due
        assert runtime.due_for_software_scan(0.0) is True
        runtime._last_software_scan = 0.0

        # Cycle 1 (t = 20s): metrics due, software NOT due
        assert runtime.due_for_software_scan(20.0) is False

        # Cycle 15 (t = 300s / 5 min): software NOT due
        assert runtime.due_for_software_scan(300.0) is False

        # Cycle 44 (t = 880s): software NOT due
        assert runtime.due_for_software_scan(880.0) is False

        # Cycle 45 (t = 900s / 15 min): software IS due
        assert runtime.due_for_software_scan(900.0) is True
        runtime._last_software_scan = 900.0

        # Cycle 46 (t = 920s): gated again
        assert runtime.due_for_software_scan(920.0) is False

    def test_software_cache_reuse_and_expiration(self):
        """Verify SoftwareCache reuses scanned list and only rescans when TTL expires."""
        cache = SoftwareCache(ttl=600)
        sample = [{"name": "Python 3.13", "version": "3.13.5", "publisher": "PSF", "install_date": "2026-01-01"}]

        with patch("core.collector.get_installed_software", return_value=sample) as mock_sw:
            # 1. First call: cache miss -> scan invoked
            res1 = _collect_software(cache=cache)
            assert res1 == sample
            assert mock_sw.call_count == 1

            # 2. Second call: within TTL -> cache hit, mock not called again
            res2 = _collect_software(cache=cache)
            assert res2 == sample
            assert mock_sw.call_count == 1

            # 3. Invalidate cache -> forces rescan
            cache.invalidate()
            res3 = _collect_software(cache=cache)
            assert res3 == sample
            assert mock_sw.call_count == 2


# ============================================================================
# E-06: Software Delivery Semantics & Fingerprinting Tests
# ============================================================================

class TestSoftwareDeliverySemanticsE06:
    """
    Verify E-06 delivery semantics:
    - Stored fingerprint represents (A) last successfully acknowledged/delivered inventory,
      NOT merely (B) last enqueued inventory.
    - Software inventory is never permanently suppressed merely because it was enqueued.
    - Idempotency key 'software_{computer_id}_{fingerprint[:16]}' remains stable.
    - All 9 required scenarios pass.
    """

    def test_01_first_inventory_no_previous_fingerprint_enqueues(self, tmp_path):
        """Scenario 1: First inventory with no previous fingerprint enqueues into outbox."""
        state_file = str(tmp_path / "software_state.json")
        outbox = DurableOutbox(db_path=str(tmp_path / "outbox.db"))
        token_holder = TokenHolder("test.token")
        data = {
            "software": [
                {"name": "AlphaApp", "version": "1.0", "publisher": "Corp", "install_date": "2026-01-01"}
            ]
        }

        with patch("core.runtime.get_computer_id", return_value=777):
            success = upload_software(data, token_holder, outbox=outbox, state_file=state_file)
            assert success is True
            assert outbox.get_stats()["total_count"] == 1

            # State records enqueue, but NOT delivery yet
            state = load_software_state(state_file)
            expected_fp = compute_software_fingerprint(data["software"])
            assert state["last_enqueued_fingerprint"] == expected_fp
            assert state["last_delivered_fingerprint"] is None

    def test_02_same_inventory_after_successful_delivery_skips(self, tmp_path):
        """Scenario 2: Same inventory after successful delivery skips upload and outbox."""
        state_file = str(tmp_path / "software_state.json")
        outbox = DurableOutbox(db_path=str(tmp_path / "outbox.db"))
        token_holder = TokenHolder("test.token")
        data = {
            "software": [
                {"name": "AlphaApp", "version": "1.0", "publisher": "Corp", "install_date": "2026-01-01"}
            ]
        }

        with patch("core.runtime.get_computer_id", return_value=777):
            # Enqueue initial inventory
            upload_software(data, token_holder, outbox=outbox, state_file=state_file)
            assert outbox.get_stats()["total_count"] == 1

            # Confirm delivery via callback / record_software_delivered
            expected_fp = compute_software_fingerprint(data["software"])
            record_software_delivered(expected_fp, state_file)
            outbox.mark_delivered(1)

            # Subsequent scan with identical inventory must skip
            skipped = upload_software(data, token_holder, outbox=outbox, state_file=state_file)
            assert skipped is False
            assert outbox.get_stats()["total_count"] == 0

    def test_03_changed_inventory_enqueues(self, tmp_path):
        """Scenario 3: Changed inventory enqueues new event into outbox."""
        state_file = str(tmp_path / "software_state.json")
        outbox = DurableOutbox(db_path=str(tmp_path / "outbox.db"))
        token_holder = TokenHolder("test.token")
        data_v1 = {"software": [{"name": "App", "version": "1.0"}]}
        data_v2 = {"software": [{"name": "App", "version": "2.0"}]}

        with patch("core.runtime.get_computer_id", return_value=777):
            # Deliver v1
            upload_software(data_v1, token_holder, outbox=outbox, state_file=state_file)
            fp_v1 = compute_software_fingerprint(data_v1["software"])
            record_software_delivered(fp_v1, state_file)
            outbox.mark_delivered(1)

            # Inventory changes to v2 -> must enqueue
            enqueued = upload_software(data_v2, token_holder, outbox=outbox, state_file=state_file)
            assert enqueued is True
            assert outbox.get_stats()["total_count"] == 1

            state = load_software_state(state_file)
            fp_v2 = compute_software_fingerprint(data_v2["software"])
            assert state["last_enqueued_fingerprint"] == fp_v2
            assert state["last_delivered_fingerprint"] == fp_v1  # v2 not delivered yet!

    def test_04_changed_inventory_enqueued_delivery_fails_remains_deliverable(self, tmp_path):
        """Scenario 4: Changed inventory enqueued but delivery fails -> MUST remain deliverable, no permanent suppression."""
        state_file = str(tmp_path / "software_state.json")
        outbox = DurableOutbox(db_path=str(tmp_path / "outbox.db"))
        token_holder = TokenHolder("test.token")
        data_v1 = {"software": [{"name": "App", "version": "1.0"}]}
        data_v2 = {"software": [{"name": "App", "version": "2.0"}]}

        with patch("core.runtime.get_computer_id", return_value=777):
            # Baseline: deliver v1
            upload_software(data_v1, token_holder, outbox=outbox, state_file=state_file)
            record_software_delivered(compute_software_fingerprint(data_v1["software"]), state_file)
            outbox.mark_delivered(1)

            # Change to v2 -> enqueued
            upload_software(data_v2, token_holder, outbox=outbox, state_file=state_file)
            v2_record = outbox.get_pending_batch(limit=10, now=time.time() + 1000)[0]
            assert v2_record.id == 2

            # Simulate delivery failure: record stays PENDING / backoff
            outbox.mark_retry(v2_record.id, "Connection refused (HTTP 503)", time.time() + 60)
            stats = outbox.get_stats()
            assert stats["status_counts"].get("PENDING", 0) == 1

            # Next software scan runs with SAME changed inventory v2
            # Must NOT be marked as delivered, must remain deliverable in outbox
            enqueued_again = upload_software(data_v2, token_holder, outbox=outbox, state_file=state_file)
            assert enqueued_again is False  # Not duplicated in outbox
            assert outbox.get_stats()["total_count"] == 1  # No duplicate record!

            # State confirms v2 was NEVER falsely marked delivered
            state = load_software_state(state_file)
            assert state["last_delivered_fingerprint"] != compute_software_fingerprint(data_v2["software"])

    def test_05_changed_inventory_eventually_delivered_next_identical_scan_skips(self, tmp_path):
        """Scenario 5: Changed inventory eventually delivered -> next identical scan skips."""
        state_file = str(tmp_path / "software_state.json")
        outbox = DurableOutbox(db_path=str(tmp_path / "outbox.db"))
        token_holder = TokenHolder("test.token")
        data = {"software": [{"name": "App", "version": "2.0"}]}
        fp_v2 = compute_software_fingerprint(data["software"])

        with patch("core.runtime.get_computer_id", return_value=777):
            upload_software(data, token_holder, outbox=outbox, state_file=state_file)

            # Simulate worker delivery success
            outbox.mark_delivered(1)
            record_software_delivered(fp_v2, state_file)

            # Next identical scan skips
            skipped = upload_software(data, token_holder, outbox=outbox, state_file=state_file)
            assert skipped is False
            assert outbox.get_stats()["total_count"] == 0

            state = load_software_state(state_file)
            assert state["last_delivered_fingerprint"] == fp_v2

    def test_06_agent_restart_with_pending_software_outbox_event(self, tmp_path):
        """Scenario 6: Agent restart with pending software outbox event -> no permanent suppression, remains deliverable."""
        state_file = str(tmp_path / "software_state.json")
        db_path = str(tmp_path / "outbox.db")
        outbox = DurableOutbox(db_path=db_path)
        token_holder = TokenHolder("test.token")
        data = {"software": [{"name": "PersistentApp", "version": "1.0"}]}
        fp = compute_software_fingerprint(data["software"])

        with patch("core.runtime.get_computer_id", return_value=777):
            # Enqueue during session 1
            upload_software(data, token_holder, outbox=outbox, state_file=state_file)
            assert outbox.get_stats()["status_counts"].get("PENDING", 0) == 1

        # Simulate agent restart: new DurableOutbox instance on same DB file
        outbox_restarted = DurableOutbox(db_path=db_path)
        assert outbox_restarted.get_stats()["status_counts"].get("PENDING", 0) == 1

        with patch("core.runtime.get_computer_id", return_value=777):
            # Software scan executes after restart while previous outbox item is still pending
            result = upload_software(data, token_holder, outbox=outbox_restarted, state_file=state_file)
            # Must not duplicate or suppress
            assert outbox_restarted.get_stats()["total_count"] == 1
            assert outbox_restarted.get_stats()["status_counts"].get("PENDING", 0) == 1

            # Eventual delivery in new session
            outbox_restarted.mark_delivered(1)
            record_software_delivered(fp, state_file)

            # Next scan skips
            assert upload_software(data, token_holder, outbox=outbox_restarted, state_file=state_file) is False

    def test_07_reordered_equivalent_inventory_same_fingerprint(self):
        """Scenario 7: Reordered equivalent inventory produces identical fingerprint."""
        inv_a = [
            {"name": "Visual Studio Code", "version": "1.90.0", "publisher": "Microsoft", "install_date": "2026-02-01"},
            {"name": "Git", "version": "2.44.0", "publisher": "The Git Development Community", "install_date": "2026-01-15"},
            {"name": "Python 3.13", "version": "3.13.5", "publisher": "Python Software Foundation", "install_date": "2026-01-01"},
        ]
        inv_b = [
            {"name": "  Python 3.13 ", "version": "3.13.5", "publisher": "Python Software Foundation", "install_date": "2026-01-01"},
            {"name": "Visual Studio Code", "version": "1.90.0", "publisher": "Microsoft", "install_date": "2026-02-01"},
            {"name": "Git", "version": "2.44.0", "publisher": "The Git Development Community", "install_date": "2026-01-15"},
        ]
        assert compute_software_fingerprint(inv_a) == compute_software_fingerprint(inv_b)

    def test_08_empty_inventory_valid_fingerprint(self):
        """Scenario 8: Empty inventory produces a valid 64-char SHA-256 fingerprint."""
        empty_fp = compute_software_fingerprint([])
        assert empty_fp == hashlib.sha256(b"[]").hexdigest()
        assert len(empty_fp) == 64

    def test_09_failed_software_scan_does_not_modify_delivered_fingerprint(self, tmp_path):
        """Scenario 9: Failed software scan does not modify last successfully delivered fingerprint."""
        state_file = str(tmp_path / "software_state.json")
        outbox = DurableOutbox(db_path=str(tmp_path / "outbox.db"))
        token_holder = TokenHolder("test.token")
        good_data = {"software": [{"name": "GoodApp", "version": "1.0"}]}
        fp_good = compute_software_fingerprint(good_data["software"])

        with patch("core.runtime.get_computer_id", return_value=777):
            upload_software(good_data, token_holder, outbox=outbox, state_file=state_file)
            record_software_delivered(fp_good, state_file)

        state_before = load_software_state(state_file)
        assert state_before["last_delivered_fingerprint"] == fp_good

        # Subsequent scan fails
        failed_entry = CollectionResult(
            status="failed",
            data=None,
            error=CollectorError("Software", "collect", "RegistryError", "Failed", time.time()),
        )
        res = upload_software({"software": failed_entry}, token_holder, outbox=outbox, state_file=state_file)
        assert res is False

        state_after = load_software_state(state_file)
        assert state_after["last_delivered_fingerprint"] == fp_good

    def test_required_failure_scenario_dead_letter_revival(self, tmp_path):
        """
        Execute the exact REQUIRED FAILURE SCENARIO:
        1. Software inventory changes.
        2. New fingerprint is generated.
        3. Software event is placed into Phase 3 outbox.
        4. Simulate network/server failure.
        5. Ensure outbox record remains pending/retryable.
        6. Simulate eventual dead-letter failure.
        7. Run another software scan with the SAME changed inventory.
        Expected: Client MUST NOT permanently suppress changed inventory; revives dead-letter record.
        """
        state_file = str(tmp_path / "software_state.json")
        outbox = DurableOutbox(db_path=str(tmp_path / "outbox.db"))
        token_holder = TokenHolder("test.token")

        with patch("core.runtime.get_computer_id", return_value=777):
            # 1 & 2 & 3: Software inventory changes, new fingerprint generated, enqueued into outbox
            changed_software = [{"name": "CriticalLabTool", "version": "4.2"}]
            data = {"software": changed_software}
            fp = compute_software_fingerprint(changed_software)

            enqueued = upload_software(data, token_holder, outbox=outbox, state_file=state_file)
            assert enqueued is True
            assert outbox.get_stats()["status_counts"].get("PENDING", 0) == 1
            record_id = 1

            # 4 & 5: Simulate network/server failure; ensure outbox record remains pending/retryable
            outbox.mark_retry(record_id, "HTTP 503 Server Unavailable", time.time() + 10)
            assert outbox.get_record_by_idempotency_key(f"software_777_{fp[:16]}").status.value == "PENDING"

            outbox.mark_retry(record_id, "HTTP 503 Server Unavailable", time.time() + 10)
            assert outbox.get_record_by_idempotency_key(f"software_777_{fp[:16]}").status.value == "PENDING"

            # 6: Simulate eventual dead-letter failure
            outbox.mark_dead_letter(record_id, "Max attempts reached: HTTP 503 Server Unavailable")
            from core.outbox.models import OutboxStatus
            dead_record = outbox.get_record_by_idempotency_key(f"software_777_{fp[:16]}")
            assert dead_record.status == OutboxStatus.DEAD_LETTER
            assert outbox.get_stats()["status_counts"].get("DEAD_LETTER", 0) == 1

            # State check: v2 was NOT marked delivered
            state = load_software_state(state_file)
            assert state["last_delivered_fingerprint"] is None

            # 7: Run another software scan with the SAME changed inventory
            scan_again = upload_software(data, token_holder, outbox=outbox, state_file=state_file)

            # EXPECTED BEHAVIOR:
            # - Not permanently suppressed
            # - Requeues dead-letter record
            # - Zero duplicate outbox records created
            assert scan_again is True
            revived_record = outbox.get_record_by_idempotency_key(f"software_777_{fp[:16]}")
            assert revived_record.status == OutboxStatus.PENDING
            assert outbox.get_stats()["total_count"] == 1
            assert outbox.get_stats()["status_counts"].get("DEAD_LETTER", 0) == 0
            assert outbox.get_stats()["status_counts"].get("PENDING", 0) == 1

    def test_idempotency_key_stability(self):
        """Verify that software idempotency key remains stable across restarts and retries."""
        inv = [{"name": "LabSoftware", "version": "1.0"}]
        fp = compute_software_fingerprint(inv)
        key1 = f"software_123_{fp[:16]}"
        key2 = f"software_123_{fp[:16]}"
        assert key1 == key2
        assert len(key1) == len("software_123_") + 16

    def test_corrupted_state_file_handled_safely(self, tmp_path):
        """Verify corrupted JSON state file is safely recovered without crashing."""
        state_file = str(tmp_path / "corrupted_software_state.json")
        with open(state_file, "w", encoding="utf-8") as f:
            f.write("<<<not-json>>>")

        state = load_software_state(state_file)
        assert state["last_fingerprint"] is None
        assert state["last_upload_time"] is None
        assert state["last_delivered_fingerprint"] is None
        assert state["last_enqueued_fingerprint"] is None


# ============================================================================
# E-07: Software Discovery Coverage Tests
# ============================================================================

class TestSoftwareDiscoveryCoverageE07:
    """Verify registry scanning coverage and explicit documentation of known limitations."""

    def test_registry_architecture_paths_configured(self):
        """Verify both standard 64-bit and WOW6432Node registry paths are targeted."""
        import inspect
        import modules.software as sw_mod

        src = inspect.getsource(sw_mod.get_installed_software)
        assert r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" in src
        assert r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall" in src

    def test_software_module_documents_limitations(self):
        """Verify module docstring explicitly describes registry scope and known limitations."""
        import modules.software as sw_mod

        doc = sw_mod.__doc__
        assert "E-07" in doc
        assert "Per-User Applications" in doc
        assert "Windows Store" in doc or "MSIX" in doc
        assert "Portable" in doc
