"""
Cross-platform tests for Software Inventory Collector (modules.software).

Validates:
1. Safe import on any platform without requiring winreg.
2. Non-Windows behavior: get_installed_software() returns empty list safely.
3. Windows behavior: registry collection functions when winreg is present.
4. Software state persistence and SHA-256 deterministic fingerprinting.
5. All 20 required endpoint inventory filtering, deduplication, and classification scenarios.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest

import modules.software as software_mod
from modules.software import (
    RawSoftwareEntry,
    SoftwareClassification,
    classify_software_entry,
    compute_software_fingerprint,
    deduplicate_software_records,
    get_installed_software,
    load_software_state,
    record_software_delivered,
    record_software_enqueued,
    save_software_state,
)


# ============================================================================
# Reusable Mock Registry Framework for Cross-Platform Unit Tests
# ============================================================================

class MockRegistrySubkey:
    """Mock open subkey holding a dictionary of registry values."""

    def __init__(self, values: dict[str, any]):
        self.values = values

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockWinregHive:
    """Mock open hive holding a mapping of subkey names to their value dictionaries."""

    def __init__(self, subkeys: dict[str, dict[str, any]]):
        self.subkeys = subkeys

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockWinregModule:
    """Mock winreg module supporting OpenKey, QueryInfoKey, EnumKey, and QueryValueEx."""

    HKEY_LOCAL_MACHINE = 1

    def __init__(self, registry_tree: dict[str, dict[str, dict[str, any]]]):
        # registry_tree structure: {registry_path: {subkey_name: {val_name: val}}}
        self.registry_tree = registry_tree

    def OpenKey(self, hive, path):
        if path in self.registry_tree:
            return MockWinregHive(self.registry_tree[path])
        # Opening subkey under path
        for root_path, subkeys in self.registry_tree.items():
            if path in subkeys:
                return MockRegistrySubkey(subkeys[path])
        raise FileNotFoundError(f"Key not found: {path}")

    def QueryInfoKey(self, key):
        if isinstance(key, MockWinregHive):
            return (len(key.subkeys), 0, 0)
        return (0, 0, 0)

    def EnumKey(self, key, index):
        if isinstance(key, MockWinregHive):
            return list(key.subkeys.keys())[index]
        raise OSError("Invalid subkey index")

    def QueryValueEx(self, key, value_name):
        if isinstance(key, MockRegistrySubkey) and value_name in key.values:
            val = key.values[value_name]
            if isinstance(val, tuple):
                return val
            return val, 1
        raise FileNotFoundError(f"Value '{value_name}' not found")


# ============================================================================
# Existing Baseline Tests (Preserved 100%)
# ============================================================================

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


# ============================================================================
# Section 7 Required Automated Tests (Scenarios 1-20)
# ============================================================================

def test_01_missing_or_empty_display_name():
    """Scenario 1: Exclude entries with missing or empty DisplayName values."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "ValidApp": {"DisplayName": "Valid Application", "DisplayVersion": "1.0"},
            "NoNameKey": {"DisplayVersion": "2.0", "Publisher": "Orphan"},
            "EmptyNameKey": {"DisplayName": "", "DisplayVersion": "3.0"},
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        assert len(result) == 1
        assert result[0]["name"] == "Valid Application"


def test_02_whitespace_only_names():
    """Scenario 2: Exclude whitespace-only names and normalize excess whitespace in names."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "SpaceKey": {"DisplayName": "    \t  \n  "},
            "PaddedKey": {"DisplayName": "   Git   for   Windows   ", "DisplayVersion": "2.46.0"},
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        assert len(result) == 1
        assert result[0]["name"] == "Git for Windows"


def test_03_case_insensitive_duplicate_entries():
    """Scenario 3: Avoid case-sensitive duplicates and whitespace-induced duplicates."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "AppUpper": {"DisplayName": "GOOGLE CHROME", "DisplayVersion": "128.0", "InstallLocation": r"C:\Program Files\Google\Chrome"},
            "AppLower": {"DisplayName": "google chrome  ", "DisplayVersion": "128.0", "InstallLocation": r"C:\Program Files\Google\Chrome"},
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        assert len(result) == 1
        assert result[0]["name"].lower() == "google chrome"


