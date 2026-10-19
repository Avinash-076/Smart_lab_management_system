"""
Unit tests for SLMS Client Agent Device Discovery & Authorization Monitor (modules/device_monitor.py).
Tests Phase 1 through Phase 4 requirements according to the test specification.
"""

from __future__ import annotations

import json
import os
import tempfile
import pytest

from modules.device_monitor import (
    AuthorizationState,
    DeviceCategory,
    DeviceLifecycleState,
    NormalizedDevice,
    build_device_issue_payload,
    classify_device,
    deduplicate_storage_devices,
    determine_incident_severity,
    enumerate_windows_devices,
    evaluate_authorization,
    extract_vid_pid,
    load_device_state,
    load_device_whitelist,
    save_device_state,
    save_device_whitelist,
    scan_and_evaluate_devices,
)


@pytest.fixture
def tmp_env(tmp_path):
    """Provide isolated paths for device state and whitelist files."""
    state_file = str(tmp_path / "test_device_state.json")
    whitelist_file = str(tmp_path / "test_device_whitelist.json")
    return {
        "state_file": state_file,
        "whitelist_file": whitelist_file,
        "tmp_path": tmp_path,
    }


def make_test_device(
    instance_id: str = "USB\\VID_0951&PID_1666\\00187D0E0B19B950",
    name: str = "Kingston DataTraveler 3.0",
    category: DeviceCategory = DeviceCategory.USB_STORAGE,
    device_class: str = "DiskDrive",
    vendor_id: str | None = "0951",
    product_id: str | None = "1666",
    serial_number: str | None = "00187D0E0B19B950",
) -> NormalizedDevice:
    """Helper to instantiate test NormalizedDevice."""
    return NormalizedDevice(
        instance_id=instance_id,
        name=name,
        category=category,
        device_class=device_class,
        hardware_ids=[f"USB\\VID_{vendor_id}&PID_{product_id}"] if vendor_id and product_id else [],
        vendor_id=vendor_id,
        product_id=product_id,
        serial_number=serial_number,
        present=True,
    )


# ============================================================================
# Classification & Identification Tests
# ============================================================================

def test_extract_vid_pid():
    vid, pid = extract_vid_pid("USB\\VID_0951&PID_1666\\12345")
    assert vid == "0951"
    assert pid == "1666"

    vid, pid = extract_vid_pid("ACPI\\PNP0A08\\0")
    assert vid is None
    assert pid is None


def test_classify_device_categories():
    assert classify_device("DiskDrive", "USBSTOR", "USB\\VID_0951&PID_1666") == DeviceCategory.USB_STORAGE
    assert classify_device("Net", "netwtw08", "USB\\VID_0BDA&PID_8153") == DeviceCategory.USB_NETWORK
    assert classify_device("WPD", "WpdBusEnumRoot", "SWD\\WPDBUSENUM\\_??_USBSTOR#DISK") == DeviceCategory.USB_PHONE
    assert classify_device("Keyboard", "kbdhid", "HID\\VID_046D&PID_C31C") == DeviceCategory.USB_HID
    assert classify_device("Camera", "usbvideo", "USB\\VID_04F2&PID_B684") == DeviceCategory.USB_AUDIO_VIDEO
    assert classify_device("Other", "unknown", "USB\\VID_1234&PID_5678") == DeviceCategory.USB_OTHER


# ============================================================================
# Test 1: Empty Successful Device Inventory
# ============================================================================

def test_empty_successful_device_inventory(tmp_env):
    """Successful enumeration returning zero devices produces zero issues."""
    mock_enum = lambda: ([], True)
    issues, recoveries = scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=mock_enum,
    )
    assert issues == []
    assert recoveries == []


# ============================================================================
# Test 2: Normal Approved Peripherals
# ============================================================================

