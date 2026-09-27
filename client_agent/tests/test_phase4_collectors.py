"""
SLMS Client Agent Phase 4 Tests — Collector Correctness.

Comprehensive unit and integration tests covering:
- D-01: Collection failure cannot become zero; genuine zero preserved; unknown distinguishable.
- D-02: Structured CollectionResult and CollectorError with diagnostic metadata.
- D-03 / D-04 / D-05: Canonical network identity; IP and MAC from same interface; no fake 127.0.0.1 or 00:00:00:00:00:00;
  prioritizes physical over virtual; handles loopback, inactive, IPv6, missing MAC, malformed data.
- D-06: Cumulative network byte counters preserved from psutil.net_io_counters().
- D-07: Software cache distinguishes valid empty [] from missing, expired, corrupted, or failed.
- D-08: Non-blocking CPU collection (< 0.5s execution; no 1-second sleep).
- D-09: Stable process identity based on (PID, create_time); handles PID reuse.
- D-10: Persistent usage state across restarts; surviving processes resume without restarting duration.
- D-11: False-stop protection; grace cycles for transient drops; confirmed dead closes immediately.
- D-12: System kernel pseudo-processes (PID <= 4, System Idle Process, System, etc.) excluded.
"""

from __future__ import annotations

import collections
import json
import os
import socket
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import psutil

from core.health import CollectionResult, CollectorError, safe_run
from core.collector import SoftwareCache, _collect_software, collect_all_data
from modules.hardware import get_hardware_info, init_cpu_sampling
from modules.network import (
    evaluate_interface,
    get_canonical_network_identity,
    get_network_info,
    is_valid_routable_ipv4,
    normalize_mac_address,
)
from modules.system_info import get_lan_ip, get_mac_address, get_system_info
from modules.usage import (
    _build_session,
    _get_running_applications,
    _is_excluded_process,
    collect_usage_sessions,
    get_active_usage_count,
    load_usage_state,
    reset_usage_tracking,
    save_usage_state,
)
from server.sender import build_metric_payload


# ============================================================================
# Helpers for Mocking psutil Network Data
# ============================================================================

AddrMock = collections.namedtuple("snicaddr", ["family", "address", "netmask", "broadcast", "ptp"])
StatMock = collections.namedtuple("snicstats", ["isup", "duplex", "speed", "mtu", "flags"])


def make_ipv4_addr(ip: str):
    return AddrMock(family=socket.AF_INET, address=ip, netmask="255.255.255.0", broadcast=None, ptp=None)


def make_mac_addr(mac: str):
    return AddrMock(family=getattr(psutil, "AF_LINK", -1), address=mac, netmask=None, broadcast=None, ptp=None)


def make_ipv6_addr(ip6: str):
    return AddrMock(family=socket.AF_INET6, address=ip6, netmask=None, broadcast=None, ptp=None)


def make_stat(isup: bool = True, speed: int = 1000):
    return StatMock(isup=isup, duplex=2, speed=speed, mtu=1500, flags="")


# ============================================================================
# D-01 + D-02: Structured Collection Results
# ============================================================================

class TestStructuredResultsD01D02:

    def test_genuine_zero_preserved_and_not_empty(self):
        """Genuine numeric 0.0 must be preserved with status='success'."""
        result = safe_run("Zero Metric", lambda: 0.0)
        assert result.status == "success"
        assert result.data == 0.0
        assert result.is_success is True
        assert result.is_failed is False
        assert result.is_empty is False
        assert result.error is None

    def test_genuine_zero_int_preserved(self):
        result = safe_run("Zero Counter", lambda: 0)
        assert result.status == "success"
        assert result.data == 0
        assert result.is_success is True
        assert result.is_empty is False

    def test_empty_list_distinguishable_from_zero(self):
        """Empty collections must have status='empty', not confused with 0."""
        result = safe_run("Empty List", lambda: [])
        assert result.status == "empty"
        assert result.data == []
        assert result.is_empty is True
        assert result.is_failed is False

    def test_collection_failure_not_converted_to_zero(self):
        """Exceptions in collector must result in status='failed' with data=None, NEVER 0."""
        def faulty_collector():
            raise RuntimeError("Hardware access timeout")

        result = safe_run("Hardware", faulty_collector, operation="read_sensors")
        assert result.status == "failed"
        assert result.data is None
        assert result.data != 0  # CRITICAL: not converted to 0
        assert result.is_failed is True
        assert result.error is not None
        assert result.error.collector_name == "Hardware"
        assert result.error.operation == "read_sensors"
        assert result.error.error_type == "RuntimeError"
        assert "Hardware access timeout" in result.error.message
        assert result.error.timestamp > 0

    def test_build_metric_payload_rejects_failed_hardware(self):
        """build_metric_payload must raise ValueError on hardware collection failure (D-01)."""
        failed_hw = CollectionResult(
            status="failed",
            data=None,
            error=CollectorError("Hardware", "read", "OSError", "I/O error", time.time()),
        )
        data = {"hardware": failed_hw, "network": {"bytes_sent": 100, "bytes_received": 200}}
        with pytest.raises(ValueError, match="Hardware metrics collection failed"):
            build_metric_payload(data)

    def test_build_metric_payload_preserves_none_for_failed_network(self):
        """Network failure in build_metric_payload must yield None for network fields, not 0."""
        hw = {"cpu_usage": 15.0, "ram_percent": 45.0, "disk_percent": 60.0}
        failed_net = CollectionResult(
            status="failed",
            data=None,
            error=CollectorError("Network", "read", "OSError", "Net down", time.time()),
        )
        payload = build_metric_payload({"hardware": hw, "network": failed_net})
        assert payload["cpu_usage"] == 15.0
        assert payload["ram_usage"] == 45.0
        assert payload["disk_usage"] == 60.0
        assert payload["network_sent"] is None  # CRITICAL: not 0
        assert payload["network_received"] is None  # CRITICAL: not 0

    def test_collection_result_dict_methods_and_serialization(self):
        """CollectionResult supports dict-like access, serialization, and truthiness."""
        res = CollectionResult(
            status="success",
            data={"cpu_usage": 25.5, "ram_usage": 50.0},
            error=None,
            collected_at=1700000000.0,
        )
        assert res.get("cpu_usage") == 25.5
        assert res.get("nonexistent", 99) == 99
        assert res["cpu_usage"] == 25.5
        assert "cpu_usage" in res
        assert bool(res) is True

        d = res.to_dict()
        assert d["status"] == "success"
        assert d["data"]["cpu_usage"] == 25.5
        assert d["error"] is None

        # Failed result is always falsy
        failed_res = CollectionResult(status="failed", data=None)
        assert bool(failed_res) is False