def test_04_same_application_name_with_different_versions():
    """Scenario 4: Preserve same application name when different versions represent distinct installations."""
    records = [
        {"name": "Python", "version": "3.11.2", "publisher": "PSF", "install_location": r"C:\Python311", "architecture": "64-bit"},
        {"name": "Python", "version": "3.12.4", "publisher": "PSF", "install_location": r"C:\Python312", "architecture": "64-bit"},
    ]
    deduped = deduplicate_software_records(records)
    assert len(deduped) == 2
    versions = {r["version"] for r in deduped}
    assert versions == {"3.11.2", "3.12.4"}


def test_05_same_application_installed_in_different_locations():
    """Scenario 5: Preserve same application name and version when installed in different locations."""
    records = [
        {"name": "CustomLabTool", "version": "1.0", "install_location": r"C:\Lab\InstanceA", "architecture": "64-bit"},
        {"name": "CustomLabTool", "version": "1.0", "install_location": r"D:\Lab\InstanceB", "architecture": "64-bit"},
    ]
    deduped = deduplicate_software_records(records)
    assert len(deduped) == 2
    locations = {r["install_location"].rstrip("\\") for r in deduped}
    assert locations == {r"C:\Lab\InstanceA", r"D:\Lab\InstanceB"}


def test_06_missing_optional_metadata():
    """Scenario 6: Handle missing versions, publishers, install dates, and locations gracefully without discarding."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "BarebonesApp": {"DisplayName": "Barebones Utility"},
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        assert len(result) == 1
        item = result[0]
        assert item["name"] == "Barebones Utility"
        assert item["version"] == "Unknown"
        assert item["publisher"] == "Unknown"
        assert item["install_date"] == "Unknown"
        assert item["install_location"] is None
        assert item["architecture"] == "64-bit"


def test_07_system_component_enabled_and_disabled():
    """Scenario 7: Filter internal MSI subcomponents with SystemComponent=1 while keeping standalone applications."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "AppReal": {"DisplayName": "Blender", "DisplayVersion": "4.2", "SystemComponent": 0},
            "SubFeatureFrag": {
                "DisplayName": "Python 3.13.5 pip Bootstrap (64-bit)",
                "DisplayVersion": "3.13.5",
                "SystemComponent": 1,
            },
            "StandaloneWSL": {
                "DisplayName": "Windows Subsystem for Linux",
                "DisplayVersion": "2.4.13",
                "SystemComponent": 1,
            },
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        names = [r["name"] for r in result]
        assert "Blender" in names
        assert "Windows Subsystem for Linux" in names
        assert "Python 3.13.5 pip Bootstrap (64-bit)" not in names


def test_08_parent_key_name_present_and_absent():
    """Scenario 8: Subordinate child components with ParentKeyName to the parent installation."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "ParentOffice": {"DisplayName": "Microsoft Office Professional", "DisplayVersion": "2021"},
            "ChildWordAddin": {
                "DisplayName": "Office Shared Proofing Tools",
                "ParentKeyName": "ParentOffice",
                "SystemComponent": 1,
            },
            "IndependentTool": {"DisplayName": "Independent Tool", "DisplayVersion": "1.0"},
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        names = [r["name"] for r in result]
        assert "Microsoft Office Professional" in names
        assert "Independent Tool" in names
        assert "Office Shared Proofing Tools" not in names


def test_09_different_release_type_values():
    """Scenario 9: Exclude hotfixes and security updates based on ReleaseType without excluding legitimate apps."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "RealApp": {"DisplayName": "VLC Media Player", "ReleaseType": None},
            "SecurityHotfix": {"DisplayName": "Hotfix for Windows (KB987654)", "ReleaseType": "Hotfix"},
            "ServicePack": {"DisplayName": "Service Pack 1", "ReleaseType": "ServicePack"},
            "UpdateRollup": {"DisplayName": "Update Rollup 3", "ReleaseType": "Update Rollup"},
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        names = [r["name"] for r in result]
        assert "VLC Media Player" in names
        assert "Hotfix for Windows (KB987654)" not in names
        assert "Service Pack 1" not in names
        assert "Update Rollup 3" not in names


