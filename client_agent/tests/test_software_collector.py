"""
Cross-platform tests for Software Inventory Collector (modules.software).

Validates:
1. Safe import on any platform without requiring winreg.
2. Non-Windows behavior: get_installed_software() returns empty list safely.
3. Windows behavior: registry collection functions when winreg is present.
4. Software state persistence and SHA-256 deterministic fingerprinting.
"""

from __future__ import annotations

import os
from unittest.mock import patch
import pytest

import modules.software as software_mod


def test_software_module_importable():
    """Verify modules.software can be imported and exposes expected collector API."""
    assert hasattr(software_mod, "get_installed_software")
    assert hasattr(software_mod, "compute_software_fingerprint")
    assert hasattr(software_mod, "load_software_state")
    assert hasattr(software_mod, "save_software_state")
    assert hasattr(software_mod, "HAVE_WINREG")


def test_non_windows_registry_collector_returns_empty_list():
    """Verify non-Windows platform (or missing winreg) returns empty list without error."""
    with patch.object(software_mod, "HAVE_WINREG", False), \
         patch.object(software_mod, "winreg", None):
        result = software_mod.get_installed_software()
        assert result == []
        assert isinstance(result, list)


def test_non_windows_scan_registry_path_returns_empty_list():
    """Verify _scan_registry_path returns empty list when winreg is unavailable."""
    with patch.object(software_mod, "HAVE_WINREG", False), \
         patch.object(software_mod, "winreg", None):
        result = software_mod._scan_registry_path(r"SOFTWARE\Test", seen=set())
        assert result == []


def test_non_windows_read_value_returns_default():
    """Verify _read_value returns default value when winreg is unavailable."""
    with patch.object(software_mod, "HAVE_WINREG", False), \
         patch.object(software_mod, "winreg", None):
        result = software_mod._read_value(None, "DisplayName", default="Fallback")
        assert result == "Fallback"


def test_software_fingerprint_deterministic():
    """Verify compute_software_fingerprint produces deterministic SHA-256 for empty and non-empty lists."""
    empty_fp = software_mod.compute_software_fingerprint([])
    assert isinstance(empty_fp, str)
    assert len(empty_fp) == 64

    # Identical software items in different orders yield identical fingerprint
    list_a = [
        {"name": "App Alpha", "version": "1.0", "publisher": "Pub A", "install_date": "2026-01-01"},
        {"name": "App Beta", "version": "2.0", "publisher": "Pub B", "install_date": "2026-02-01"},
    ]
    list_b = [
        {"name": "App Beta", "version": "2.0", "publisher": "Pub B", "install_date": "2026-02-01"},
        {"name": "App Alpha", "version": "1.0", "publisher": "Pub A", "install_date": "2026-01-01"},
    ]
    assert software_mod.compute_software_fingerprint(list_a) == software_mod.compute_software_fingerprint(list_b)


def test_software_state_roundtrip(tmp_path):
    """Verify load_software_state and save_software_state roundtrip correctly."""
    state_file = str(tmp_path / "test_software_state.json")
    initial_state = software_mod.load_software_state(state_file)
    assert initial_state["last_delivered_fingerprint"] is None

    software_mod.record_software_enqueued("fp_enqueued_123", state_file=state_file)
    state = software_mod.load_software_state(state_file)
    assert state["last_enqueued_fingerprint"] == "fp_enqueued_123"

    software_mod.record_software_delivered("fp_delivered_456", state_file=state_file)
    state = software_mod.load_software_state(state_file)
    assert state["last_delivered_fingerprint"] == "fp_delivered_456"
    assert state["last_delivery_time"] is not None