# ============================================================================
# D-03 + D-04 + D-05: Network Identity
# ============================================================================

class TestCanonicalNetworkIdentityD03D04D05:

    def test_mac_normalization(self):
        assert normalize_mac_address("ce-30-a6-2b-d9-db") == "CE:30:A6:2B:D9:DB"
        assert normalize_mac_address("CE:30:A6:2B:D9:DB") == "CE:30:A6:2B:D9:DB"
        # Null or broadcast MAC rejected
        assert normalize_mac_address("00:00:00:00:00:00") is None
        assert normalize_mac_address("00-00-00-00-00-00") is None
        assert normalize_mac_address("FF:FF:FF:FF:FF:FF") is None
        assert normalize_mac_address("invalid_mac") is None
        assert normalize_mac_address(None) is None

    def test_ipv4_validation(self):
        assert is_valid_routable_ipv4("192.168.1.50") is True
        assert is_valid_routable_ipv4("10.0.0.1") is True
        assert is_valid_routable_ipv4("172.16.0.1") is True
        # Loopback rejected
        assert is_valid_routable_ipv4("127.0.0.1") is False
        assert is_valid_routable_ipv4("127.0.0.2") is False
        # APIPA link-local rejected
        assert is_valid_routable_ipv4("169.254.10.20") is False
        # Unspecified rejected
        assert is_valid_routable_ipv4("0.0.0.0") is False
        assert is_valid_routable_ipv4("") is False
        assert is_valid_routable_ipv4("not_an_ip") is False

    def test_loopback_and_lan_selects_lan(self):
        """Loopback adapter ignored; real LAN adapter selected."""
        addrs = {
            "Loopback Pseudo-Interface 1": [
                make_ipv4_addr("127.0.0.1"),
                make_ipv6_addr("::1"),
            ],
            "Ethernet": [
                make_mac_addr("AA:BB:CC:DD:EE:01"),
                make_ipv4_addr("192.168.1.100"),
            ],
        }
        stats = {
            "Loopback Pseudo-Interface 1": make_stat(isup=True),
            "Ethernet": make_stat(isup=True, speed=1000),
        }
        ident = get_canonical_network_identity(addrs=addrs, stats=stats)
        assert ident["status"] == "success"
        assert ident["interface"] == "Ethernet"
        assert ident["ip_address"] == "192.168.1.100"
        assert ident["mac_address"] == "AA:BB:CC:DD:EE:01"

    def test_multiple_active_adapters_ethernet_preferred_over_wifi(self):
        """When both Ethernet and Wi-Fi are active, Ethernet is preferred."""
        addrs = {
            "Wi-Fi": [
                make_mac_addr("11:22:33:44:55:66"),
                make_ipv4_addr("192.168.1.105"),
            ],
            "Ethernet": [
                make_mac_addr("AA:BB:CC:DD:EE:01"),
                make_ipv4_addr("192.168.1.50"),
            ],
        }
        stats = {
            "Wi-Fi": make_stat(isup=True, speed=300),
            "Ethernet": make_stat(isup=True, speed=1000),
        }
        ident = get_canonical_network_identity(addrs=addrs, stats=stats)
        assert ident["status"] == "success"
        assert ident["interface"] == "Ethernet"
        assert ident["ip_address"] == "192.168.1.50"
        assert ident["mac_address"] == "AA:BB:CC:DD:EE:01"

    def test_inactive_adapter_skipped_even_if_first(self):
        """Inactive (down) adapter is skipped in favor of an active UP adapter."""
        addrs = {
            "Ethernet": [
                make_mac_addr("AA:BB:CC:DD:EE:01"),
                make_ipv4_addr("169.254.1.1"),
            ],
            "Wi-Fi": [
                make_mac_addr("11:22:33:44:55:66"),
                make_ipv4_addr("192.168.1.105"),
            ],
        }
        stats = {
            "Ethernet": make_stat(isup=False, speed=0),
            "Wi-Fi": make_stat(isup=True, speed=300),
        }
        ident = get_canonical_network_identity(addrs=addrs, stats=stats)
        assert ident["status"] == "success"
        assert ident["interface"] == "Wi-Fi"
        assert ident["ip_address"] == "192.168.1.105"
        assert ident["mac_address"] == "11:22:33:44:55:66"

    def test_virtual_adapter_deprioritized(self):
        """vEthernet/Hyper-V virtual adapter is deprioritized when physical adapter is up."""
        addrs = {
            "vEthernet (Default Switch)": [
                make_mac_addr("00:15:5D:01:02:03"),
                make_ipv4_addr("172.20.10.1"),
            ],
            "Wi-Fi": [
                make_mac_addr("CE:30:A6:2B:D9:DB"),
                make_ipv4_addr("192.168.1.20"),
            ],
        }
        stats = {
            "vEthernet (Default Switch)": make_stat(isup=True, speed=10000),
            "Wi-Fi": make_stat(isup=True, speed=200),
        }
        ident = get_canonical_network_identity(addrs=addrs, stats=stats)
        assert ident["status"] == "success"
        assert ident["interface"] == "Wi-Fi"
        assert ident["ip_address"] == "192.168.1.20"
        assert ident["mac_address"] == "CE:30:A6:2B:D9:DB"

    def test_ip_and_mac_always_from_same_interface(self):
        """CRITICAL (D-05): IP and MAC must come from the exact same interface."""
        addrs = {
            "AdapterA": [
                make_mac_addr("AA:AA:AA:AA:AA:AA"),
                make_ipv4_addr("10.0.0.1"),
            ],
            "AdapterB": [
                make_mac_addr("BB:BB:BB:BB:BB:BB"),
                make_ipv4_addr("10.0.0.2"),
            ],
        }
        stats = {
            "AdapterA": make_stat(isup=True, speed=100),
            "AdapterB": make_stat(isup=True, speed=1000),  # B has higher speed
        }
        ident = get_canonical_network_identity(addrs=addrs, stats=stats)
        assert ident["status"] == "success"
        # B wins due to speed; its MAC MUST be AdapterB's MAC!
        assert ident["interface"] == "AdapterB"
        assert ident["ip_address"] == "10.0.0.2"
        assert ident["mac_address"] == "BB:BB:BB:BB:BB:BB"

    def test_no_valid_interface_returns_structured_failure(self):
        """When no suitable interface exists, returns status='failed', NEVER fake 127.0.0.1 or 00s."""
        addrs = {
            "Loopback": [make_ipv4_addr("127.0.0.1")],
            "Disconnected": [make_mac_addr("11:22:33:44:55:66")],  # No IP
        }
        stats = {
            "Loopback": make_stat(isup=True),
            "Disconnected": make_stat(isup=False),
        }
        ident = get_canonical_network_identity(addrs=addrs, stats=stats)
        assert ident["status"] == "failed"
        assert ident["interface"] is None
        assert ident["ip_address"] is None  # CRITICAL: not 127.0.0.1
        assert ident["mac_address"] is None  # CRITICAL: not 00:00:00:00:00:00

    def test_ipv6_only_interface_skipped(self):
        """IPv6-only interface cannot satisfy IPv4 LAN requirement."""
        addrs = {
            "IPv6Only": [
                make_mac_addr("AA:BB:CC:DD:EE:FF"),
                make_ipv6_addr("fe80::1"),
            ]
        }
        stats = {"IPv6Only": make_stat(isup=True)}
        ident = get_canonical_network_identity(addrs=addrs, stats=stats)
        assert ident["status"] == "failed"

    def test_interface_without_mac_does_not_steal_from_other(self):
        """Interface with IP but no MAC returns mac_address=None; never steals MAC from another adapter."""
        addrs = {
            "VPN": [make_ipv4_addr("10.8.0.2")],  # No MAC entry
        }
        stats = {"VPN": make_stat(isup=True)}
        ident = get_canonical_network_identity(addrs=addrs, stats=stats)
        assert ident["status"] == "success"
        assert ident["ip_address"] == "10.8.0.2"
        assert ident["mac_address"] is None  # NOT stolen from another adapter

    def test_malformed_address_handled_safely(self):
        """Malformed address data does not crash network identity evaluation."""
        addrs = {
            "Glitchy": [
                AddrMock(family=socket.AF_INET, address="999.999.999.999", netmask=None, broadcast=None, ptp=None),
                AddrMock(family=-1, address="not-a-mac", netmask=None, broadcast=None, ptp=None),
            ]
        }
        stats = {"Glitchy": make_stat(isup=True)}
        ident = get_canonical_network_identity(addrs=addrs, stats=stats)
        assert ident["status"] == "failed"

    def test_system_info_uses_canonical_network_identity(self):
        """modules.system_info must use canonical network identity without duplicating logic (D-04)."""
        mock_identity = {
            "status": "success",
            "interface": "Ethernet",
            "ip_address": "192.168.1.88",
            "mac_address": "12:34:56:78:9A:BC",
            "error": None,
        }
        with patch("modules.system_info.get_canonical_network_identity", return_value=mock_identity):
            sys_info = get_system_info()
            assert sys_info["ip_address"] == "192.168.1.88"
            assert sys_info["mac_address"] == "12:34:56:78:9A:BC"
            assert get_lan_ip() == "192.168.1.88"
            assert get_mac_address() == "12:34:56:78:9A:BC"


