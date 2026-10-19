"""
SLMS Client Agent - Device Discovery & Authorization Monitor.

Monitors connected USB and PnP devices on Windows workstations, enforces an
explicit authorization model (APPROVED, PENDING_APPROVAL, UNAUTHORIZED, UNKNOWN),
classifies operational/security risks, and generates debounced incident/recovery
events for integration with the SLMS Issue Management subsystem.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
import os
import re
import sys
import tempfile
import time
from typing import Any, Callable

try:
    from config import (
        ALERT_ON_UNKNOWN_PERIPHERAL,
        ALERT_ON_USB_NETWORK,
        ALERT_ON_USB_STORAGE,
        DEVICE_DEBOUNCE_CYCLES,
        ENABLE_DEVICE_MONITOR,
    )
except Exception:
    ENABLE_DEVICE_MONITOR = True
    ALERT_ON_USB_STORAGE = True
    ALERT_ON_USB_NETWORK = True
    ALERT_ON_UNKNOWN_PERIPHERAL = False
    DEVICE_DEBOUNCE_CYCLES = 2

try:
    from paths import DEVICE_STATE_FILE, DEVICE_WHITELIST_FILE
except Exception:
    DEVICE_STATE_FILE = "device_state.json"
    DEVICE_WHITELIST_FILE = "device_whitelist.json"

logger = logging.getLogger("slms_device_monitor")


def _utc_now() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# Enums & Data Models
# ============================================================================

class DeviceCategory(str, Enum):
    USB_STORAGE = "usb_storage"          # Flash drives, external hard drives, SD card readers
    USB_NETWORK = "usb_network"          # USB Wi-Fi dongles, Ethernet adapters, cellular modems
    USB_PHONE = "usb_phone"              # Phones exposing MTP/PTP/WPD interfaces
    USB_HID = "usb_hid"                  # Keyboards, mice, barcode scanners, input devices
    USB_AUDIO_VIDEO = "usb_audio_video"  # Webcams, headsets, microphones
    USB_OTHER = "usb_other"              # Other USB peripherals (serial, vendor-specific)
    UNKNOWN = "unknown"


class AuthorizationState(str, Enum):
    APPROVED = "APPROVED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNKNOWN = "UNKNOWN"


class DeviceLifecycleState(str, Enum):
    OBSERVED = "OBSERVED"
    CONFIRMED = "CONFIRMED"              # Debounce confirmed; incident active
    RECOVERED = "RECOVERED"              # Device absence confirmed; incident recovered
    DISMISSED = "DISMISSED"


@dataclass
class NormalizedDevice:
    """Canonical normalized representation of an endpoint-observed device."""
    instance_id: str
    name: str
    category: DeviceCategory
    device_class: str
    hardware_ids: list[str] = field(default_factory=list)
    vendor_id: str | None = None
    product_id: str | None = None
    manufacturer: str | None = None
    serial_number: str | None = None
    present: bool = True
    enumeration_source: str = "wmi_com"
    confidence: str = "high"
    first_observed: str = field(default_factory=_utc_now)
    last_observed: str = field(default_factory=_utc_now)

    @property
    def device_hash(self) -> str:
        """Deterministic, compact identifier for outbox keys and deduplication."""
        base = self.instance_id.strip().upper() if self.instance_id else ""
        if not base and self.hardware_ids:
            base = self.hardware_ids[0].strip().upper()
        if not base:
            base = f"{self.name}_{self.vendor_id}_{self.product_id}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        data["device_hash"] = self.device_hash
        return data


# ============================================================================
# Device Classification Helpers
# ============================================================================

_STORAGE_CLASSES = {"DISKDRIVE", "CDROM", "STORAGE", "SCSIADAPTER", "USBSTOR"}
_NETWORK_CLASSES = {"NET"}
_HID_CLASSES = {"HIDCLASS", "KEYBOARD", "MOUSE"}
_AV_CLASSES = {"CAMERA", "IMAGE", "MEDIA", "AUDIOENDPOINT"}
_WPD_CLASSES = {"WPD", "PORTABLEDEVICE"}


def classify_device(
    pnp_class: str | None,
    service: str | None,
    device_id: str,
    name: str | None = None,
) -> DeviceCategory:
    """
    Classify a Windows PnP device into operational risk categories based on
    PnP class, service driver, device ID path, and friendly name.
    """
    pnp_upper = (pnp_class or "").strip().upper()
    svc_upper = (service or "").strip().upper()
    dev_upper = device_id.strip().upper()
    name_upper = (name or "").strip().upper()

    # 1. Portable Devices (Phones, MTP, PTP media players)
    if pnp_upper in _WPD_CLASSES or "WPDBUSENUM" in dev_upper:
        return DeviceCategory.USB_PHONE

    # 2. USB Storage (Highest Security Sensitivity)
    if (
        svc_upper == "USBSTOR"
        or "USBSTOR" in dev_upper
        or (pnp_upper in _STORAGE_CLASSES and "USB" in dev_upper)
        or "UASPSTOR" in svc_upper
        or "FLASH DISK" in name_upper
        or "MASS STORAGE" in name_upper
    ):
        return DeviceCategory.USB_STORAGE

    # 3. USB Network Adapters (Firewall / Proxy bypass risk)
    if pnp_upper in _NETWORK_CLASSES:
        if "USB" in dev_upper or "WIRELESS" in name_upper or "WLAN" in name_upper:
            return DeviceCategory.USB_NETWORK

    # 4. Input devices (Keyboards, Mice, Barcode Scanners)
    if pnp_upper in _HID_CLASSES or "HID" in dev_upper:
        return DeviceCategory.USB_HID

    # 5. Audio / Video (Webcams, Microphones, Headsets)
    if pnp_upper in _AV_CLASSES or "CAMERA" in name_upper or "WEBCAM" in name_upper:
        return DeviceCategory.USB_AUDIO_VIDEO

    # 6. Generic or other USB peripheral
    if dev_upper.startswith("USB") or "USB" in dev_upper:
        return DeviceCategory.USB_OTHER

    return DeviceCategory.UNKNOWN


def extract_vid_pid(text: str) -> tuple[str | None, str | None]:
    """Extract 4-hex-digit Vendor ID (VID) and Product ID (PID) from hardware identifier."""
    if not text:
        return None, None
    vid_match = re.search(r"VID_([0-9A-Fa-f]{4})", text)
    pid_match = re.search(r"PID_([0-9A-Fa-f]{4})", text)
    vid = vid_match.group(1).upper() if vid_match else None
    pid = pid_match.group(1).upper() if pid_match else None
    return vid, pid


# ============================================================================
# Device Whitelist & Policy Management (Phase 2)
# ============================================================================

def _get_default_whitelist() -> dict[str, Any]:
    """Default restrictive whitelist schema."""
    return {
        "version": 1,
        "updated_at": _utc_now(),
        "approved_devices": [],          # List of approved instance_id or device_hash strings
        "approved_vid_pids": [],         # List of approved "VID_XXXX&PID_YYYY" pairs
        "approved_categories": [],       # By default EMPTY; no broad blanket approvals
        "notes": "SLMS Device Authorization Whitelist",
    }


def load_device_whitelist(whitelist_file: str | None = None) -> dict[str, Any]:
    """
    Load device whitelist from JSON file safely.
    Fails closed: if missing, corrupted, or unreadable, returns an empty restrictive policy.
    """
    target = whitelist_file or DEVICE_WHITELIST_FILE
    if not os.path.exists(target):
        return _get_default_whitelist()

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                logger.warning(f"Corrupted device whitelist in {target} (not a dict). Failing closed.")
                return _get_default_whitelist()
            data.setdefault("approved_devices", [])
            data.setdefault("approved_vid_pids", [])
            data.setdefault("approved_categories", [])
            return data
    except Exception as e:
        logger.warning(f"Failed to load device whitelist from {target}: {e}. Failing closed.")
        return _get_default_whitelist()


def save_device_whitelist(whitelist: dict[str, Any], whitelist_file: str | None = None) -> None:
    """Save device whitelist using atomic file replacement."""
    target = whitelist_file or DEVICE_WHITELIST_FILE
    target_dir = os.path.dirname(target)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    whitelist["updated_at"] = _utc_now()
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(
            prefix="whitelist_",
            suffix=".tmp",
            dir=target_dir or ".",
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(whitelist, f, indent=2)
        os.replace(temp_path, target)
    except Exception as e:
        logger.error(f"Failed to atomically persist device whitelist to {target}: {e}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def evaluate_authorization(
    device: NormalizedDevice,
    whitelist: dict[str, Any],
) -> AuthorizationState:
    """
    Evaluate device authorization against explicit whitelist rules.
    Security Invariant: Devices are never automatically approved without explicit policy match.
    """
    # 1. Exact instance ID or hash match
    approved_devices = {str(d).strip().upper() for d in whitelist.get("approved_devices", [])}
    if (
        device.instance_id.strip().upper() in approved_devices
        or device.device_hash.upper() in approved_devices
    ):
        return AuthorizationState.APPROVED

    # 2. Specific approved VID & PID pair (narrow hardware rule)
    if device.vendor_id and device.product_id:
        vid_pid = f"VID_{device.vendor_id}&PID_{device.product_id}".upper()
        approved_vid_pids = {str(vp).strip().upper() for vp in whitelist.get("approved_vid_pids", [])}
        if vid_pid in approved_vid_pids:
            return AuthorizationState.APPROVED

    # 3. Explicitly approved categories (e.g. standard approved lab mice/keyboards policy)
    approved_cats = {str(c).strip().lower() for c in whitelist.get("approved_categories", [])}
    if device.category.value in approved_cats:
        return AuthorizationState.APPROVED

    # 4. Prohibited categories default to UNAUTHORIZED
    if device.category in (DeviceCategory.USB_STORAGE, DeviceCategory.USB_NETWORK, DeviceCategory.USB_PHONE):
        return AuthorizationState.UNAUTHORIZED

    # 5. Other unapproved peripherals require administrative review
    return AuthorizationState.PENDING_APPROVAL


# ============================================================================
# Risk Severity Mapping (Phase 3.1)
# ============================================================================

def determine_incident_severity(
    category: DeviceCategory,
    auth_state: AuthorizationState,
) -> str | None:
    """
    Determine incident severity based on device risk classification and authorization state.
    Returns None if no incident is warranted (e.g. APPROVED devices).
    """
    if auth_state == AuthorizationState.APPROVED:
        return None

    if category == DeviceCategory.USB_STORAGE:
        # High security breach risk: unauthorized external storage
        return "critical" if ALERT_ON_USB_STORAGE else "high"

    if category == DeviceCategory.USB_NETWORK:
        # Network segmentation / tethering breach risk
        return "high" if ALERT_ON_USB_NETWORK else "medium"

    if category == DeviceCategory.USB_PHONE:
        # Phone MTP file transfer risk
        return "high"

    if category in (DeviceCategory.USB_HID, DeviceCategory.USB_AUDIO_VIDEO, DeviceCategory.USB_OTHER):
        return "medium" if ALERT_ON_UNKNOWN_PERIPHERAL else None

    return "medium"



# ============================================================================
# Device Deduplication & Filtering Helpers
# ============================================================================

def is_device_internal(instance_id: str) -> bool:
    """
    Check if a device is physically fixed/internal to the system chassis.
    In Windows, devices soldered to the motherboard or integrated into the laptop
    (built-in Bluetooth, internal keyboard/trackpad, internal webcam) have the
    CM_DEVCAP_REMOVABLE flag (0x04) cleared in their registry Capabilities.
    """
    if sys.platform != "win32" or not instance_id:
        return False
    try:
        import winreg
        key_path = r"SYSTEM\CurrentControlSet\Enum\\" + instance_id.strip()
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
            caps, _ = winreg.QueryValueEx(k, "Capabilities")
            return not bool(caps & 0x04)
    except Exception:
        return False


def deduplicate_storage_devices(devices: list[NormalizedDevice]) -> list[NormalizedDevice]:
    """
    Deduplicate multi-node PnP entries for single physical USB storage devices.

    Windows PnP registers a bus parent ('USB Mass Storage Device'), a disk node
    ('Lexar USB Flash Drive USB Device'), and companion nodes for one physical drive.
    This collapses them into a single high-fidelity device entry with full VID/PID metadata.
    """
    storage_devices = [d for d in devices if d.category == DeviceCategory.USB_STORAGE]
    disk_drives = [
        d for d in storage_devices
        if d.name.upper() != "USB MASS STORAGE DEVICE"
    ]

    if not disk_drives:
        return devices

    generic_parents = [
        d for d in storage_devices
        if d.name.upper() == "USB MASS STORAGE DEVICE"
    ]

    for parent in generic_parents:
        parent_id = parent.instance_id.upper()
        parent_parts = parent_id.split("\\")
        parent_serial = parent_parts[-1] if len(parent_parts) > 2 else ""

        matched_disk = None
        for disk in disk_drives:
            if parent_serial and parent_serial in disk.instance_id.upper():
                matched_disk = disk
                break

        if not matched_disk and len(disk_drives) == 1:
            matched_disk = disk_drives[0]

        if matched_disk:
            if not matched_disk.vendor_id and parent.vendor_id:
                matched_disk.vendor_id = parent.vendor_id
            if not matched_disk.product_id and parent.product_id:
                matched_disk.product_id = parent.product_id
            if not matched_disk.serial_number and parent.serial_number:
                matched_disk.serial_number = parent.serial_number
            if parent.hardware_ids:
                for hid in parent.hardware_ids:
                    if hid not in matched_disk.hardware_ids:
                        matched_disk.hardware_ids.append(hid)

    generic_parent_hashes = {p.device_hash for p in generic_parents}
    return [d for d in devices if d.device_hash not in generic_parent_hashes]


# ============================================================================
# Windows Native Device Enumeration (Phase 1)
# ============================================================================

def enumerate_windows_devices() -> tuple[list[NormalizedDevice], bool]:
    """
    Enumerate connected devices on Windows using WMI Win32_PnPEntity and Win32_DiskDrive.
    Returns (devices_list, success_flag).

    IMPORTANT:
    - Never interpret an enumeration exception as an empty device inventory.
    - If COM fails or is unavailable, success_flag is False.
    - Non-Windows environments return ([], False) explicitly.
    """
    if sys.platform != "win32":
        logger.debug("Device enumeration skipped: non-Windows operating system.")
        return [], False

    devices: list[NormalizedDevice] = []
    co_initialized = False

    def _query_wmi() -> list[NormalizedDevice]:
        import win32com.client
        wmi = win32com.client.GetObject("winmgmts:\\\\.\\root\\cimv2")
        result: list[NormalizedDevice] = []
        now_utc = _utc_now()

        pnp_query = (
            "SELECT DeviceID, Name, Description, PNPClass, Service, Manufacturer, "
            "HardwareID, Present FROM Win32_PnPEntity WHERE Present = True"
        )
        pnp_entities = wmi.ExecQuery(pnp_query)
        for entity in pnp_entities:
            try:
                device_id = getattr(entity, "DeviceID", None) or ""
                if not device_id:
                    continue

                pnp_class = getattr(entity, "PNPClass", None) or ""
                service = getattr(entity, "Service", None) or ""
                name = getattr(entity, "Name", None) or getattr(entity, "Description", None) or "Unknown Device"
                manufacturer = getattr(entity, "Manufacturer", None)

                dev_upper = device_id.strip().upper()
                name_upper = str(name).strip().upper()
                pnp_upper = str(pnp_class).strip().upper()

                # Filter out volumes (file-system partition mounts, not physical devices)
                if pnp_upper == "VOLUME" or name_upper == "VOLUME" or "STORAGE\\VOLUME" in dev_upper:
                    continue

                # Filter out internal USB bus infrastructure, controllers, hubs, and composite containers
                if (
                    "ROOT_HUB" in dev_upper
                    or "HOST CONTROLLER" in name_upper
                    or name_upper in ("USB COMPOSITE DEVICE", "GENERIC USB HUB", "USB HUB", "USB ROOT HUB")
                    or "GENERIC USB HUB" in name_upper
                    or "ROOT HUB" in name_upper
                ):
                    continue

                # Filter out WPD mirror projections for USB storage disks
                if pnp_upper in _WPD_CLASSES or "WPDBUSENUM" in dev_upper:
                    if "USBSTOR" in dev_upper or "DISK" in dev_upper:
                        continue

                is_usb = dev_upper.startswith("USB") or "USB" in dev_upper
                is_usbstor = service.upper() == "USBSTOR" or "USBSTOR" in dev_upper
                is_portable = pnp_upper in _WPD_CLASSES or "WPD" in dev_upper
                is_disk = pnp_upper in _STORAGE_CLASSES and is_usb

                if not (is_usb or is_usbstor or is_portable or is_disk):
                    continue

                category = classify_device(
                    pnp_class=pnp_class,
                    service=service,
                    device_id=device_id,
                    name=name,
                )

                # Ignore standard peripherals (keyboards, mice, built-in webcams, bluetooth)
                # when peripheral alerting is disabled (default in lab environments).
                if category in (DeviceCategory.USB_HID, DeviceCategory.USB_AUDIO_VIDEO, DeviceCategory.USB_OTHER):
                    if not ALERT_ON_UNKNOWN_PERIPHERAL:
                        continue
                    # Even if peripheral alerting is enabled, skip physically internal non-removable hardware
                    if is_device_internal(device_id):
                        continue

                raw_hw_ids = getattr(entity, "HardwareID", None)
                hw_ids: list[str] = []
                if raw_hw_ids is not None:
                    if isinstance(raw_hw_ids, (list, tuple)):
                        hw_ids = [str(h) for h in raw_hw_ids]
                    else:
                        hw_ids = [str(raw_hw_ids)]

                vid, pid = extract_vid_pid(device_id)
                if not (vid and pid) and hw_ids:
                    for h in hw_ids:
                        v, p = extract_vid_pid(h)
                        if v and p:
                            vid, pid = v, p
                            break

                result.append(
                    NormalizedDevice(
                        instance_id=device_id,
                        name=str(name).strip(),
                        category=category,
                        device_class=str(pnp_class).strip(),
                        hardware_ids=hw_ids,
                        vendor_id=vid,
                        product_id=pid,
                        manufacturer=str(manufacturer).strip() if manufacturer else None,
                        present=True,
                        enumeration_source="wmi_com",
                        confidence="high",
                        first_observed=now_utc,
                        last_observed=now_utc,
                    )
                )
            except Exception as item_err:
                logger.debug(f"Error parsing PnP entity item: {item_err}")
                continue

        try:
            disk_query = "SELECT Model, InterfaceType, DeviceID, SerialNumber, Size FROM Win32_DiskDrive WHERE InterfaceType = 'USB'"
            usb_disks = wmi.ExecQuery(disk_query)
            for disk in usb_disks:
                d_id = getattr(disk, "DeviceID", None) or ""
                model = getattr(disk, "Model", None) or "External USB Drive"
                serial = getattr(disk, "SerialNumber", None)
                if not d_id:
                    continue

                if not any(d_id.upper() in d.instance_id.upper() or d.name == model for d in result):
                    result.append(
                        NormalizedDevice(
                            instance_id=d_id,
                            name=str(model).strip(),
                            category=DeviceCategory.USB_STORAGE,
                            device_class="DiskDrive",
                            serial_number=str(serial).strip() if serial else None,
                            present=True,
                            enumeration_source="wmi_disk_drive",
                            confidence="high",
                            first_observed=now_utc,
                            last_observed=now_utc,
                        )
                    )
        except Exception as disk_err:
            logger.debug(f"Non-critical error querying Win32_DiskDrive: {disk_err}")

        # Deduplicate intermediate USB storage nodes (e.g. parent USB Mass Storage Device vs disk)
        result = deduplicate_storage_devices(result)
        return result

    try:
        try:
            import pythoncom
            pythoncom.CoInitialize()
            co_initialized = True
        except Exception:
            pass

        devices = _query_wmi()
        return devices, True

    except Exception as exc:
        logger.error(f"Device enumeration failed via Windows WMI/COM: {exc}")
        return [], False
    finally:
        import gc
        gc.collect()
        if co_initialized:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass


# ============================================================================
# Persistent Device Tracking State (Phase 3.3, 3.4)
# ============================================================================

def _get_default_device_state() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": _utc_now(),
        "first_run_completed": False,
        "active_incidents": {},     # device_hash -> incident dict
        "recent_recoveries": {},    # device_hash -> recovery dict
        "last_known_devices": {},   # device_hash -> device dict
    }


def load_device_state(state_file: str | None = None) -> dict[str, Any]:
    """Load persistent device tracking state from JSON file."""
    target = state_file or DEVICE_STATE_FILE
    if not os.path.exists(target):
        return _get_default_device_state()

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return _get_default_device_state()
            data.setdefault("version", 1)
            data.setdefault("first_run_completed", False)
            data.setdefault("active_incidents", {})
            data.setdefault("recent_recoveries", {})
            data.setdefault("last_known_devices", {})
            return data
    except Exception as e:
        logger.warning(f"Failed to load device state from {target}: {e}. Returning clean state.")
        return _get_default_device_state()


def save_device_state(state: dict[str, Any], state_file: str | None = None) -> None:
    """Persist device tracking state using atomic replacement."""
    target = state_file or DEVICE_STATE_FILE
    target_dir = os.path.dirname(target)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    state["updated_at"] = _utc_now()
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(
            prefix="device_state_",
            suffix=".tmp",
            dir=target_dir or ".",
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(temp_path, target)
    except Exception as e:
        logger.error(f"Failed to atomically persist device state to {target}: {e}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


# ============================================================================
# Device Monitoring & Issue Generation (Phases 3 & 4)
# ============================================================================

def build_device_issue_payload(
    device: NormalizedDevice,
    auth_state: AuthorizationState,
    severity: str,
    incident_id: str,
) -> dict[str, Any]:
    """
    Format a standardized diagnostic Issue payload for backend ingestion.
    """
    cat_label = {
        DeviceCategory.USB_STORAGE: "USB Mass Storage Device",
        DeviceCategory.USB_NETWORK: "USB Network Adapter",
        DeviceCategory.USB_PHONE: "USB Portable Phone / Media Device",
        DeviceCategory.USB_HID: "USB Input Device (Keyboard/Mouse)",
        DeviceCategory.USB_AUDIO_VIDEO: "USB Audio/Video Peripheral",
        DeviceCategory.USB_OTHER: "USB Peripheral",
    }.get(device.category, "Unknown External Device")

    title = f"Unauthorized {cat_label}: {device.name}"[:255]

    desc_lines = [
        f"An unauthorized or unapproved device was detected on this workstation.",
        "",
        f"• Device Name: {device.name}",
        f"• Category: {device.category.value} ({cat_label})",
        f"• Authorization Status: {auth_state.value}",
        f"• Device Instance ID: {device.instance_id}",
        f"• PnP Class: {device.device_class}",
    ]
    if device.vendor_id and device.product_id:
        desc_lines.append(f"• Hardware VID/PID: VID_{device.vendor_id}&PID_{device.product_id}")
    if device.manufacturer:
        desc_lines.append(f"• Manufacturer: {device.manufacturer}")
    if device.serial_number:
        desc_lines.append(f"• Serial Number: {device.serial_number}")

    desc_lines.extend([
        f"• First Observed: {device.first_observed}",
        f"• Last Observed: {device.last_observed}",
        f"• Detection Source: {device.enumeration_source} (Confidence: {device.confidence})",
    ])

    return {
        "issue_key": f"unauthorized_device_{device.device_hash}",
        "device_hash": device.device_hash,
        "incident_id": incident_id,
        "title": title,
        "description": "\n".join(desc_lines),
        "severity": severity,
        "category": device.category.value,
        "authorization_state": auth_state.value,
        "device_info": device.to_dict(),
    }


def scan_and_evaluate_devices(
    state_file: str | None = None,
    whitelist_file: str | None = None,
    enumerator: Callable[[], tuple[list[NormalizedDevice], bool]] = enumerate_windows_devices,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Execute device discovery, evaluate authorization, enforce debounce, and generate
    active issue payloads and recovery events.

    Returns:
        (emitted_issues, recovery_events)
        - emitted_issues: list of Issue dicts requiring outbox/backend submission.
        - recovery_events: list of recovery dicts for devices confirmed absent.

    Reliability Invariants:
    1. If enumeration fails (success_flag == False), NEVER clear incidents or mark recovered.
    2. Devices on first run are NEVER automatically approved (Phase 2.2).
    3. Consecutive debounce cycles require confirmed presence before emitting tickets.
    """
    if not ENABLE_DEVICE_MONITOR:
        return [], []

    devices, success = enumerator()
    if not success:
        # Enumeration failure: log warning, retain existing state, never trigger mass recovery
        logger.warning("Device scan could not complete successfully. Retaining existing device state.")
        return [], []

    state = load_device_state(state_file)
    whitelist = load_device_whitelist(whitelist_file)

    active_incidents: dict[str, Any] = state.get("active_incidents", {})
    recent_recoveries: dict[str, Any] = state.get("recent_recoveries", {})
    last_known: dict[str, Any] = state.get("last_known_devices", {})

    debounce_cycles = max(1, int(DEVICE_DEBOUNCE_CYCLES))
    now_utc = _utc_now()
    now_ts = time.time()

    emitted_issues: list[dict[str, Any]] = []
    recovery_events: list[dict[str, Any]] = []
    state_modified = False

    # Map current scan devices by hash
    current_device_map: dict[str, NormalizedDevice] = {d.device_hash: d for d in devices}

    # ------------------------------------------------------------------------
    # Step A: Evaluate Currently Connected Devices
    # ------------------------------------------------------------------------
    for dev_hash, device in current_device_map.items():
        # Update last known devices registry
        last_known[dev_hash] = device.to_dict()
        state_modified = True

        auth_state = evaluate_authorization(device, whitelist)
        severity = determine_incident_severity(device.category, auth_state)

        # If device is approved, no incident is warranted
        if auth_state == AuthorizationState.APPROVED or severity is None:
            # If there was an active incident for this device and it was later approved, resolve it
            if dev_hash in active_incidents:
                inc = active_incidents.pop(dev_hash)
                recovery_events.append({
                    "issue_key": inc["payload"]["issue_key"],
                    "incident_id": inc["incident_id"],
                    "device_hash": dev_hash,
                    "reason": "Device explicitly approved by administrative policy",
                    "recovered_at": now_utc,
                })
                state_modified = True
            continue

        # Device is UNAUTHORIZED or PENDING_APPROVAL with risk severity
        incident = active_incidents.get(dev_hash)

        if incident is None:
            # New observation: start debounce confirmation
            incident_id = hashlib.sha256(f"{dev_hash}_{now_ts}".encode("utf-8")).hexdigest()[:12]
            payload = build_device_issue_payload(device, auth_state, severity, incident_id)

            if debounce_cycles == 1:
                # Immediate confirmation
                active_incidents[dev_hash] = {
                    "incident_id": incident_id,
                    "device_hash": dev_hash,
                    "state": DeviceLifecycleState.CONFIRMED.value,
                    "consecutive_count": 1,
                    "missing_count": 0,
                    "first_observed": now_utc,
                    "last_observed": now_utc,
                    "payload": payload,
                    "emitted": True,
                }
                emitted_issues.append(payload)
                state_modified = True
                logger.warning(
                    f"Unauthorized device confirmed immediately: {device.name} (hash={dev_hash})"
                )
            else:
                # Cycle 1 of debounce
                active_incidents[dev_hash] = {
                    "incident_id": incident_id,
                    "device_hash": dev_hash,
                    "state": DeviceLifecycleState.OBSERVED.value,
                    "consecutive_count": 1,
                    "missing_count": 0,
                    "first_observed": now_utc,
                    "last_observed": now_utc,
                    "payload": payload,
                    "emitted": False,
                }
                state_modified = True
                logger.info(
                    f"Unauthorized device observed (sample 1/{debounce_cycles}): {device.name}. Awaiting debounce."
                )

        else:
            # Existing incident tracked
            incident["last_observed"] = now_utc
            incident["missing_count"] = 0  # Still present, reset missing counter
            curr_state = incident.get("state")

            if curr_state == DeviceLifecycleState.OBSERVED.value:
                count = incident.get("consecutive_count", 1) + 1
                incident["consecutive_count"] = count
                state_modified = True

                if count >= debounce_cycles:
                    # Debounce confirmed!
                    incident["state"] = DeviceLifecycleState.CONFIRMED.value
                    incident["emitted"] = True
                    payload = incident["payload"]
                    payload["description"] += f"\n• Debounce Confirmed: {count} consecutive cycles"
                    emitted_issues.append(payload)
                    logger.warning(
                        f"Unauthorized device debounce confirmed ({count}/{debounce_cycles}): "
                        f"{device.name} (incident_id={incident['incident_id']})"
                    )

            elif curr_state == DeviceLifecycleState.CONFIRMED.value:
                # Still confirmed and active; do not spam duplicate issue emissions
                incident["consecutive_count"] = incident.get("consecutive_count", 1) + 1
                state_modified = True

    # ------------------------------------------------------------------------
    # Step B: Detect Device Disconnection & Absence (Phase 3.4)
    # ------------------------------------------------------------------------
    active_hashes = list(active_incidents.keys())
    for dev_hash in active_hashes:
        if dev_hash not in current_device_map:
            # Device missing in this successful scan
            inc = active_incidents[dev_hash]
            missing_count = inc.get("missing_count", 0) + 1
            inc["missing_count"] = missing_count
            state_modified = True

            # Require debounce_cycles consecutive missing scans before confirming removal
            if missing_count >= debounce_cycles:
                logger.info(
                    f"Device confirmed disconnected after {missing_count} scans: "
                    f"hash={dev_hash} (incident_id={inc['incident_id']})"
                )
                active_incidents.pop(dev_hash)
                recovery_payload = {
                    "issue_key": inc["payload"]["issue_key"],
                    "incident_id": inc["incident_id"],
                    "device_hash": dev_hash,
                    "title": inc["payload"]["title"],
                    "recovered_at": now_utc,
                    "reason": "Confirmed physical device disconnection",
                }
                recent_recoveries[dev_hash] = recovery_payload
                recovery_events.append(recovery_payload)
            else:
                logger.debug(
                    f"Device absent on 1 scan (confirming absence {missing_count}/{debounce_cycles}): {dev_hash}"
                )

    state["first_run_completed"] = True
    state["active_incidents"] = active_incidents
    state["recent_recoveries"] = recent_recoveries
    state["last_known_devices"] = last_known

    if state_modified:
        save_device_state(state, state_file)

    return emitted_issues, recovery_events