def test_10_no_display_enabled_and_disabled():
    """Scenario 10: Use NoDisplay as supporting evidence to filter hidden components."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "DisplayableApp": {"DisplayName": "Docker Desktop", "NoDisplay": 0},
            "HiddenHelper": {"DisplayName": "Internal Helper Tool", "NoDisplay": 1},
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        names = [r["name"] for r in result]
        assert "Docker Desktop" in names
        assert "Internal Helper Tool" not in names


def test_11_legitimate_microsoft_applications():
    """Scenario 11: Ensure Microsoft applications are never excluded merely because publisher is Microsoft."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "MS365": {"DisplayName": "Microsoft 365 - en-us", "Publisher": "Microsoft Corporation", "DisplayVersion": "16.0"},
            "OneNote": {"DisplayName": "Microsoft OneNote - en-us", "Publisher": "Microsoft Corporation", "DisplayVersion": "16.0"},
            "Edge": {"DisplayName": "Microsoft Edge", "Publisher": "Microsoft Corporation", "DisplayVersion": "128.0"},
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        names = [r["name"] for r in result]
        assert "Microsoft 365 - en-us" in names
        assert "Microsoft OneNote - en-us" in names
        assert "Microsoft Edge" in names


def test_12_applications_containing_update_or_runtime_in_name():
    """Scenario 12: Preserve applications whose names contain words like 'Update' or 'Runtime'."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "AsusUpdate": {"DisplayName": "ASUS Update Helper", "Publisher": "ASUSTeK"},
            "AdobeRefresh": {"DisplayName": "Adobe Refresh Manager", "Publisher": "Adobe"},
            "VCRedist": {"DisplayName": "Microsoft Visual C++ 2015-2022 Redistributable (x64)", "DisplayVersion": "14.40"},
            "NetRuntime": {"DisplayName": "Microsoft .NET Runtime - 8.0.13 (x64)", "DisplayVersion": "8.0.13"},
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        names = [r["name"] for r in result]
        assert "ASUS Update Helper" in names
        assert "Adobe Refresh Manager" in names
        assert "Microsoft Visual C++ 2015-2022 Redistributable (x64)" in names
        assert "Microsoft .NET Runtime - 8.0.13 (x64)" in names


def test_13_python_java_vscode_and_database_software():
    """Scenario 13: Guarantee developer tools (Python, Java, VS Code, databases) remain discoverable."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "PythonApp": {"DisplayName": "Python 3.12.7 (64-bit)", "Publisher": "Python Software Foundation", "DisplayVersion": "3.12.7"},
            "JavaApp": {"DisplayName": "Java(TM) SE Development Kit 21.0.2 (64-bit)", "Publisher": "Oracle Corporation", "DisplayVersion": "21.0.2"},
            "VSCode": {"DisplayName": "Microsoft Visual Studio Code", "Publisher": "Microsoft Corporation", "DisplayVersion": "1.92.0"},
            "Postgres": {"DisplayName": "PostgreSQL 16", "Publisher": "PostgreSQL Global Development Group", "DisplayVersion": "16.3"},
            "Mongo": {"DisplayName": "MongoDB 8.0.0", "Publisher": "MongoDB Inc.", "DisplayVersion": "8.0.0"},
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        names = [r["name"] for r in result]
        assert "Python 3.12.7 (64-bit)" in names
        assert "Java(TM) SE Development Kit 21.0.2 (64-bit)" in names
        assert "Microsoft Visual Studio Code" in names
        assert "PostgreSQL 16" in names
        assert "MongoDB 8.0.0" in names