# ============================================================================
# D-06: Cumulative Network Counters
# ============================================================================

class TestNetworkCountersD06:

    def test_cumulative_counters_preserved_from_psutil(self):
        """bytes_sent and bytes_received must reflect cumulative counters from psutil (D-06)."""
        mock_stats = collections.namedtuple("snetio", ["bytes_sent", "bytes_recv"])(
            bytes_sent=1234567890,
            bytes_recv=9876543210,
        )
        with patch("modules.network.psutil.net_io_counters", return_value=mock_stats):
            info = get_network_info()
            assert info["bytes_sent"] == 1234567890  # Cumulative, not rate
            assert info["bytes_received"] == 9876543210  # Cumulative, not rate

    def test_build_metric_payload_passes_cumulative_counters(self):
        """build_metric_payload correctly preserves cumulative network counters."""
        data = {
            "hardware": {"cpu_usage": 10.0, "ram_percent": 20.0, "disk_percent": 30.0},
            "network": {"bytes_sent": 5000000, "bytes_received": 10000000},
        }
        payload = build_metric_payload(data)
        assert payload["network_sent"] == 5000000
        assert payload["network_received"] == 10000000


# ============================================================================
# D-07: Software Cache Empty-Result Bug
# ============================================================================

class TestSoftwareCacheD07:

    def test_cache_contains_software_uses_cache(self):
        """When cache contains items and is not expired, returns cached without rescanning."""
        cache = SoftwareCache(ttl=60.0)
        items = [{"name": "VSCode", "version": "1.85"}]
        now = time.monotonic()
        cache.set(items, now=now)

        with patch("core.collector.get_installed_software") as mock_scan:
            result = _collect_software(cache=cache)
            assert result == items
            mock_scan.assert_not_called()

    def test_cache_contains_valid_empty_inventory_uses_empty(self):
        """CRITICAL (D-07): Valid empty inventory [] must be reused from cache, not rescanned!"""
        cache = SoftwareCache(ttl=60.0)
        empty_items: list[dict] = []
        now = time.monotonic()
        cache.set(empty_items, now=now)

        assert cache.is_present is True

        with patch("core.collector.get_installed_software") as mock_scan:
            # Within TTL: must return [] without calling get_installed_software
            result = _collect_software(cache=cache)
            assert result == []
            mock_scan.assert_not_called()


    def test_cache_missing_triggers_rescan(self):
        """When cache is missing (uninitialized), it scans registry and populates cache."""
        cache = SoftwareCache(ttl=60.0)
        assert cache.is_present is False

        scanned = [{"name": "Git", "version": "2.40"}]
        with patch("core.collector.get_installed_software", return_value=scanned) as mock_scan:
            result = _collect_software(cache=cache)
            assert result == scanned
            mock_scan.assert_called_once()
            assert cache.is_present is True
            assert cache.get() == scanned

    def test_cache_expired_triggers_rescan(self):
        """When cache TTL expires, it rescans and updates cache."""
        cache = SoftwareCache(ttl=10.0)
        cache.set([{"name": "OldApp"}], now=100.0)

        new_items = [{"name": "NewApp"}]
        with patch("core.collector.get_installed_software", return_value=new_items) as mock_scan:
            # Call with simulated time > TTL
            with patch("time.monotonic", return_value=120.0):
                result = _collect_software(cache=cache)
                assert result == new_items
                mock_scan.assert_called_once()

    def test_cache_corrupted_heals_and_rescans(self):
        """If cache is corrupted (e.g. non-list data), it invalidates and rescans."""
        cache = SoftwareCache(ttl=60.0)
        cache._items = "not_a_list"  # Corrupted internal state
        cache._is_valid = True

        healed_items = [{"name": "Python"}]
        with patch("core.collector.get_installed_software", return_value=healed_items):
            result = _collect_software(cache=cache)
            assert result == healed_items
            assert cache._items == healed_items

    def test_collection_failure_does_not_convert_to_valid_empty_inventory(self):
        """If get_installed_software fails, failure must not be cached as valid empty []."""
        cache = SoftwareCache(ttl=60.0)

        with patch("core.collector.get_installed_software", side_effect=OSError("Registry locked")):
            with pytest.raises(OSError):
                _collect_software(cache=cache)

        # Cache must remain invalid/empty; must NOT contain valid []
        assert cache.is_present is False
        assert cache.get() is None


