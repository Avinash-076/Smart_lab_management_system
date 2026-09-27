from __future__ import annotations

import time

from config import (
    ENABLE_HARDWARE_INFO,
    ENABLE_ISSUE_REPORTING,
    ENABLE_NETWORK_INFO,
    ENABLE_PROCESS_INFO,
    ENABLE_SOFTWARE_INFO,
    ENABLE_SYSTEM_INFO,
    ENABLE_USAGE_INFO,
    PROCESS_COLLECTION_INTERVAL,
    SOFTWARE_SCAN_INTERVAL,
)

from core.health import safe_run

from modules.hardware import get_hardware_info
from modules.issues import detect_issues
from modules.network import get_network_info
from modules.processes import get_running_processes
from modules.software import get_installed_software
from modules.system_info import get_system_info
from modules.usage import collect_usage_sessions


class SoftwareCache:
    """
    Explicit cache container for installed software inventory (D-07).
    Distinguishes valid empty inventory ([]) from missing, expired,
    corrupted, or failed cache states.
    """

    def __init__(self, ttl: float = SOFTWARE_SCAN_INTERVAL):
        self.ttl = ttl
        self._items: list[dict] | None = None
        self._last_scan_time: float | None = None
        self._is_valid: bool = False

    @property
    def is_present(self) -> bool:
        """Returns True if the cache contains a valid scan, even if empty ([])."""
        return self._is_valid and self._items is not None

    def is_expired(self, now: float | None = None) -> bool:
        """Check if the cache has exceeded its TTL."""
        if not self._is_valid or self._last_scan_time is None:
            return True
        if now is None:
            now = time.monotonic()
        return (now - self._last_scan_time) >= self.ttl

    def get(self, now: float | None = None) -> list[dict] | None:
        """
        Return cached inventory if valid and not expired.
        Returns None if cache is missing, expired, or invalid.
        """
        if not self._is_valid or self._items is None:
            return None
        # Integrity check: items must be a list
        if not isinstance(self._items, list):
            self.invalidate()
            return None
        if self.is_expired(now):
            return None
        return self._items

    def set(self, items: list[dict], now: float | None = None) -> None:
        """
        Store a valid scan result in cache (even if empty []).
        Validates that items is a list of dicts.
        """
        if not isinstance(items, list):
            self.invalidate()
            return
        if now is None:
            now = time.monotonic()
        self._items = items
        self._last_scan_time = now
        self._is_valid = True

    def invalidate(self) -> None:
        """Mark cache as missing/invalid."""
        self._items = None
        self._last_scan_time = None
        self._is_valid = False


class ProcessCache:
    """
    Explicit cache container for running processes inventory (E-01).
    Avoids expensive psutil.process_iter() enumeration on every 20s cycle.
    """

    def __init__(self, ttl: float = PROCESS_COLLECTION_INTERVAL):
        self.ttl = ttl
        self._items: list[dict] | None = None
        self._last_scan_time: float | None = None
        self._is_valid: bool = False

    @property
    def is_present(self) -> bool:
        """Returns True if the cache contains a valid scan, even if empty ([])."""
        return self._is_valid and self._items is not None

    def is_expired(self, now: float | None = None) -> bool:
        """Check if the cache has exceeded its TTL."""
        if not self._is_valid or self._last_scan_time is None:
            return True
        if now is None:
            now = time.monotonic()
        return (now - self._last_scan_time) >= self.ttl

    def get(self, now: float | None = None) -> list[dict] | None:
        """
        Return cached inventory if valid and not expired.
        Returns None if cache is missing, expired, or invalid.
        """
        if not self._is_valid or self._items is None:
            return None
        if not isinstance(self._items, list):
            self.invalidate()
            return None
        if self.is_expired(now):
            return None
        return self._items

    def set(self, items: list[dict], now: float | None = None) -> None:
        """Store a valid process scan result in cache."""
        if not isinstance(items, list):
            self.invalidate()
            return
        if now is None:
            now = time.monotonic()
        self._items = items
        self._last_scan_time = now
        self._is_valid = True

    def invalidate(self) -> None:
        """Mark cache as missing/invalid."""
        self._items = None
        self._last_scan_time = None
        self._is_valid = False


