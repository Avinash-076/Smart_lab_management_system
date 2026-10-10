"""
SLMS Client Agent Software Inventory Module.

Collects installed Windows applications from system uninstall registry keys:
- 64-bit: HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall
- 32-bit: HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall

E-06: Change Detection & Fingerprinting
Provides deterministic SHA-256 fingerprinting for inventory change detection,
preventing redundant uploads and outbox saturation.

E-07: Discovery Coverage Scope & Known Limitations
- Current Scope: System-wide applications installed with machine administrative
  rights via MSI, InstallShield, InnoSetup, NSIS, etc.
- Known Limitations:
  1. Per-User Applications: Software installed per-user under HKCU (e.g. user-mode
     VS Code or Chrome) is not visible from a Windows Service account without
     impersonating interactive user profiles.
  2. Windows Store / MSIX / AppX Packages: Modern packaged apps are not registered
     in standard Uninstall registry keys.
  3. Portable / Standalone Executables: Applications without installer registration
     do not generate registry entries.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
import tempfile
import time

try:
    import winreg
    HAVE_WINREG = True
except ImportError:
    winreg = None  # type: ignore
    HAVE_WINREG = False

from core.logger import logger
from paths import SOFTWARE_STATE_FILE


def _format_install_date(raw_date):
    """
    Convert Windows registry install date from YYYYMMDD into YYYY-MM-DD.
    """
    if not raw_date:
        return "Unknown"

    try:
        return datetime.strptime(
            str(raw_date),
            "%Y%m%d",
        ).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return str(raw_date)


def _read_value(
    registry_key,
    value_name,
    default="Unknown",
):
    """
    Safely read one Windows registry value.
    """
    if not HAVE_WINREG or winreg is None:
        return default

    try:
        value, _ = winreg.QueryValueEx(
            registry_key,
            value_name,
        )
        if value is None:
            return default
        return value
    except (
        FileNotFoundError,
        OSError,
    ):
        return default


def _scan_registry_path(
    registry_path: str,
    seen: set,
) -> list[dict]:
    """
    Scan one Windows uninstall registry path under HKEY_LOCAL_MACHINE.
    """
    if not HAVE_WINREG or winreg is None:
        return []

    software_list = []

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            registry_path,
        ) as registry:
            subkey_count = winreg.QueryInfoKey(registry)[0]

            for index in range(subkey_count):
                try:
                    subkey_name = winreg.EnumKey(registry, index)

                    with winreg.OpenKey(registry, subkey_name) as subkey:
                        name = _read_value(subkey, "DisplayName", "")
                        if not name:
                            continue

                        version = _read_value(subkey, "DisplayVersion")
                        publisher = _read_value(subkey, "Publisher")
                        raw_install_date = _read_value(subkey, "InstallDate", None)
                        install_date = _format_install_date(raw_install_date)

                        identity = (
                            str(name).strip().casefold(),
                            str(version).strip().casefold(),
                        )

                        if identity in seen:
                            continue

                        seen.add(identity)

                        software_list.append(
                            {
                                "name": str(name).strip(),
                                "version": str(version),
                                "publisher": str(publisher),
                                "install_date": install_date,
                            }
                        )

                except (OSError, ValueError, TypeError):
                    continue
                except Exception:
                    continue

    except (OSError, FileNotFoundError):
        pass
    except Exception:
        pass

    return software_list


def get_installed_software() -> list[dict]:
    """
    Collect installed Windows applications from HKLM 64-bit and 32-bit registry keys.
    Results are deduplicated and deterministically sorted by name.
    On non-Windows platforms where winreg is unavailable, returns an empty list.
    """
    if not HAVE_WINREG or winreg is None:
        return []

    software_list = []
    seen: set = set()

    registry_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]

    for registry_path in registry_paths:
        software_list.extend(
            _scan_registry_path(
                registry_path,
                seen,
            )
        )

    software_list.sort(
        key=lambda item: item["name"].casefold()
    )

    return software_list


# ============================================================================
# Software Fingerprinting & Change Detection (E-06)
# ============================================================================

def compute_software_fingerprint(software_list: list[dict]) -> str:
    """
    Compute a deterministic SHA-256 fingerprint for installed software inventory (E-06).

    Guarantees:
    - Normalizes field values and strips leading/trailing whitespace.
    - Sorts items canonically by (name, version, publisher, install_date) case-insensitively,
      ensuring that reordered but equivalent inventories produce the exact same fingerprint.
    - Deterministically handles empty inventory ([]).
    """
    if not software_list:
        return hashlib.sha256(b"[]").hexdigest()

    canonical_items: list[dict[str, str]] = []
    for item in software_list:
        if not isinstance(item, dict):
            continue
        canonical_items.append(
            {
                "name": str(item.get("name") or "").strip(),
                "version": str(item.get("version") or "").strip(),
                "publisher": str(item.get("publisher") or "").strip(),
                "install_date": str(item.get("install_date") or "").strip(),
            }
        )

    # Sort canonically by composite key
    canonical_items.sort(
        key=lambda x: (
            x["name"].casefold(),
            x["version"].casefold(),
            x["publisher"].casefold(),
            x["install_date"].casefold(),
        )
    )

    canonical_json = json.dumps(canonical_items, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def load_software_state(state_file: str | None = None) -> dict:
    """
    Load persisted software state (last delivered fingerprint, last enqueued fingerprint).
    Returns a default dictionary if the file is missing or corrupted.
    """
    filepath = state_file or SOFTWARE_STATE_FILE
    default_state = {
        "last_delivered_fingerprint": None,
        "last_enqueued_fingerprint": None,
        "last_delivery_time": None,
        "last_scan_time": None,
        "last_fingerprint": None,
        "last_upload_time": None,
    }

    if not os.path.exists(filepath):
        return default_state

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                delivered = data.get("last_delivered_fingerprint") or data.get("last_fingerprint")
                return {
                    "last_delivered_fingerprint": delivered,
                    "last_enqueued_fingerprint": data.get("last_enqueued_fingerprint"),
                    "last_delivery_time": data.get("last_delivery_time") or data.get("last_upload_time"),
                    "last_scan_time": data.get("last_scan_time"),
                    "last_fingerprint": delivered,
                    "last_upload_time": data.get("last_delivery_time") or data.get("last_upload_time"),
                }
    except (json.JSONDecodeError, OSError, ValueError, TypeError) as e:
        logger.warning(f"Corrupted or unreadable software state file '{filepath}' ({e}); resetting state.")

    return default_state


def save_software_state(state: dict, state_file: str | None = None) -> None:
    """
    Atomically save software state to disk using tempfile + os.replace (E-06).
    Guarantees no partial or corrupted file can remain on disk upon crash.
    """
    filepath = state_file or SOFTWARE_STATE_FILE
    target_dir = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(target_dir, exist_ok=True)

    delivered = state.get("last_delivered_fingerprint") or state.get("last_fingerprint")
    normalized_state = {
        "last_delivered_fingerprint": delivered,
        "last_enqueued_fingerprint": state.get("last_enqueued_fingerprint"),
        "last_delivery_time": state.get("last_delivery_time") or state.get("last_upload_time"),
        "last_scan_time": state.get("last_scan_time"),
        "last_fingerprint": delivered,
        "last_upload_time": state.get("last_delivery_time") or state.get("last_upload_time"),
    }

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=target_dir, delete=False, encoding="utf-8") as tf:
            temp_path = tf.name
            json.dump(normalized_state, tf, indent=2)
            tf.flush()
            os.fsync(tf.fileno())

        os.replace(temp_path, filepath)
    except Exception as e:
        logger.exception(f"Failed to atomically persist software state to '{filepath}': {e}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def record_software_enqueued(fingerprint: str, state_file: str | None = None) -> None:
    """Record that an inventory with this fingerprint was placed into the outbox."""
    state = load_software_state(state_file)
    state["last_enqueued_fingerprint"] = fingerprint
    save_software_state(state, state_file)


def record_software_delivered(fingerprint: str, state_file: str | None = None) -> None:
    """Record that an inventory with this fingerprint was successfully acknowledged/delivered."""
    state = load_software_state(state_file)
    state["last_delivered_fingerprint"] = fingerprint
    state["last_fingerprint"] = fingerprint
    state["last_delivery_time"] = time.time()
    state["last_upload_time"] = time.time()
    save_software_state(state, state_file)