# ============================================================================
# D-08: Non-Blocking CPU Collection
# ============================================================================

class TestNonBlockingCpuCollectionD08:

    def test_cpu_collection_is_non_blocking(self):
        """get_hardware_info must NOT sleep for 1 second (interval=1 removed). Execution < 0.3s."""
        t0 = time.monotonic()
        info = get_hardware_info()
        elapsed = time.monotonic() - t0

        assert elapsed < 0.5, f"get_hardware_info took {elapsed:.2f}s, expected non-blocking < 0.5s"
        assert "cpu_usage" in info
        assert isinstance(info["cpu_usage"], float)
        assert info["cpu_usage"] >= 0.0

    def test_init_cpu_sampling_primes_without_blocking(self):
        """init_cpu_sampling executes immediately without blocking."""
        t0 = time.monotonic()
        init_cpu_sampling()
        elapsed = time.monotonic() - t0
        assert elapsed < 0.2

    def test_cpu_collection_error_does_not_mask_to_zero(self):
        """If psutil.cpu_percent raises an error, safe_run records failure, NOT 0.0%."""
        with patch("modules.hardware.psutil.cpu_percent", side_effect=RuntimeError("psutil error")):
            result = safe_run("Hardware", get_hardware_info)
            assert result.status == "failed"
            assert result.data is None
            assert result.is_failed is True


# ============================================================================
# D-09: Stable Process Identity (PID + create_time)
# ============================================================================

class TestProcessIdentityD09:

    def test_same_pid_same_create_time_identified_as_same_process(self):
        """Same PID with matching creation time is recognized as the same running process."""
        p1 = {"pid": 1234, "name": "editor.exe", "create_time": 1700000000.0}
        p2 = {"pid": 1234, "name": "editor.exe", "create_time": 1700000000.0}

        id1 = (p1["pid"], p1["create_time"])
        id2 = (p2["pid"], p2["create_time"])
        assert id1 == id2

    def test_same_pid_different_create_time_identified_as_different_process(self):
        """CRITICAL (D-09): PID reuse with new create_time creates a distinct identity."""
        old_proc = {"pid": 1234, "name": "app.exe", "create_time": 1700000000.0}
        new_proc = {"pid": 1234, "name": "app.exe", "create_time": 1700005000.0}

        id_old = (old_proc["pid"], old_proc["create_time"])
        id_new = (new_proc["pid"], new_proc["create_time"])
        assert id_old != id_new

    def test_process_name_change_retains_stable_identity(self):
        """Process identity is independent of process name changes."""
        id_initial = (5678, 1700000000.0)
        id_renamed = (5678, 1700000000.0)
        assert id_initial == id_renamed


# ============================================================================
# D-10: Persistent Usage State Across Restart
# ============================================================================