def test_normal_approved_peripherals(tmp_env):
    """Explicitly approved lab peripherals do not generate issues."""
    kb = make_test_device(
        instance_id="USB\\VID_413C&PID_2113\\01",
        name="Dell KB216 Wired Keyboard",
        category=DeviceCategory.USB_HID,
        device_class="Keyboard",
        vendor_id="413C",
        product_id="2113",
    )
    whitelist = {
        "version": 1,
        "approved_devices": [kb.instance_id],
        "approved_vid_pids": [],
        "approved_categories": [],
    }
    save_device_whitelist(whitelist, tmp_env["whitelist_file"])

    mock_enum = lambda: ([kb], True)
    issues, recoveries = scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=mock_enum,
    )
    assert issues == []
    assert recoveries == []


# ============================================================================
# Test 3 & 4: Unauthorized USB Storage & Network Adapter (Phase 3.1)
# ============================================================================

def test_unauthorized_usb_storage_risk_severity():
    dev = make_test_device(category=DeviceCategory.USB_STORAGE)
    auth = evaluate_authorization(dev, whitelist={"approved_devices": []})
    assert auth == AuthorizationState.UNAUTHORIZED
    assert determine_incident_severity(dev.category, auth) == "critical"


def test_unauthorized_usb_network_risk_severity():
    dev = make_test_device(
        instance_id="USB\\VID_0BDA&PID_8153\\001",
        name="Realtek USB GbE Network Adapter",
        category=DeviceCategory.USB_NETWORK,
        device_class="Net",
        vendor_id="0BDA",
        product_id="8153",
    )
    auth = evaluate_authorization(dev, whitelist={"approved_devices": []})
    assert auth == AuthorizationState.UNAUTHORIZED
    assert determine_incident_severity(dev.category, auth) == "high"


# ============================================================================
# Test 5 & 6: Unknown Peripheral & Explicitly Approved Device
# ============================================================================

def test_unknown_peripheral_and_explicit_approval(monkeypatch):
    mouse = make_test_device(
        instance_id="USB\\VID_046D&PID_C077\\02",
        name="Logitech Optical USB Mouse",
        category=DeviceCategory.USB_HID,
        device_class="Mouse",
        vendor_id="046D",
        product_id="C077",
    )
    # When not whitelisted and ALERT_ON_UNKNOWN_PERIPHERAL is False (default):
    monkeypatch.setattr("modules.device_monitor.ALERT_ON_UNKNOWN_PERIPHERAL", False)
    auth_unapproved = evaluate_authorization(mouse, whitelist={"approved_devices": []})
    assert auth_unapproved == AuthorizationState.PENDING_APPROVAL
    # Should be None by default to prevent false-alarm incidents for standard lab mice/keyboards
    assert determine_incident_severity(mouse.category, auth_unapproved) is None

    # When ALERT_ON_UNKNOWN_PERIPHERAL is explicitly enabled:
    monkeypatch.setattr("modules.device_monitor.ALERT_ON_UNKNOWN_PERIPHERAL", True)
    assert determine_incident_severity(mouse.category, auth_unapproved) == "medium"

    # When whitelisted by VID_PID:
    auth_approved = evaluate_authorization(
        mouse,
        whitelist={"approved_devices": [], "approved_vid_pids": ["VID_046D&PID_C077"]},
    )
    assert auth_approved == AuthorizationState.APPROVED
    assert determine_incident_severity(mouse.category, auth_approved) is None