_software_cache = SoftwareCache()
_process_cache = ProcessCache()


def _collect_software(cache: SoftwareCache | None = None) -> list[dict]:
    """
    Collect software inventory only when the configured
    software scan interval has elapsed (E-05).

    The previously collected inventory (including valid empty [])
    is reused between scans.
    """
    active_cache = cache if cache is not None else _software_cache
    now = time.monotonic()

    cached = active_cache.get(now=now)
    if cached is not None:
        return cached

    # Rescan required: cache missing, expired, or corrupted
    raw_software = get_installed_software()
    if not isinstance(raw_software, list):
        raise TypeError(f"get_installed_software returned invalid type: {type(raw_software)}")

    active_cache.set(raw_software, now=now)
    return raw_software


def _collect_processes(cache: ProcessCache | None = None) -> list[dict]:
    """
    Collect running process inventory only when the configured
    process collection interval has elapsed (E-01).

    The previously collected inventory is reused between scans.
    """
    active_cache = cache if cache is not None else _process_cache
    now = time.monotonic()

    cached = active_cache.get(now=now)
    if cached is not None:
        return cached

    raw_processes = get_running_processes()
    if not isinstance(raw_processes, list):
        raise TypeError(f"get_running_processes returned invalid type: {type(raw_processes)}")

    active_cache.set(raw_processes, now=now)
    return raw_processes


def collect_all_data(
    include_processes: bool = True,
    include_software: bool = True,
    software_cache: SoftwareCache | None = None,
    process_cache: ProcessCache | None = None,
) -> dict:
    """
    Collect all enabled client-agent data with cadence gating (E-01, E-05).

    Parameters:
    - include_processes: If True, collects process inventory (reusing cache if valid).
                         If False, processes collection is bypassed for this cycle.
    - include_software: If True, collects software inventory (reusing cache if valid).
                        If False, software scanning is bypassed for this cycle.
    """
    data = {}

    # ------------------------------------------
    # System Information
    # ------------------------------------------
    if ENABLE_SYSTEM_INFO:
        data["system"] = safe_run(
            "System Information",
            get_system_info,
        )

    # ------------------------------------------
    # Hardware Information
    # ------------------------------------------
    if ENABLE_HARDWARE_INFO:
        data["hardware"] = safe_run(
            "Hardware Information",
            get_hardware_info,
        )

    # ------------------------------------------
    # Software Inventory (E-05 Cadence)
    # ------------------------------------------
    if ENABLE_SOFTWARE_INFO and include_software:
        data["software"] = safe_run(
            "Installed Software",
            lambda: _collect_software(cache=software_cache),
        )

    # ------------------------------------------
    # Process Monitoring (E-01 Cadence)
    # ------------------------------------------
    if ENABLE_PROCESS_INFO and include_processes:
        data["processes"] = safe_run(
            "Running Processes",
            lambda: _collect_processes(cache=process_cache),
        )

    # ------------------------------------------
    # Usage Tracking (20s event tracking)
    # ------------------------------------------
    if ENABLE_USAGE_INFO:
        data["usage"] = safe_run(
            "Application Usage",
            collect_usage_sessions,
        )

    # ------------------------------------------
    # Network Information (20s counters)
    # ------------------------------------------
    if ENABLE_NETWORK_INFO:
        data["network"] = safe_run(
            "Network Information",
            get_network_info,
        )

    # ------------------------------------------
    # Issue Detection (20s thresholds)
    # ------------------------------------------
    if ENABLE_ISSUE_REPORTING:
        data["issues"] = safe_run(
            "Problem Detection",
            lambda: detect_issues(data),
        )

    return data