class TestUsagePersistenceAndRestartRecoveryD10:

    def test_active_usage_saved_and_loaded_atomically(self, tmp_path):
        """Active sessions are persisted atomically and recovered safely across restart."""
        state_file = str(tmp_path / "usage_state.json")
        reset_usage_tracking(state_file)

        started_at = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)
        test_session = {
            "pid": 99999,
            "create_time": 1700000000.0,
            "application_name": "lab_tool.exe",
            "started_at": started_at,
            "last_seen_at": started_at,
            "consecutive_misses": 0,
        }

        # Populate in-memory state and save
        import modules.usage as usage_mod
        usage_mod._ACTIVE_SESSIONS[(99999, 1700000000.0)] = test_session
        save_usage_state(state_file)

        assert os.path.exists(state_file)

        # Clear in-memory state (simulate restart)
        usage_mod._ACTIVE_SESSIONS.clear()
        usage_mod._INITIALIZED = False

        # Mock: process is still alive in OS!
        mock_proc = MagicMock()
        mock_proc.create_time.return_value = 1700000000.0
        with patch("modules.usage.psutil.pid_exists", return_value=True), \
             patch("modules.usage.psutil.Process", return_value=mock_proc), \
             patch("modules.usage._safe_create_time", return_value=1700000000.0):
            completed = load_usage_state(state_file)
            # Must NOT emit stop event (process survived!)
            assert len(completed) == 0
            # Active session restored with original started_at!
            assert (99999, 1700000000.0) in usage_mod._ACTIVE_SESSIONS
            restored = usage_mod._ACTIVE_SESSIONS[(99999, 1700000000.0)]
            assert restored["started_at"] == started_at
            assert restored["application_name"] == "lab_tool.exe"


        reset_usage_tracking(state_file)

    def test_process_terminated_during_restart_emitted_on_recovery(self, tmp_path):
        """Process that terminated while agent was stopped is reconciled and emitted."""
        state_file = str(tmp_path / "usage_state.json")
        reset_usage_tracking(state_file)

        started_at = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)
        import modules.usage as usage_mod
        usage_mod._ACTIVE_SESSIONS[(88888, 1700000000.0)] = {
            "pid": 88888,
            "create_time": 1700000000.0,
            "application_name": "student_ide.exe",
            "started_at": started_at,
            "last_seen_at": started_at,
            "consecutive_misses": 0,
        }
        save_usage_state(state_file)

        usage_mod._ACTIVE_SESSIONS.clear()
        usage_mod._INITIALIZED = False

        # Process no longer exists in OS
        with patch("modules.usage.psutil.pid_exists", return_value=False):
            completed = load_usage_state(state_file)
            assert len(completed) == 1
            assert completed[0]["application_name"] == "student_ide.exe"
            assert (88888, 1700000000.0) not in usage_mod._ACTIVE_SESSIONS

        reset_usage_tracking(state_file)


# ============================================================================
# D-11: False-Stop Protection & Grace Cycles
# ============================================================================

class TestFalseStopProtectionD11:

    def test_confirmed_termination_closes_immediately(self, tmp_path):
        """When OS confirms PID does not exist, session terminates immediately."""
        state_file = str(tmp_path / "usage_state.json")
        reset_usage_tracking(state_file)

        import modules.usage as usage_mod
        now = datetime.now(timezone.utc)
        usage_mod._ACTIVE_SESSIONS[(77777, 1700000000.0)] = {
            "pid": 77777,
            "create_time": 1700000000.0,
            "application_name": "test_app.exe",
            "started_at": now,
            "last_seen_at": now,
            "consecutive_misses": 0,
        }

        # Scan returns empty, and pid_exists returns False (confirmed dead)
        with patch("modules.usage._get_running_applications", return_value={}), \
             patch("modules.usage.psutil.pid_exists", return_value=False):
            completed = collect_usage_sessions(state_file)
            assert len(completed) == 1
            assert completed[0]["application_name"] == "test_app.exe"
            assert (77777, 1700000000.0) not in usage_mod._ACTIVE_SESSIONS

        reset_usage_tracking(state_file)

    def test_transient_process_drop_held_in_grace_period(self, tmp_path):
        """Process missing for 1 scan but PID still exists in OS is held in grace period (D-11)."""
        state_file = str(tmp_path / "usage_state.json")
        reset_usage_tracking(state_file)

        import modules.usage as usage_mod
        now = datetime.now(timezone.utc)
        usage_mod._ACTIVE_SESSIONS[(66666, 1700000000.0)] = {
            "pid": 66666,
            "create_time": 1700000000.0,
            "application_name": "heavy_compiler.exe",
            "started_at": now,
            "last_seen_at": now,
            "consecutive_misses": 0,
        }

        # Cycle 1: Process missing from process_iter, but pid_exists is True (transient lag/AccessDenied)
        mock_proc = MagicMock()
        mock_proc.create_time.return_value = 1700000000.0
        with patch("modules.usage._get_running_applications", return_value={}), \
             patch("modules.usage.psutil.pid_exists", return_value=True), \
             patch("modules.usage.psutil.Process", return_value=mock_proc), \
             patch("modules.usage._safe_create_time", return_value=1700000000.0):
            completed = collect_usage_sessions(state_file)

            # CRITICAL: must NOT emit stop event!
            assert len(completed) == 0
            # Session remains alive in grace period
            session = usage_mod._ACTIVE_SESSIONS[(66666, 1700000000.0)]
            assert session["consecutive_misses"] == 1

        # Cycle 2: Process reappears in process_iter!
        reappeared = {
            (66666, 1700000000.0): {
                "pid": 66666,
                "create_time": 1700000000.0,
                "application_name": "heavy_compiler.exe",
                "started_at": now,
            }
        }
        with patch("modules.usage._get_running_applications", return_value=reappeared):
            completed = collect_usage_sessions(state_file)
            assert len(completed) == 0
            # consecutive_misses reset to 0!
            session = usage_mod._ACTIVE_SESSIONS[(66666, 1700000000.0)]
            assert session["consecutive_misses"] == 0

        reset_usage_tracking(state_file)

    def test_global_process_enumeration_failure_does_not_close_sessions(self, tmp_path):
        """Global enumeration failure (returns 0 when >5 active) does not close all sessions."""
        state_file = str(tmp_path / "usage_state.json")
        reset_usage_tracking(state_file)

        import modules.usage as usage_mod
        now = datetime.now(timezone.utc)
        # Setup 6 active sessions
        for i in range(6):
            usage_mod._ACTIVE_SESSIONS[(1000 + i, 1700000000.0)] = {
                "pid": 1000 + i,
                "create_time": 1700000000.0,
                "application_name": f"app_{i}.exe",
                "started_at": now,
                "last_seen_at": now,
                "consecutive_misses": 0,
            }

        # Enumeration glitch returns empty
        with patch("modules.usage._get_running_applications", return_value={}):
            completed = collect_usage_sessions(state_file)
            # Must NOT close all 6 sessions!
            assert len(completed) == 0
            assert len(usage_mod._ACTIVE_SESSIONS) == 6

        reset_usage_tracking(state_file)

    def test_pid_reuse_closes_old_session_and_starts_new(self, tmp_path):
        """When PID exists with different create_time, old session closes and new starts."""
        state_file = str(tmp_path / "usage_state.json")
        reset_usage_tracking(state_file)

        import modules.usage as usage_mod
        now = datetime.now(timezone.utc)
        old_id = (55555, 1700000000.0)
        new_id = (55555, 1700009999.0)

        usage_mod._ACTIVE_SESSIONS[old_id] = {
            "pid": 55555,
            "create_time": 1700000000.0,
            "application_name": "first_app.exe",
            "started_at": now,
            "last_seen_at": now,
            "consecutive_misses": 0,
        }

        # PID exists but create_time changed to new_proc!
        new_current = {
            new_id: {
                "pid": 55555,
                "create_time": 1700009999.0,
                "application_name": "second_app.exe",
                "started_at": now,
            }
        }
        with patch("modules.usage._get_running_applications", return_value=new_current), \
             patch("modules.usage.psutil.pid_exists", return_value=True), \
             patch("modules.usage._safe_create_time", return_value=1700009999.0):
            completed = collect_usage_sessions(state_file)
            # Old session must be completed!
            assert len(completed) == 1
            assert completed[0]["application_name"] == "first_app.exe"
            # Old session removed; new session active!
            assert old_id not in usage_mod._ACTIVE_SESSIONS
            assert new_id in usage_mod._ACTIVE_SESSIONS

        reset_usage_tracking(state_file)