def test_deduplicate_storage_devices_collapses_parent_and_child():
    """
    Ensure when a single USB stick presents both a generic parent ('USB Mass Storage Device')
    and a specific disk drive ('Lexar USB Flash Drive USB Device'), the generic parent is suppressed
    and VID/PID metadata is preserved on the disk drive.
    """
    parent_device = NormalizedDevice(
        instance_id="USB\\VID_05DC&PID_A815\\07000000000000000000",
        name="USB Mass Storage Device",
        category=DeviceCategory.USB_STORAGE,
        device_class="USB",
        hardware_ids=["USB\\VID_05DC&PID_A815"],
        vendor_id="05DC",
        product_id="A815",
        serial_number="07000000000000000000",
        present=True,
    )
    child_disk = NormalizedDevice(
        instance_id="USBSTOR\\DISK&VEN_LEXAR&PROD_USB_FLASH_DRIVE&REV_1100\\07000000000000000000&0",
        name="Lexar USB Flash Drive USB Device",
        category=DeviceCategory.USB_STORAGE,
        device_class="DiskDrive",
        hardware_ids=["USBSTOR\\DiskLexar___USB_Flash_Drive_1100"],
        vendor_id=None,
        product_id=None,
        serial_number=None,
        present=True,
    )

    deduped = deduplicate_storage_devices([parent_device, child_disk])
    assert len(deduped) == 1
    assert deduped[0].name == "Lexar USB Flash Drive USB Device"
    # VID/PID inherited from parent
    assert deduped[0].vendor_id == "05DC"
    assert deduped[0].product_id == "A815"


# ============================================================================
# Test 7, 8, 9: Missing Serial Number, Generic ID, Multiple Devices
# ============================================================================

def test_missing_serial_number_and_stable_hash():
    dev1 = make_test_device(serial_number=None)
    assert dev1.device_hash is not None
    assert len(dev1.device_hash) == 16


def test_multiple_identical_devices_connected():
    dev_port1 = make_test_device(instance_id="USB\\VID_0951&PID_1666\\PORT_1")
    dev_port2 = make_test_device(instance_id="USB\\VID_0951&PID_1666\\PORT_2")
    assert dev_port1.device_hash != dev_port2.device_hash


# ============================================================================
# Test 10: Enumeration Exception (Never counts as empty, never recovers)
# ============================================================================

def test_enumeration_exception_preserves_state(tmp_env):
    """COM/WMI exception must not be treated as empty or trigger recovery."""
    dev = make_test_device()
    # Cycle 1: Confirmed incident
    scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=lambda: ([dev], True),
    )
    scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=lambda: ([dev], True),
    )
    state_before = load_device_state(tmp_env["state_file"])
    assert dev.device_hash in state_before["active_incidents"]

    # Cycle 3: Enumeration throws/fails
    issues, recoveries = scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=lambda: ([], False),
    )
    assert issues == []
    assert recoveries == []  # Must NOT recover because enumeration failed!

    state_after = load_device_state(tmp_env["state_file"])
    assert dev.device_hash in state_after["active_incidents"]


# ============================================================================
# Test 11: Corrupted Whitelist (Fails closed)
# ============================================================================

def test_corrupted_whitelist_fails_closed(tmp_env):
    with open(tmp_env["whitelist_file"], "w") as f:
        f.write("{ INVALID JSON NOT DICT }}}")

    whitelist = load_device_whitelist(tmp_env["whitelist_file"])
    assert isinstance(whitelist, dict)
    assert whitelist["approved_devices"] == []

    dev = make_test_device()
    auth = evaluate_authorization(dev, whitelist)
    assert auth == AuthorizationState.UNAUTHORIZED


# ============================================================================
# Test 12: Unauthorized Device Present on First Launch (Never silently trusted)
# ============================================================================

def test_first_launch_does_not_auto_approve(tmp_env):
    """Critical Security Requirement: Devices present on startup are evaluated, not trusted."""
    unauthorized_usb = make_test_device(category=DeviceCategory.USB_STORAGE)
    mock_enum = lambda: ([unauthorized_usb], True)

    # First cycle
    issues1, _ = scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=mock_enum,
    )
    # Second cycle (debounce confirmed)
    issues2, _ = scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=mock_enum,
    )

    state = load_device_state(tmp_env["state_file"])
    assert state["first_run_completed"] is True
    assert unauthorized_usb.device_hash in state["active_incidents"]
    assert len(issues2) == 1
    assert issues2[0]["severity"] == "critical"
    assert "Unauthorized" in issues2[0]["title"]


