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

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import json
import os
import tempfile
import time
from typing import Any

try:
    import winreg
    HAVE_WINREG = True
except ImportError:
    winreg = None  # type: ignore
    HAVE_WINREG = False

from core.logger import logger
from paths import SOFTWARE_STATE_FILE


# ============================================================================
# Classification Categories & Registry Metadata Constants
# ============================================================================

class SoftwareClassification(str, Enum):
    USER_FACING = "user_facing"
    RUNTIME_DEPENDENCY = "runtime_dependency"
    SYSTEM_COMPONENT = "system_component"
    UPDATE = "update"
    INVALID = "invalid"


@dataclass
class RawSoftwareEntry:
    subkey_name: str
    registry_path: str
    architecture: str
    name: str | None
    version: str | None = None
    publisher: str | None = None
    install_date: str | None = None
    install_location: str | None = None
    system_component: int = 0
    parent_key_name: str | None = None
    release_type: str | None = None
    windows_installer: int = 0
    no_remove: int = 0
    no_display: int = 0
    uninstall_string: str | None = None
    quiet_uninstall_string: str | None = None


KNOWN_UPDATE_RELEASE_TYPES = {
    "hotfix",
    "update",
    "security update",
    "securityupdate",
    "servicepack",
    "service pack",
    "update rollup",
    "updaterollup",
    "critical update",
    "criticalupdate",
    "definition update",
}

# Sub-feature MSI fragments that accompany a parent suite when SystemComponent == 1
KNOWN_SUBFEATURE_FRAGMENT_PATTERNS = (
    "pip bootstrap",
    "test suite",
    "development libraries",
    "standard library",
    "tcl/tk support",
    "utility scripts",
    "documentation",
    "add to path",
    "minimum runtime",
    "additional runtime",
    "debug runtime",
    "setup configuration",
    "setup wmi provider",
    "extensibility component",
    "click-to-run extensibility",
    "app driver settings",
    "messagebus",
    "telemetry client",
    "watchdog plugin",
    "install application",
    "winrt intellisense",
    "supportedapilist",
)

# Known standalone developer/runtime platforms that may have SystemComponent=1
# but should be retained as runtime dependencies if no parent exists
KNOWN_STANDALONE_RUNTIMES = (
    "windows subsystem for linux",
    "wsl",
)


# ============================================================================
# Robust Value Extraction & Normalization
# ============================================================================

def _normalize_text(text: Any) -> str:
    """Strip non-printable characters and collapse multiple internal whitespaces."""
    if text is None:
        return ""
    s = str(text).replace("\x00", " ")
    clean = "".join(ch for ch in s if ch.isprintable())
    return " ".join(clean.split())


def _format_install_date(raw_date: Any) -> str:
    """Convert Windows registry install date from YYYYMMDD into YYYY-MM-DD."""
    if not raw_date:
        return "Unknown"
    s = _normalize_text(raw_date)
    if not s or s.lower() in ("unknown", "none"):
        return "Unknown"
    try:
        return datetime.strptime(s, "%Y%m%d").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    try:
        clean_d = s.replace("/", "-")
        return datetime.strptime(clean_d, "%Y-%m-%d").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    return s[:20]


def _read_raw_value(registry_key, value_name: str) -> tuple[Any, int] | tuple[None, None]:
    """Safely query a Windows registry value returning (value, type)."""
    if not HAVE_WINREG or winreg is None or registry_key is None:
        return None, None
    try:
        val, val_type = winreg.QueryValueEx(registry_key, value_name)
        return val, val_type
    except (FileNotFoundError, OSError):
        return None, None


def _read_value(registry_key, value_name: str, default: Any = "Unknown") -> Any:
    """Safely read one Windows registry value (backward-compatible signature)."""
    val, _ = _read_raw_value(registry_key, value_name)
    if val is None:
        return default
    return val


def _read_str_value(registry_key, value_name: str, default: str | None = None) -> str | None:
    """Safely read and normalize a string registry value."""
    val, _ = _read_raw_value(registry_key, value_name)
    if val is None:
        return default
    cleaned = _normalize_text(val)
    return cleaned if cleaned else default


def _read_int_value(registry_key, value_name: str, default: int = 0) -> int:
    """Safely read an integer or DWORD registry value."""
    val, _ = _read_raw_value(registry_key, value_name)
    if val is None:
        return default
    if isinstance(val, int):
        return val
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return default