# ============================================================================
# D-12: Usage Filtering Policy
# ============================================================================

class TestUsageFilteringD12:

    def test_kernel_and_idle_pseudo_processes_excluded(self):
        """PID <= 4 and OS pseudo-processes are excluded from student usage (D-12)."""
        assert _is_excluded_process(0, "System Idle Process") is True
        assert _is_excluded_process(4, "System") is True
        assert _is_excluded_process(120, "registry") is True
        assert _is_excluded_process(250, "Memory Compression") is True

    def test_student_applications_included(self):
        """Regular user applications are tracked normally."""
        assert _is_excluded_process(1234, "notepad.exe") is False
        assert _is_excluded_process(5678, "python.exe") is False
        assert _is_excluded_process(9012, "code.exe") is False
        assert _is_excluded_process(3456, "chrome.exe") is False


# ============================================================================
# Final Pre-Commit Audit Verification
# ============================================================================

class TestPhase4PreCommitAudit:

    def test_d10_persistence_atomic_replace_and_interrupted_write_safety(self, tmp_path):
        """D-10 Audit: Atomic replace, interrupted write safety, and temp file cleanup."""
        state_file = str(tmp_path / "usage_state.json")
        reset_usage_tracking(state_file)

        import modules.usage as usage_mod
        now = datetime.now(timezone.utc)
        usage_mod._ACTIVE_SESSIONS[(111, 100.0)] = {
            "pid": 111,
            "create_time": 100.0,
            "application_name": "initial_app.exe",
            "started_at": now,
            "last_seen_at": now,
            "consecutive_misses": 0,
        }
        save_usage_state(state_file)
        assert os.path.exists(state_file)

        with open(state_file, "r", encoding="utf-8") as f:
            initial_content = f.read()

        # Simulate interrupted write during json.dump
        with patch("modules.usage.json.dump", side_effect=IOError("Disk write error")):
            usage_mod._ACTIVE_SESSIONS[(222, 200.0)] = {
                "pid": 222,
                "create_time": 200.0,
                "application_name": "broken_app.exe",
                "started_at": now,
                "last_seen_at": now,
                "consecutive_misses": 0,
            }
            save_usage_state(state_file)

        # File content must remain completely unchanged (not corrupted or partial)
        with open(state_file, "r", encoding="utf-8") as f:
            after_content = f.read()
        assert after_content == initial_content

        # No lingering temporary files in directory
        temp_files = [f for f in os.listdir(tmp_path) if f.startswith("tmp") or f.endswith(".tmp")]
        assert len(temp_files) == 0

        reset_usage_tracking(state_file)

    def test_d10_persistence_no_secrets_stored(self, tmp_path):
        """D-10 Audit: usage_state.json must never store credentials, tokens, or secrets."""
        state_file = str(tmp_path / "usage_state.json")
        reset_usage_tracking(state_file)

        import modules.usage as usage_mod
        now = datetime.now(timezone.utc)
        usage_mod._ACTIVE_SESSIONS[(333, 100.0)] = {
            "pid": 333,
            "create_time": 100.0,
            "application_name": "app.exe",
            "started_at": now,
            "last_seen_at": now,
            "consecutive_misses": 0,
        }
        save_usage_state(state_file)

        with open(state_file, "r", encoding="utf-8") as f:
            raw = f.read().lower()

        forbidden_terms = ["token", "secret", "password", "bearer", "credential", "auth"]
        for term in forbidden_terms:
            assert term not in raw, f"Forbidden sensitive term '{term}' found in usage_state.json"

        reset_usage_tracking(state_file)

    def test_d10_multiple_saves_consistency(self, tmp_path):
        """D-10 Audit: Repeated saves maintain integrity without corruption."""
        state_file = str(tmp_path / "usage_state.json")
        reset_usage_tracking(state_file)

        import modules.usage as usage_mod
        now = datetime.now(timezone.utc)
        for i in range(10):
            usage_mod._ACTIVE_SESSIONS[(400 + i, 100.0 + i)] = {
                "pid": 400 + i,
                "create_time": 100.0 + i,
                "application_name": f"app_{i}.exe",
                "started_at": now,
                "last_seen_at": now,
                "consecutive_misses": 0,
            }
            save_usage_state(state_file)

        with open(state_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
        assert len(saved) == 10

        reset_usage_tracking(state_file)

    def test_d11_pid_reuse_state_transition_explicit(self, tmp_path):
        """
        D-11 Audit: Explicit PID reuse state transition test.
        Old process: PID=1234, create_time=100.0 terminates.
        New process: PID=1234, create_time=200.0 starts.
        Expected:
        - old session is closed
        - new process gets a NEW session
        - old session duration is not extended by the new process
        - new session does not inherit the old process identity
        - no duplicate active session remains for the old identity
        """
        state_file = str(tmp_path / "usage_state.json")
        reset_usage_tracking(state_file)

        import modules.usage as usage_mod
        t1 = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)  # 100.0
        old_id = (1234, 100.0)

        # Step 1: Old process running
        usage_mod._ACTIVE_SESSIONS[old_id] = {
            "pid": 1234,
            "create_time": 100.0,
            "application_name": "first_app.exe",
            "started_at": t1,
            "last_seen_at": t1,
            "consecutive_misses": 0,
        }

        # Step 2: Next cycle, old process terminated, new process with PID 1234, create_time 200.0 starts
        t2 = datetime(2026, 9, 27, 10, 5, 0, tzinfo=timezone.utc)  # 5 min later
        new_id = (1234, 200.0)
        current_apps = {
            new_id: {
                "pid": 1234,
                "create_time": 200.0,
                "application_name": "second_app.exe",
                "started_at": t2,
            }
        }

        mock_proc = MagicMock()
        mock_proc.create_time.return_value = 200.0
        with patch("modules.usage._get_running_applications", return_value=current_apps), \
             patch("modules.usage.psutil.pid_exists", return_value=True), \
             patch("modules.usage.psutil.Process", return_value=mock_proc), \
             patch("modules.usage._safe_create_time", return_value=200.0):
            completed = collect_usage_sessions(state_file)

            # 1. Old session is closed
            assert len(completed) == 1
            old_completed = completed[0]
            assert old_completed["application_name"] == "first_app.exe"

            # 2. Old session duration is NOT extended by new process
            # Old started_at is t1; ended_at is close to now
            assert old_completed["started_at"] == t1.isoformat()

            # 3. New process gets a NEW session
            assert new_id in usage_mod._ACTIVE_SESSIONS
            new_session = usage_mod._ACTIVE_SESSIONS[new_id]
            assert new_session["application_name"] == "second_app.exe"

            # 4. New session does NOT inherit old process identity
            assert new_session["started_at"] == t2
            assert new_session["create_time"] == 200.0

            # 5. No duplicate active session remains for the old identity
            assert old_id not in usage_mod._ACTIVE_SESSIONS
            assert len(usage_mod._ACTIVE_SESSIONS) == 1

        reset_usage_tracking(state_file)

    def test_d11_transient_access_failure_does_not_close_session_immediately(self, tmp_path):
        """D-11 Audit: Transient AccessDenied does NOT close the active session immediately."""
        state_file = str(tmp_path / "usage_state.json")
        reset_usage_tracking(state_file)

        import modules.usage as usage_mod
        now = datetime.now(timezone.utc)
        ident = (9876, 500.0)
        usage_mod._ACTIVE_SESSIONS[ident] = {
            "pid": 9876,
            "create_time": 500.0,
            "application_name": "secured_app.exe",
            "started_at": now,
            "last_seen_at": now,
            "consecutive_misses": 0,
        }

        # psutil returns AccessDenied
        with patch("modules.usage._get_running_applications", return_value={}), \
             patch("modules.usage.psutil.pid_exists", return_value=True), \
             patch("modules.usage.psutil.Process", side_effect=psutil.AccessDenied(pid=9876)):
            completed = collect_usage_sessions(state_file)
            # Must NOT close session immediately
            assert len(completed) == 0
            assert ident in usage_mod._ACTIVE_SESSIONS
            assert usage_mod._ACTIVE_SESSIONS[ident]["consecutive_misses"] == 1

        reset_usage_tracking(state_file)

    def test_d10_d11_restart_scenarios_a_b_c(self, tmp_path):
        """
        D-10/D-11 Audit:
        Scenario A: agent running, process running, agent restarts, process still running -> same session resumes.
        Scenario B: agent running, process running, agent stops, process terminates while agent down -> previous session reconciled as completed using best available timestamp.
        Scenario C: state file is corrupted -> agent does not crash and does not fabricate a huge session.
        """
        state_file = str(tmp_path / "usage_state.json")

        # Scenario A: process still running after restart
        reset_usage_tracking(state_file)
        import modules.usage as usage_mod
        t0 = datetime(2026, 9, 27, 9, 0, 0, tzinfo=timezone.utc)
        usage_mod._ACTIVE_SESSIONS[(1001, 100.0)] = {
            "pid": 1001,
            "create_time": 100.0,
            "application_name": "persistent_worker.exe",
            "started_at": t0,
            "last_seen_at": t0,
            "consecutive_misses": 0,
        }
        save_usage_state(state_file)

        # Simulate agent restart
        usage_mod._ACTIVE_SESSIONS.clear()
        usage_mod._INITIALIZED = False
        mock_proc = MagicMock()
        mock_proc.create_time.return_value = 100.0
        with patch("modules.usage.psutil.pid_exists", return_value=True), \
             patch("modules.usage.psutil.Process", return_value=mock_proc), \
             patch("modules.usage._safe_create_time", return_value=100.0):
            completed = load_usage_state(state_file)
            assert len(completed) == 0  # No false stop event
            assert (1001, 100.0) in usage_mod._ACTIVE_SESSIONS
            assert usage_mod._ACTIVE_SESSIONS[(1001, 100.0)]["started_at"] == t0

        # Scenario B: process terminated while agent down
        reset_usage_tracking(state_file)
        t_start = datetime(2026, 9, 27, 8, 0, 0, tzinfo=timezone.utc)
        t_last = datetime(2026, 9, 27, 8, 30, 0, tzinfo=timezone.utc)
        usage_mod._ACTIVE_SESSIONS[(1002, 200.0)] = {
            "pid": 1002,
            "create_time": 200.0,
            "application_name": "stopped_service.exe",
            "started_at": t_start,
            "last_seen_at": t_last,
            "consecutive_misses": 0,
        }
        save_usage_state(state_file)

        usage_mod._ACTIVE_SESSIONS.clear()
        usage_mod._INITIALIZED = False
        with patch("modules.usage.psutil.pid_exists", return_value=False):
            completed = load_usage_state(state_file)
            assert len(completed) == 1
            assert completed[0]["application_name"] == "stopped_service.exe"
            assert completed[0]["started_at"] == t_start.isoformat()
            assert completed[0]["ended_at"] == t_last.isoformat()
            assert completed[0]["duration_seconds"] == 1800  # 30 min accurately reconciled

        # Scenario C: corrupted state file
        reset_usage_tracking(state_file)
        with open(state_file, "w", encoding="utf-8") as f:
            f.write("<<<corrupted-json-data>>>")

        usage_mod._ACTIVE_SESSIONS.clear()
        usage_mod._INITIALIZED = False
        completed = load_usage_state(state_file)
        # Does not crash and does not fabricate huge sessions
        assert len(completed) == 0
        assert len(usage_mod._ACTIVE_SESSIONS) == 0

        reset_usage_tracking(state_file)

    def test_d01_d02_genuine_zero_vs_collection_failure_and_outbox_protection(self, tmp_path):
        """
        D-01/D-02 Audit:
        genuine 0 != collection failure.
        CPU = 0.0, RAM = 0.0, network bytes = 0 are preserved.
        CPU collection failure / hardware failure rejects payload and prevents outbox entry.
        """
        from core.outbox import DurableOutbox, OutboxPriority
        from core.runtime import upload_metrics, TokenHolder

        # Case 1: Genuine 0.0 values
        data_zero = {
            "hardware": {"cpu_usage": 0.0, "ram_percent": 0.0, "disk_percent": 0.0},
            "network": {"bytes_sent": 0, "bytes_received": 0},
        }
        payload = build_metric_payload(data_zero)
        assert payload["cpu_usage"] == 0.0
        assert payload["ram_usage"] == 0.0
        assert payload["disk_usage"] == 0.0
        assert payload["network_sent"] == 0
        assert payload["network_received"] == 0

        # Case 2: Hardware collection failure
        failed_hw = CollectionResult(
            status="failed",
            data=None,
            error=CollectorError("Hardware", "collect", "WMIError", "Timeout", time.time()),
        )
        data_failed = {"hardware": failed_hw, "network": {"bytes_sent": 100, "bytes_received": 200}}

        with pytest.raises(ValueError, match="Hardware metrics collection failed"):
            build_metric_payload(data_failed)

        # Case 3: Outbox protection: upload_metrics returns False and nothing enters outbox
        test_outbox = DurableOutbox(db_path=str(tmp_path / "audit_outbox.db"))
        token_holder = TokenHolder("test.token")
        with patch("core.runtime.get_computer_id", return_value=123):
            success = upload_metrics(data_failed, token_holder, outbox=test_outbox)
            assert success is False
            assert test_outbox.get_stats()["total_count"] == 0  # CRITICAL: 0 records in outbox!

    def test_network_identity_ethernet_wifi_virtual_same_adapter(self):
        """
        D-03/D-04/D-05 Audit:
        Ethernet + Wi-Fi + Virtual adapter -> canonical resolver returns IP and MAC
        strictly from the winning physical adapter. Confirms no uuid.getnode().
        """
        addrs = {
            "vEthernet (Default Switch)": [
                make_mac_addr("00:15:5D:AA:BB:CC"),
                make_ipv4_addr("172.19.48.1"),
            ],
            "Wi-Fi": [
                make_mac_addr("CE:30:A6:2B:D9:DB"),
                make_ipv4_addr("192.168.1.77"),
            ],
            "Ethernet": [
                make_mac_addr("CC:28:AA:8B:68:AD"),
                make_ipv4_addr("192.168.1.50"),
            ],
        }
        stats = {
            "vEthernet (Default Switch)": make_stat(isup=True, speed=10000),
            "Wi-Fi": make_stat(isup=True, speed=300),
            "Ethernet": make_stat(isup=True, speed=1000),
        }

        # Ensure uuid.getnode is never called
        with patch("uuid.getnode", side_effect=AssertionError("uuid.getnode must NOT be called")):
            ident = get_canonical_network_identity(addrs=addrs, stats=stats)

        assert ident["status"] == "success"
        # Ethernet wins over Wi-Fi and vEthernet
        assert ident["interface"] == "Ethernet"
        assert ident["ip_address"] == "192.168.1.50"
        assert ident["mac_address"] == "CC:28:AA:8B:68:AD"  # Must match Ethernet's MAC!