def test_14_malformed_registry_values():
    """Scenario 14: Safely reject or sanitize malformed data (embedded nulls, binary numbers) without collector crashes."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "NullByteApp": {"DisplayName": "Clean\x00AppName", "DisplayVersion": "1.0\x00extra"},
            "IntegerAsName": {"DisplayName": 12345},
            "LongText": {"DisplayName": "X" * 300, "DisplayVersion": "V" * 150},
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        assert len(result) == 3
        names = {r["name"] for r in result}
        assert "Clean AppName" in names
        assert "12345" in names
        # Max length truncation check (name <= 255)
        long_item = next(r for r in result if r["name"].startswith("XXX"))
        assert len(long_item["name"]) <= 255


def test_15_duplicate_entries_across_registry_locations():
    """Scenario 15: Cross-hive duplicates (64-bit vs WOW6432Node) merge deterministically keeping richer record."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "7Zip64": {
                "DisplayName": "7-Zip 24.08 (x64)",
                "DisplayVersion": "24.08",
                "Publisher": "Igor Pavlov",
                "InstallLocation": r"C:\Program Files\7-Zip",
                "InstallDate": "20260115",
            },
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {
            "7Zip32": {
                "DisplayName": "7-Zip 24.08 (x64)",
                "DisplayVersion": "24.08",
                "Publisher": "Unknown",
                "InstallLocation": "",
            },
        },
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        assert len(result) == 1
        item = result[0]
        assert item["name"] == "7-Zip 24.08 (x64)"
        assert item["publisher"] == "Igor Pavlov"
        assert item["install_location"] == "C:\\Program Files\\7-Zip\\"
        assert item["install_date"] == "2026-01-15"


def test_16_stable_ordering_and_deterministic_fingerprints():
    """Scenario 16: Ensure stable canonical ordering and identical fingerprints across equivalent inventories."""
    inv1 = [
        {"name": "Zebra Editor", "version": "1.0", "publisher": "Z-Corp", "install_date": "2026-01-01"},
        {"name": "Alpha CAD", "version": "2.0", "publisher": "A-Corp", "install_date": "2026-02-01"},
        {"name": "Beta Browser", "version": "3.0", "publisher": "B-Corp", "install_date": "2026-03-01"},
    ]
    inv2 = [
        {"name": "Beta Browser", "version": "3.0", "publisher": "B-Corp", "install_date": "2026-03-01"},
        {"name": "Zebra Editor", "version": "1.0", "publisher": "Z-Corp", "install_date": "2026-01-01"},
        {"name": "Alpha CAD", "version": "2.0", "publisher": "A-Corp", "install_date": "2026-02-01"},
    ]
    fp1 = compute_software_fingerprint(inv1)
    fp2 = compute_software_fingerprint(inv2)
    assert fp1 == fp2

    deduped = deduplicate_software_records(inv2)
    assert [r["name"] for r in deduped] == ["Alpha CAD", "Beta Browser", "Zebra Editor"]


def test_17_correct_upload_behavior_when_inventory_changes(tmp_path):
    """Scenario 17: Genuine inventory changes generate distinct fingerprints and trigger upload."""
    from core.managers import UploadManager, TokenManager, TokenHolder, OutboxManager
    from core.outbox import DurableOutbox

    state_file = str(tmp_path / "software_state.json")
    outbox = DurableOutbox(db_path=str(tmp_path / "outbox.db"))
    outbox_mgr = OutboxManager(outbox=outbox, enable_outbox=True, software_state_file=state_file)
    token_mgr = TokenManager(token_holder=TokenHolder("test-token"))
    upload_mgr = UploadManager()

    inv_v1 = [{"name": "LabApp", "version": "1.0", "publisher": "Lab", "install_date": "2026-01-01"}]
    with patch("core.managers._resolve_computer_id", return_value=999):
        uploaded_1 = upload_mgr.upload_software(inv_v1, token_mgr, outbox_mgr, state_file=state_file)
        assert uploaded_1 is True

        # Simulate delivery
        fp_v1 = compute_software_fingerprint(inv_v1)
        record_software_delivered(fp_v1, state_file)

        # Inventory change: version bump
        inv_v2 = [{"name": "LabApp", "version": "2.0", "publisher": "Lab", "install_date": "2026-01-01"}]
        fp_v2 = compute_software_fingerprint(inv_v2)
        assert fp_v1 != fp_v2

        uploaded_2 = upload_mgr.upload_software(inv_v2, token_mgr, outbox_mgr, state_file=state_file)
        assert uploaded_2 is True