def _extract_install_location(subkey) -> str | None:
    """Extract and sanitize install location, falling back to DisplayIcon folder."""
    raw_loc = _read_str_value(subkey, "InstallLocation", None)
    if raw_loc:
        clean_loc = raw_loc.strip('"').rstrip("\\/")
        if clean_loc:
            return (clean_loc + "\\")[:500]

    raw_icon = _read_str_value(subkey, "DisplayIcon", None)
    if raw_icon and ("\\" in raw_icon or "/" in raw_icon):
        clean_icon = raw_icon.split(",")[0].strip('"').strip()
        dir_name = os.path.dirname(clean_icon).rstrip("\\/")
        if dir_name:
            return (dir_name + "\\")[:500]

    return None


# ============================================================================
# Entry Classification & Filtering Logic
# ============================================================================

def classify_software_entry(
    entry: RawSoftwareEntry | dict,
    known_parent_keys: set[str] | None = None,
) -> SoftwareClassification:
    """
    Classify a discovered software entry using conservative metadata signals.

    Categories:
    - INVALID: Missing or whitespace-only name, corrupted data.
    - UPDATE: Hotfixes, KB updates, security rollups (identified via ReleaseType).
    - SYSTEM_COMPONENT: Subordinate features with ParentKeyName or internal hidden MSI components.
    - RUNTIME_DEPENDENCY: Runtimes, compilers, frameworks, SDKs, drivers, and databases.
    - USER_FACING: Standard desktop and user applications.
    """
    if isinstance(entry, dict):
        raw = RawSoftwareEntry(
            subkey_name=str(entry.get("subkey_name") or ""),
            registry_path=str(entry.get("registry_path") or ""),
            architecture=str(entry.get("architecture") or "64-bit"),
            name=entry.get("name"),
            version=entry.get("version"),
            publisher=entry.get("publisher"),
            install_date=entry.get("install_date"),
            install_location=entry.get("install_location"),
            system_component=int(entry.get("system_component") or 0),
            parent_key_name=entry.get("parent_key_name"),
            release_type=entry.get("release_type"),
            windows_installer=int(entry.get("windows_installer") or 0),
            no_remove=int(entry.get("no_remove") or 0),
            no_display=int(entry.get("no_display") or 0),
            uninstall_string=entry.get("uninstall_string"),
            quiet_uninstall_string=entry.get("quiet_uninstall_string"),
        )
    else:
        raw = entry

    name = _normalize_text(raw.name)
    if not name:
        return SoftwareClassification.INVALID

    name_lower = name.lower()

    # 1. Explicit Windows Update / Hotfix Classification via ReleaseType
    if raw.release_type:
        clean_rel = _normalize_text(raw.release_type).lower()
        if clean_rel in KNOWN_UPDATE_RELEASE_TYPES:
            return SoftwareClassification.UPDATE

    # Check for direct KB package key names with update parent
    if raw.parent_key_name and (name_lower.startswith("kb") or "package_for_kb" in raw.subkey_name.lower()):
        return SoftwareClassification.UPDATE

    # 2. Subordinate Child Components via ParentKeyName
    if raw.parent_key_name:
        clean_parent = _normalize_text(raw.parent_key_name).lower()
        if known_parent_keys and clean_parent in known_parent_keys:
            return SoftwareClassification.SYSTEM_COMPONENT
        if raw.system_component == 1 or raw.no_display == 1:
            return SoftwareClassification.SYSTEM_COMPONENT

    # 3. Hidden System Components (SystemComponent == 1 or NoDisplay == 1)
    if raw.no_display == 1:
        return SoftwareClassification.SYSTEM_COMPONENT

    if raw.system_component == 1:
        # Check if it represents an independently useful standalone tool
        if any(sr in name_lower for sr in KNOWN_STANDALONE_RUNTIMES):
            return SoftwareClassification.RUNTIME_DEPENDENCY
        # Exclude known MSI subfeature fragments
        if any(pat in name_lower for pat in KNOWN_SUBFEATURE_FRAGMENT_PATTERNS):
            return SoftwareClassification.SYSTEM_COMPONENT
        if name_lower.startswith("vs_") or name_lower.startswith("icecap_") or ("nvidia " in name_lower and not raw.uninstall_string):
            return SoftwareClassification.SYSTEM_COMPONENT
        # If missing both install location and uninstall command, it is an internal registration helper
        if not raw.install_location and not raw.uninstall_string and not raw.quiet_uninstall_string:
            return SoftwareClassification.SYSTEM_COMPONENT

    # 4. Runtimes, Compilers, SDKs, and System Tools
    runtime_signals = (
        "runtime", "redistributable", "sdk", "framework", "python", "java", "jdk", "jre",
        "node.js", ".net", "dotnet", "postgresql", "mysql", "mongodb", "compiler",
        "driver package", "subsystem for linux", "git", "powershell", "openal"
    )
    if any(sig in name_lower for sig in runtime_signals):
        return SoftwareClassification.RUNTIME_DEPENDENCY

    return SoftwareClassification.USER_FACING