# ============================================================================
# Test 13 & 14: Debounce & No Duplicate Incidents Across Repeated Scans
# ============================================================================

def test_debounce_and_no_duplicate_incidents(tmp_env):
    usb = make_test_device()
    mock_enum = lambda: ([usb], True)

    # Scan 1: Observed (Awaiting debounce count 1/2)
    issues_scan1, _ = scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=mock_enum,
    )
    assert len(issues_scan1) == 0

    # Scan 2: Confirmed (Sample count 2/2 -> emitted)
    issues_scan2, _ = scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=mock_enum,
    )
    assert len(issues_scan2) == 1

    # Scan 3: Still active; must NOT re-emit duplicate incident!
    issues_scan3, _ = scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=mock_enum,
    )
    assert len(issues_scan3) == 0


# ============================================================================
# Test 15 & 16: Confirmed Device Removal & No Recovery on Failed Scans
# ============================================================================

def test_confirmed_device_removal_lifecycle(tmp_env):
    usb = make_test_device()

    # 1. Confirm device
    scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=lambda: ([usb], True),
    )
    scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=lambda: ([usb], True),
    )

    # 2. Device missing scan 1 (confirming absence 1/2)
    _, rec1 = scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=lambda: ([], True),
    )
    assert len(rec1) == 0

    # 3. Device missing scan 2 (confirmed absence 2/2 -> recovered)
    _, rec2 = scan_and_evaluate_devices(
        state_file=tmp_env["state_file"],
        whitelist_file=tmp_env["whitelist_file"],
        enumerator=lambda: ([], True),
    )
    assert len(rec2) == 1
    assert rec2[0]["device_hash"] == usb.device_hash
    assert "Confirmed physical device disconnection" in rec2[0]["reason"]

    # Active incidents is now empty
    state = load_device_state(tmp_env["state_file"])
    assert usb.device_hash not in state["active_incidents"]
    assert usb.device_hash in state["recent_recoveries"]


# ============================================================================
# Test 17: Device Reconnection After Recovery (New incident generated)
# ============================================================================

def test_device_reconnection_after_recovery(tmp_env):
    usb = make_test_device()

    # Cycle A: Connect and confirm
    scan_and_evaluate_devices(state_file=tmp_env["state_file"], enumerator=lambda: ([usb], True))
    scan_and_evaluate_devices(state_file=tmp_env["state_file"], enumerator=lambda: ([usb], True))

    # Cycle B: Disconnect and confirm removal
    scan_and_evaluate_devices(state_file=tmp_env["state_file"], enumerator=lambda: ([], True))
    scan_and_evaluate_devices(state_file=tmp_env["state_file"], enumerator=lambda: ([], True))

    # Cycle C: Reconnect same device
    scan_and_evaluate_devices(state_file=tmp_env["state_file"], enumerator=lambda: ([usb], True))
    re_issues, _ = scan_and_evaluate_devices(state_file=tmp_env["state_file"], enumerator=lambda: ([usb], True))
    assert len(re_issues) == 1
    assert re_issues[0]["device_hash"] == usb.device_hash


# ============================================================================
# Test 18 & 19: Non-Windows Behavior & State Persistence
# ============================================================================

def test_non_windows_behavior(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    devs, ok = enumerate_windows_devices()
    assert devs == []
    assert ok is False


def test_build_device_issue_payload():
    usb = make_test_device()
    payload = build_device_issue_payload(
        device=usb,
        auth_state=AuthorizationState.UNAUTHORIZED,
        severity="critical",
        incident_id="inc123",
    )
    assert payload["issue_key"].startswith("unauthorized_device_")
    assert payload["severity"] == "critical"
    assert "Kingston DataTraveler 3.0" in payload["title"]
    assert "USB Mass Storage" in payload["description"]
    assert "VID_0951&PID_1666" in payload["description"]