def test_18_no_unnecessary_upload_when_inventory_unchanged(tmp_path):
    """Scenario 18: Unchanged inventory identical to last delivered fingerprint skips upload without I/O."""
    from core.managers import UploadManager, TokenManager, TokenHolder, OutboxManager
    from core.outbox import DurableOutbox

    state_file = str(tmp_path / "software_state.json")
    outbox = DurableOutbox(db_path=str(tmp_path / "outbox.db"))
    outbox_mgr = OutboxManager(outbox=outbox, enable_outbox=True, software_state_file=state_file)
    token_mgr = TokenManager(token_holder=TokenHolder("test-token"))
    upload_mgr = UploadManager()

    inv = [{"name": "LabApp", "version": "1.0", "publisher": "Lab", "install_date": "2026-01-01"}]
    fp = compute_software_fingerprint(inv)
    record_software_delivered(fp, state_file)

    with patch("core.managers._resolve_computer_id", return_value=999):
        # Equivalent inventory with whitespace or reordered keys skips upload
        inv_equivalent = [{"install_date": "2026-01-01", "name": "LabApp  ", "publisher": "Lab", "version": "1.0"}]
        uploaded = upload_mgr.upload_software(inv_equivalent, token_mgr, outbox_mgr, state_file=state_file)
        assert uploaded is False


def test_19_empty_registry_results_and_registry_access_errors():
    """Scenario 19: Empty registry hive and OSError / AccessDenied exceptions are caught cleanly."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {},
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        assert result == []

    # Access Denied / OSError simulation
    broken_winreg = MagicMock()
    broken_winreg.OpenKey.side_effect = PermissionError("Access Denied to registry key")
    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", broken_winreg):
        result = get_installed_software()
        assert result == []


def test_20_backward_compatibility_with_backend_payload():
    """Scenario 20: Verified records strictly conform to the backend SoftwareUpload/SoftwareItem contract."""
    mock_tree = {
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall": {
            "TestApp1": {
                "DisplayName": "PostgreSQL 16",
                "DisplayVersion": "16.4-1",
                "Publisher": "PostgreSQL Global Development Group",
                "InstallDate": "20260401",
                "InstallLocation": r"C:\Program Files\PostgreSQL\16",
            },
        },
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall": {},
    }
    mock_winreg = MockWinregModule(mock_tree)

    with patch.object(software_mod, "HAVE_WINREG", True), \
         patch.object(software_mod, "winreg", mock_winreg):
        result = get_installed_software()
        assert len(result) == 1
        item = result[0]

        # Conformance to backend SoftwareItem schema bounds:
        assert isinstance(item["name"], str) and 1 <= len(item["name"]) <= 255
        assert item["version"] is None or (isinstance(item["version"], str) and len(item["version"]) <= 100)
        assert item["publisher"] is None or (isinstance(item["publisher"], str) and len(item["publisher"]) <= 255)
        assert item["install_date"] is None or (isinstance(item["install_date"], str) and len(item["install_date"]) <= 20)
        assert item["install_location"] is None or (isinstance(item["install_location"], str) and len(item["install_location"]) <= 500)
        assert item["architecture"] is None or (isinstance(item["architecture"], str) and len(item["architecture"]) <= 20)