# ============================================================================
# Deterministic Deduplication & Conflict Resolution
# ============================================================================

def _record_quality(record: dict) -> int:
    """Calculate metadata richness score to resolve duplicate conflicts."""
    score = 0
    v = record.get("version")
    if v and str(v).lower() not in ("unknown", "none"):
        score += 3
    p = record.get("publisher")
    if p and str(p).lower() not in ("unknown", "none"):
        score += 2
    if record.get("install_location"):
        score += 4
    d = record.get("install_date")
    if d and str(d).lower() not in ("unknown", "none"):
        score += 1
    if record.get("architecture") == "64-bit":
        score += 1
    return score


def _merge_records(primary: dict, secondary: dict) -> dict:
    """Merge metadata from secondary into primary where primary has missing/Unknown values."""
    merged = dict(primary)
    for field in ("version", "publisher", "install_date"):
        val = merged.get(field)
        if not val or str(val).lower() in ("unknown", "none"):
            sec_val = secondary.get(field)
            if sec_val and str(sec_val).lower() not in ("unknown", "none"):
                merged[field] = sec_val
    if not merged.get("install_location") and secondary.get("install_location"):
        merged["install_location"] = secondary["install_location"]
    return merged


def deduplicate_software_records(records: list[dict]) -> list[dict]:
    """
    Deduplicate software records deterministically without merging distinct installations.

    Guarantees:
    - Conservative identity key: (name_norm, version_norm, arch_norm, location_norm).
    - Merges cross-hive duplicates of the same application when one record has richer metadata.
    - Preserves distinct versions, editions, architectures, and install paths.
    - Deterministic output ordering.
    """
    merged_map: dict[tuple, dict] = {}

    for record in records:
        name = record.get("name")
        if not name or not str(name).strip():
            continue

        name_norm = _normalize_text(name).casefold()
        ver = record.get("version")
        ver_norm = _normalize_text(ver).casefold() if ver and str(ver).lower() not in ("unknown", "none") else ""
        arch_norm = (record.get("architecture") or "").strip().lower()
        loc = record.get("install_location")
        loc_norm = loc.replace("/", "\\").rstrip("\\").casefold() if loc else ""

        full_key = (name_norm, ver_norm, arch_norm, loc_norm)

        cross_hive_key = (name_norm, ver_norm, loc_norm) if loc_norm else None

        existing_key = None
        if full_key in merged_map:
            existing_key = full_key
        elif cross_hive_key:
            for k in list(merged_map.keys()):
                if k[0] == name_norm and k[1] == ver_norm and k[3] == loc_norm:
                    existing_key = k
                    break

        if existing_key is not None:
            existing = merged_map[existing_key]
            if _record_quality(record) > _record_quality(existing):
                merged_map[existing_key] = _merge_records(record, existing)
            else:
                merged_map[existing_key] = _merge_records(existing, record)
        else:
            matched = False
            for k, existing in list(merged_map.items()):
                if k[0] == name_norm and k[1] == ver_norm:
                    p1 = str(record.get("publisher") or "").casefold()
                    p2 = str(existing.get("publisher") or "").casefold()
                    pubs_compatible = (p1 == p2) or (not p1 or p1 == "unknown") or (not p2 or p2 == "unknown")

                    if pubs_compatible and (not loc_norm or not k[3]):
                        if _record_quality(record) > _record_quality(existing):
                            del merged_map[k]
                            merged_map[full_key] = _merge_records(record, existing)
                        else:
                            merged_map[k] = _merge_records(existing, record)
                        matched = True
                        break

            if not matched:
                merged_map[full_key] = dict(record)

    deduped = list(merged_map.values())
    deduped.sort(
        key=lambda item: (
            (item.get("name") or "").casefold(),
            (item.get("version") or "").casefold(),
            (item.get("architecture") or "").casefold(),
            (item.get("install_location") or "").casefold(),
        )
    )
    return deduped


# ============================================================================
# Scanning Orchestration
# ============================================================================

def _scan_registry_path(
    registry_path: str,
    seen: set | None = None,
) -> list[dict]:
    """
    Scan one Windows uninstall registry path under HKEY_LOCAL_MACHINE.
    Returns cleaned, validated software dictionaries.
    Maintains backward compatibility with callers passing `seen`.
    """
    if not HAVE_WINREG or winreg is None:
        return []

    entries: list[dict] = []
    seen_set = seen if seen is not None else set()

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
                        raw_name = _read_value(subkey, "DisplayName", "")
                        name = _normalize_text(raw_name)
                        if not name:
                            continue

                        raw_ver = _read_value(subkey, "DisplayVersion", None)
                        version = _normalize_text(raw_ver)[:100] if raw_ver else "Unknown"

                        raw_pub = _read_value(subkey, "Publisher", None)
                        publisher = _normalize_text(raw_pub)[:255] if raw_pub else "Unknown"

                        raw_install_date = _read_value(subkey, "InstallDate", None)
                        install_date = _format_install_date(raw_install_date)
                        install_location = _extract_install_location(subkey)

                        architecture = "32-bit" if "WOW6432Node" in registry_path else "64-bit"

                        system_component = _read_int_value(subkey, "SystemComponent", 0)
                        parent_key_name = _read_str_value(subkey, "ParentKeyName", None)
                        release_type = _read_str_value(subkey, "ReleaseType", None)
                        no_display = _read_int_value(subkey, "NoDisplay", 0)
                        uninstall_str = _read_str_value(subkey, "UninstallString", None)
                        quiet_uninstall_str = _read_str_value(subkey, "QuietUninstallString", None)
                        windows_installer = _read_int_value(subkey, "WindowsInstaller", 0)
                        no_remove = _read_int_value(subkey, "NoRemove", 0)

                        raw_entry = RawSoftwareEntry(
                            subkey_name=subkey_name,
                            registry_path=registry_path,
                            architecture=architecture,
                            name=name[:255],
                            version=version,
                            publisher=publisher,
                            install_date=install_date,
                            install_location=install_location,
                            system_component=system_component,
                            parent_key_name=parent_key_name,
                            release_type=release_type,
                            windows_installer=windows_installer,
                            no_remove=no_remove,
                            no_display=no_display,
                            uninstall_string=uninstall_str,
                            quiet_uninstall_string=quiet_uninstall_str,
                        )

                        cls = classify_software_entry(raw_entry)
                        if cls in (SoftwareClassification.USER_FACING, SoftwareClassification.RUNTIME_DEPENDENCY):
                            record = {
                                "name": name[:255],
                                "version": version,
                                "publisher": publisher,
                                "install_date": install_date,
                                "install_location": install_location,
                                "architecture": architecture,
                            }
                            identity = (
                                name.casefold(),
                                version.casefold(),
                                architecture.casefold(),
                                (install_location or "").casefold(),
                            )
                            if identity not in seen_set:
                                seen_set.add(identity)
                                entries.append(record)
                except (OSError, ValueError, TypeError):
                    continue
                except Exception as e:
                    logger.debug(f"Error reading subkey in {registry_path}: {e}")
                    continue
    except (OSError, FileNotFoundError):
        pass
    except Exception as e:
        logger.warning(f"Error opening registry path {registry_path}: {e}")

    return entries


def get_installed_software(
    include_system_components: bool = False,
    include_updates: bool = False,
) -> list[dict]:
    """
    Collect installed Windows applications from HKLM 64-bit and 32-bit registry keys.
    Results are validated, filtered against internal sub-components, deduplicated,
    and deterministically sorted.

    Registry paths scanned:
    - SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall
    - SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall

    On non-Windows platforms where winreg is unavailable, returns an empty list.
    """
    if not HAVE_WINREG or winreg is None:
        return []

    registry_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]

    raw_entries: list[RawSoftwareEntry] = []
    known_parent_keys: set[str] = set()

    for registry_path in registry_paths:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as registry:
                subkey_count = winreg.QueryInfoKey(registry)[0]
                for index in range(subkey_count):
                    try:
                        subkey_name = winreg.EnumKey(registry, index)
                        known_parent_keys.add(subkey_name.lower())
                        architecture = "32-bit" if "WOW6432Node" in registry_path else "64-bit"

                        with winreg.OpenKey(registry, subkey_name) as subkey:
                            raw_name = _read_value(subkey, "DisplayName", "")
                            name = _normalize_text(raw_name)
                            if not name:
                                continue

                            raw_ver = _read_value(subkey, "DisplayVersion", None)
                            version = _normalize_text(raw_ver)[:100] if raw_ver else "Unknown"

                            raw_pub = _read_value(subkey, "Publisher", None)
                            publisher = _normalize_text(raw_pub)[:255] if raw_pub else "Unknown"

                            raw_install_date = _read_value(subkey, "InstallDate", None)
                            install_date = _format_install_date(raw_install_date)
                            install_location = _extract_install_location(subkey)

                            system_component = _read_int_value(subkey, "SystemComponent", 0)
                            parent_key_name = _read_str_value(subkey, "ParentKeyName", None)
                            release_type = _read_str_value(subkey, "ReleaseType", None)
                            no_display = _read_int_value(subkey, "NoDisplay", 0)
                            uninstall_str = _read_str_value(subkey, "UninstallString", None)
                            quiet_uninstall_str = _read_str_value(subkey, "QuietUninstallString", None)
                            windows_installer = _read_int_value(subkey, "WindowsInstaller", 0)
                            no_remove = _read_int_value(subkey, "NoRemove", 0)

                            raw_entries.append(
                                RawSoftwareEntry(
                                    subkey_name=subkey_name,
                                    registry_path=registry_path,
                                    architecture=architecture,
                                    name=name[:255],
                                    version=version,
                                    publisher=publisher,
                                    install_date=install_date,
                                    install_location=install_location,
                                    system_component=system_component,
                                    parent_key_name=parent_key_name,
                                    release_type=release_type,
                                    windows_installer=windows_installer,
                                    no_remove=no_remove,
                                    no_display=no_display,
                                    uninstall_string=uninstall_str,
                                    quiet_uninstall_string=quiet_uninstall_str,
                                )
                            )
                    except (OSError, ValueError, TypeError):
                        continue
                    except Exception as e:
                        logger.debug(f"Error enumerating subkey in {registry_path}: {e}")
                        continue
        except (OSError, FileNotFoundError):
            pass
        except Exception as e:
            logger.warning(f"Error accessing registry path {registry_path}: {e}")

    filtered_records: list[dict] = []
    for raw in raw_entries:
        cls = classify_software_entry(raw, known_parent_keys=known_parent_keys)

        should_include = False
        if cls in (SoftwareClassification.USER_FACING, SoftwareClassification.RUNTIME_DEPENDENCY):
            should_include = True
        elif cls == SoftwareClassification.SYSTEM_COMPONENT and include_system_components:
            should_include = True
        elif cls == SoftwareClassification.UPDATE and include_updates:
            should_include = True

        if should_include:
            filtered_records.append(
                {
                    "name": raw.name,
                    "version": raw.version or "Unknown",
                    "publisher": raw.publisher or "Unknown",
                    "install_date": raw.install_date or "Unknown",
                    "install_location": raw.install_location,
                    "architecture": raw.architecture,
                }
            )

    deduped = deduplicate_software_records(filtered_records)
    return deduped


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
                "install_location": str(item.get("install_location") or "").strip(),
                "architecture": str(item.get("architecture") or "").strip(),
            }
        )

    # Sort canonically by composite key
    canonical_items.sort(
        key=lambda x: (
            x["name"].casefold(),
            x["version"].casefold(),
            x["publisher"].casefold(),
            x["install_date"].casefold(),
            x["install_location"].casefold(),
            x["architecture"].casefold(),
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