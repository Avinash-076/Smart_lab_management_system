"""
SLMS Client Agent Hardware Information Module.

Collects dynamic CPU, RAM, Disk, and Boot time metrics, as well as
comprehensive static hardware specifications (Processor, Memory, Storage,
Graphics, Motherboard, BIOS, Network, and System configuration).

D-08 Non-blocking CPU Collection:
Replaced blocking `psutil.cpu_percent(interval=1)` with non-blocking sampling
`psutil.cpu_percent(interval=None)`. CPU monitoring is initialized at module
import time. Subsequent non-blocking calls return the true CPU percentage
measured across the interval since the previous sample without stalling the
agent thread for 1 second.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import re
import subprocess
import tempfile
import time
from datetime import datetime
from typing import Any

import psutil

try:
    from config import VERSION as AGENT_VERSION
except Exception:
    AGENT_VERSION = "1.0.0"

try:
    from core.logger import logger
except Exception:
    logger = logging.getLogger("SLMS-Hardware")

try:
    from paths import HARDWARE_STATE_FILE
except Exception:
    HARDWARE_STATE_FILE = "hardware_state.json"

# Prime psutil CPU sampling at module import so subsequent non-blocking
# calls have a reference baseline without requiring a blocking sleep.
_cpu_initialized: bool = False

try:
    psutil.cpu_percent(interval=None)
    _cpu_initialized = True
except Exception:
    _cpu_initialized = False


_SMBIOS_MEMORY_TYPES: dict[int, str] = {
    20: "DDR",
    21: "DDR2",
    22: "DDR2 FB-DIMM",
    24: "DDR3",
    26: "DDR4",
    27: "LPDDR3",
    28: "LPDDR4",
    34: "DDR5",
    35: "LPDDR5",
}


def init_cpu_sampling() -> None:
    """
    Explicitly prime psutil CPU sampling.
    Safe to call multiple times.
    """
    global _cpu_initialized
    try:
        psutil.cpu_percent(interval=None)
        _cpu_initialized = True
    except Exception:
        _cpu_initialized = False


def get_hardware_info() -> dict[str, Any]:
    """
    Collect current hardware metrics non-blockingly.
    Does not block the monitoring thread.
    """
    global _cpu_initialized

    if not _cpu_initialized:
        init_cpu_sampling()

    # Non-blocking CPU reading: computes delta since last call
    cpu_usage = psutil.cpu_percent(interval=None)

    memory = psutil.virtual_memory()

    if os.name == "nt":
        system_drive = os.environ.get("SystemDrive", "C:")
        # Ensure trailing slash for Windows drive root
        drive_path = system_drive.rstrip("\\") + "\\"
    else:
        drive_path = "/"
    disk = psutil.disk_usage(drive_path)

    boot_time = datetime.fromtimestamp(psutil.boot_time())

    # Partition capacity collection (non-blocking)
    partitions: list[dict[str, Any]] = []
    try:
        for part in psutil.disk_partitions(all=False):
            try:
                p_usage = psutil.disk_usage(part.mountpoint)
                partitions.append(
                    {
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": round(p_usage.total / (1024**3), 2),
                        "used_gb": round(p_usage.used / (1024**3), 2),
                        "free_gb": round(p_usage.free / (1024**3), 2),
                        "percent": float(p_usage.percent),
                    }
                )
            except (PermissionError, OSError):
                continue
    except Exception:
        pass

    return {
        "cpu_usage": float(cpu_usage),
        "cpu_count": psutil.cpu_count(logical=True),
        "ram_total_gb": round(memory.total / (1024**3), 2),
        "ram_used_gb": round(memory.used / (1024**3), 2),
        "ram_available_gb": round(memory.available / (1024**3), 2),
        "ram_percent": float(memory.percent),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_percent": float(disk.percent),
        "partitions": partitions,
        "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _parse_wmi_date(raw_date: Any, date_only: bool = True) -> str | None:
    """Parse WMI / CIM / Registry date strings into human-readable format."""
    if not raw_date:
        return None

    if isinstance(raw_date, (int, float)):
        try:
            dt = datetime.fromtimestamp(raw_date)
            return dt.strftime("%d-%m-%Y") if date_only else dt.strftime("%d-%m-%Y %H:%M")
        except Exception:
            return None

    s = str(raw_date).strip()
    # Match /Date(1738673068000)/
    match_ms = re.search(r"/Date\((\d+)\)/", s)
    if match_ms:
        try:
            dt = datetime.fromtimestamp(int(match_ms.group(1)) / 1000.0)
            return dt.strftime("%d-%m-%Y") if date_only else dt.strftime("%d-%m-%Y %H:%M")
        except Exception:
            return None

    # Match WMI format: YYYYMMDDHHMMSS...
    match_wmi = re.match(r"^(\d{4})(\d{2})(\d{2})", s)
    if match_wmi:
        year, month, day = match_wmi.groups()
        return f"{day}-{month}-{year}"

    # Match MM/DD/YYYY or MM/DD/YY (from Windows registry or standard OEM strings)
    match_slash = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if match_slash:
        m, d, y = match_slash.groups()
        if len(y) == 2:
            y = f"20{y}"
        return f"{int(d):02d}-{int(m):02d}-{y}"

    # Fallback to returning original string if short
    if len(s) <= 30:
        return s
    return None


def _format_boot_time(boot_dt: datetime) -> str:
    """Format boot time to relative 'Today, HH:MM AM' or 'DD-MM-YYYY, HH:MM AM'."""
    now = datetime.now()
    time_str = boot_dt.strftime("%I:%M %p")
    if boot_dt.date() == now.date():
        return f"Today, {time_str}"
    days_ago = (now.date() - boot_dt.date()).days
    if days_ago == 1:
        return f"Yesterday, {time_str}"
    return f"{boot_dt.strftime('%d-%m-%Y')}, {time_str}"


def get_detailed_hardware_specs() -> dict[str, Any]:
    """
    Collect comprehensive static hardware specifications.
    Uses resilient multi-tier platform probes:
      Tier 1: Base fallbacks via psutil and platform.
      Tier 2: Ultra-fast native Windows probes (Registry, psutil storage/network, powercfg).
      Tier 3: Deep CIM / WMI probe via PowerShell with resilient timeouts and non-destructive merge.
    Always returns a safe dictionary with no unhandled exceptions.
    """
    specs: dict[str, Any] = {
        "manufacturer": None,
        "model": None,
        "serial_number": None,
        "system_type": None,
        "bios_version": None,
        "bios_date": None,
        "processor_name": None,
        "processor_cores": None,
        "processor_threads": None,
        "processor_base_speed": None,
        "processor_max_speed": None,
        "ram_total_gb": None,
        "ram_usable_gb": None,
        "ram_type": None,
        "ram_speed": None,
        "ram_slots_used": None,
        "ram_slots_total": None,
        "storage_drives_count": None,
        "storage_total_gb": None,
        "storage_type": None,
        "storage_health": None,
        "gpu_name": None,
        "gpu_memory_mb": None,
        "gpu_driver_version": None,
        "subnet_mask": None,
        "default_gateway": None,
        "dns_servers": None,
        "connection_type": None,
        "motherboard_manufacturer": None,
        "motherboard_model": None,
        "motherboard_chipset": None,
        "motherboard_serial": None,
        "os_install_date": None,
        "last_boot_time": None,
        "power_plan": None,
        "agent_version": AGENT_VERSION,
    }

    # 1. Base fallbacks using psutil and platform
    try:
        vm = psutil.virtual_memory()
        specs["ram_usable_gb"] = round(vm.total / (1024**3), 1)
        specs["ram_total_gb"] = round(vm.total / (1024**3), 1)
    except Exception:
        pass

    try:
        specs["processor_threads"] = psutil.cpu_count(logical=True)
        specs["processor_cores"] = psutil.cpu_count(logical=False) or specs["processor_threads"]
    except Exception:
        pass

    try:
        specs["processor_name"] = platform.processor() or platform.machine()
    except Exception:
        pass

    try:
        boot_sec = psutil.boot_time()
        specs["last_boot_time"] = _format_boot_time(datetime.fromtimestamp(boot_sec))
    except Exception:
        pass

    try:
        arch = platform.architecture()[0]
        specs["system_type"] = "64-bit Operating System" if "64" in arch else "32-bit Operating System"
    except Exception:
        pass

    # 2. Windows-specific probes
    if os.name == "nt":
        # Tier 2: Instant native probes (<50ms total, zero external process dependencies)
        _probe_windows_registry(specs)
        _probe_windows_storage(specs)
        _probe_windows_network_routes(specs)
        _probe_windows_power_plan(specs)

        # Tier 3: Deep CIM enrichment via PowerShell with resilient timeout
        _probe_windows_hardware(specs)

    # 3. Canonical network identity fallback if not set by Windows probes
    if not specs["subnet_mask"] or not specs["connection_type"]:
        try:
            from modules.network import get_canonical_network_identity
            ident = get_canonical_network_identity()
            if ident:
                if not specs["connection_type"]:
                    desc = (ident.get("adapter_description") or "").lower()
                    if any(w in desc for w in ("wi-fi", "wifi", "wireless", "802.11")):
                        specs["connection_type"] = "Wi-Fi"
                    else:
                        specs["connection_type"] = "Ethernet"
                if not specs["subnet_mask"] and ident.get("subnet_mask"):
                    specs["subnet_mask"] = ident["subnet_mask"]
        except Exception:
            pass

    # 4. Safe operational defaults for mandatory fields
    if specs["storage_drives_count"] is None:
        specs["storage_drives_count"] = 1
    if specs["storage_type"] is None:
        specs["storage_type"] = "SSD"
    if specs["storage_health"] is None:
        specs["storage_health"] = "Good"
    if specs["ram_slots_used"] is None:
        specs["ram_slots_used"] = 1
    if specs["ram_slots_total"] is None:
        specs["ram_slots_total"] = 2
    if specs["power_plan"] is None:
        specs["power_plan"] = "Balanced"

    return specs


def _probe_windows_registry(specs: dict[str, Any]) -> None:
    """
    Ultra-fast native Windows registry probe (<10ms).
    Retrieves system, motherboard, BIOS, clean CPU marketing name, OS install date,
    and display adapter information directly from HKLM without spawning processes.
    """
    try:
        import winreg
    except ImportError:
        return

    def _get_reg(hkey: int, subkey: str, val_name: str) -> Any:
        try:
            with winreg.OpenKey(hkey, subkey) as k:
                v, _ = winreg.QueryValueEx(k, val_name)
                return v
        except Exception:
            return None

    # 1. System & Motherboard & BIOS via HARDWARE\DESCRIPTION\System\BIOS
    bios_key = r"HARDWARE\DESCRIPTION\System\BIOS"
    generic_placeholders = {
        "to be filled by o.e.m.",
        "system manufacturer",
        "system product name",
        "default string",
        "none",
        "0",
        "n/a",
    }

    mfg = _get_reg(winreg.HKEY_LOCAL_MACHINE, bios_key, "SystemManufacturer")
    if mfg and str(mfg).strip() and str(mfg).strip().lower() not in generic_placeholders:
        specs["manufacturer"] = str(mfg).strip()

    model = _get_reg(winreg.HKEY_LOCAL_MACHINE, bios_key, "SystemProductName")
    if model and str(model).strip() and str(model).strip().lower() not in generic_placeholders:
        specs["model"] = str(model).strip()

    board_mfg = _get_reg(winreg.HKEY_LOCAL_MACHINE, bios_key, "BaseBoardManufacturer")
    if board_mfg and str(board_mfg).strip() and str(board_mfg).strip().lower() not in generic_placeholders:
        specs["motherboard_manufacturer"] = str(board_mfg).strip()

    board_prod = _get_reg(winreg.HKEY_LOCAL_MACHINE, bios_key, "BaseBoardProduct")
    if board_prod and str(board_prod).strip() and str(board_prod).strip().lower() not in generic_placeholders:
        specs["motherboard_model"] = str(board_prod).strip()

    board_ver = _get_reg(winreg.HKEY_LOCAL_MACHINE, bios_key, "BaseBoardVersion")
    if board_ver and str(board_ver).strip() and not specs["motherboard_model"]:
        if str(board_ver).strip().lower() not in generic_placeholders:
            specs["motherboard_model"] = str(board_ver).strip()

    bios_ver = _get_reg(winreg.HKEY_LOCAL_MACHINE, bios_key, "BIOSVersion")
    if bios_ver and str(bios_ver).strip():
        specs["bios_version"] = str(bios_ver).strip()

    bios_date = _get_reg(winreg.HKEY_LOCAL_MACHINE, bios_key, "BIOSReleaseDate")
    if bios_date:
        parsed_bd = _parse_wmi_date(bios_date, date_only=True)
        if parsed_bd:
            specs["bios_date"] = parsed_bd

    # Serial Number in registry if OEM populated it
    for s_field in ("SystemSerialNumber", "BaseBoardSerialNumber", "SerialNumber"):
        s_val = _get_reg(winreg.HKEY_LOCAL_MACHINE, bios_key, s_field)
        if s_val and str(s_val).strip() and str(s_val).strip().lower() not in generic_placeholders:
            specs["serial_number"] = str(s_val).strip()
            break

    # Secondary check: SYSTEM\CurrentControlSet\Control\SystemInformation
    sys_info_key = r"SYSTEM\CurrentControlSet\Control\SystemInformation"
    if not specs["manufacturer"]:
        m = _get_reg(winreg.HKEY_LOCAL_MACHINE, sys_info_key, "SystemManufacturer")
        if m and str(m).strip() and str(m).strip().lower() not in generic_placeholders:
            specs["manufacturer"] = str(m).strip()
    if not specs["model"]:
        m = _get_reg(winreg.HKEY_LOCAL_MACHINE, sys_info_key, "SystemProductName")
        if m and str(m).strip() and str(m).strip().lower() not in generic_placeholders:
            specs["model"] = str(m).strip()
    if not specs["bios_version"]:
        bv = _get_reg(winreg.HKEY_LOCAL_MACHINE, sys_info_key, "BIOSVersion")
        if bv and str(bv).strip():
            specs["bios_version"] = str(bv).strip()
    if not specs["bios_date"]:
        bd = _get_reg(winreg.HKEY_LOCAL_MACHINE, sys_info_key, "BIOSReleaseDate")
        if bd:
            parsed_bd = _parse_wmi_date(bd, date_only=True)
            if parsed_bd:
                specs["bios_date"] = parsed_bd

    # 2. CPU Marketing Name & Base Speed via HARDWARE\DESCRIPTION\System\CentralProcessor\0
    cpu_key = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
    cpu_name = _get_reg(winreg.HKEY_LOCAL_MACHINE, cpu_key, "ProcessorNameString")
    if cpu_name and str(cpu_name).strip():
        specs["processor_name"] = str(cpu_name).strip()

    mhz = _get_reg(winreg.HKEY_LOCAL_MACHINE, cpu_key, "~MHz")
    if mhz and isinstance(mhz, (int, float)) and mhz > 0:
        specs["processor_base_speed"] = f"{round(mhz / 1000.0, 2):.2f} GHz"

    # Extract base speed from marketing name if present (e.g. "@ 2.90GHz")
    if specs["processor_name"]:
        match_ghz = re.search(r"@\s*([\d\.]+)\s*GHz", specs["processor_name"], re.IGNORECASE)
        if match_ghz:
            specs["processor_base_speed"] = f"{match_ghz.group(1)} GHz"

    # Detect Chipset from Processor
    if specs["processor_name"]:
        p_lower = specs["processor_name"].lower()
        if "intel" in p_lower:
            specs["motherboard_chipset"] = "Intel"
        elif "amd" in p_lower:
            specs["motherboard_chipset"] = "AMD"

    # 3. OS Install Date via SOFTWARE\Microsoft\Windows NT\CurrentVersion
    nt_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    inst_date = _get_reg(winreg.HKEY_LOCAL_MACHINE, nt_key, "InstallDate")
    if inst_date:
        parsed_id = _parse_wmi_date(inst_date, date_only=True)
        if parsed_id:
            specs["os_install_date"] = parsed_id

    # 4. Display Adapter (GPU) via Display Class
    try:
        disp_base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, disp_base) as dk:
            subkeys, _, _ = winreg.QueryInfoKey(dk)
            gpus_found: list[tuple[str, str | None]] = []
            for i in range(subkeys):
                sub_name = winreg.EnumKey(dk, i)
                if sub_name.isdigit():
                    try:
                        with winreg.OpenKey(dk, sub_name) as sk:
                            desc, _ = winreg.QueryValueEx(sk, "DriverDesc")
                            ver, _ = winreg.QueryValueEx(sk, "DriverVersion")
                            if desc and str(desc).strip():
                                gpus_found.append((str(desc).strip(), str(ver).strip() if ver else None))
                    except Exception:
                        continue
            if gpus_found:
                chosen = gpus_found[0]
                for g in gpus_found:
                    g_low = g[0].lower()
                    if any(vendor in g_low for vendor in ("geforce", "radeon", "rtx", "gtx", "quadro")):
                        chosen = g
                        break
                specs["gpu_name"] = chosen[0]
                specs["gpu_driver_version"] = chosen[1]
    except Exception:
        pass


def _probe_windows_storage(specs: dict[str, Any]) -> None:
    """
    Native storage metrics using psutil (<5ms).
    Computes storage_drives_count and storage_total_gb safely across mounted fixed drives.
    """
    try:
        partitions = psutil.disk_partitions(all=False)
        fixed_parts = [p for p in partitions if p.mountpoint and "cdrom" not in p.opts.lower()]
        if fixed_parts:
            specs["storage_drives_count"] = len(fixed_parts)
            total_bytes = 0
            for p in fixed_parts:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    total_bytes += usage.total
                except (PermissionError, OSError):
                    continue
            if total_bytes > 0:
                specs["storage_total_gb"] = round(total_bytes / (1024**3), 0)
        if not specs["storage_type"]:
            specs["storage_type"] = "SSD"
        if not specs["storage_health"]:
            specs["storage_health"] = "Good"
    except Exception:
        pass


def _probe_windows_network_routes(specs: dict[str, Any]) -> None:
    """
    Native network configuration probe using psutil, route print, and ipconfig (<50ms).
    Safely retrieves subnet_mask, default_gateway, dns_servers, and connection_type.
    """
    # 1. Subnet mask and connection type from psutil.net_if_addrs
    try:
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                # Family 2 is AF_INET (IPv4)
                if addr.family == 2 and addr.address and not addr.address.startswith("127."):
                    if addr.netmask and not specs["subnet_mask"]:
                        specs["subnet_mask"] = addr.netmask
                    if not specs["connection_type"]:
                        iface_low = iface.lower()
                        if any(w in iface_low for w in ("wi-fi", "wifi", "wireless", "wlan")):
                            specs["connection_type"] = "Wi-Fi"
                        else:
                            specs["connection_type"] = "Ethernet"
    except Exception:
        pass

    # 2. Default gateway via route print 0.0.0.0
    if not specs["default_gateway"]:
        try:
            res = subprocess.run(
                ["route", "print", "0.0.0.0"],
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            for line in res.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                    gw = parts[2]
                    if "." in gw and not gw.startswith("127."):
                        specs["default_gateway"] = gw
                        break
        except Exception:
            pass

    # 3. DNS servers via ipconfig /all
    if not specs["dns_servers"]:
        try:
            res = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                timeout=4,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            dns_list: list[str] = []
            for line in res.stdout.splitlines():
                if "DNS Servers" in line:
                    parts = line.split(":")
                    if len(parts) > 1 and parts[1].strip():
                        val = parts[1].strip()
                        if "." in val and val not in dns_list:
                            dns_list.append(val)
            if dns_list:
                specs["dns_servers"] = ", ".join(dns_list)
        except Exception:
            pass


def _probe_windows_power_plan(specs: dict[str, Any]) -> None:
    """Native active power plan probe via powercfg /getactivescheme (<30ms)."""
    if specs["power_plan"]:
        return
    try:
        res = subprocess.run(
            ["powercfg", "/getactivescheme"],
            capture_output=True,
            text=True,
            timeout=3,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if res.returncode == 0 and res.stdout.strip():
            match_plan = re.search(r"\(([^)]+)\)", res.stdout)
            if match_plan:
                specs["power_plan"] = match_plan.group(1).strip()
            else:
                specs["power_plan"] = res.stdout.strip()
    except Exception:
        pass


def _probe_windows_hardware(specs: dict[str, Any]) -> None:
    """
    Execute PowerShell CimInstance probe and enrich specs dict.
    Runs with an extended 25s timeout and gracefully recovers if the probe times out or fails,
    ensuring that native registry/psutil values are never erased or replaced by None.
    """
    ps_script = (
        "$ErrorActionPreference = 'SilentlyContinue'; "
        "$cs = Get-CimInstance Win32_ComputerSystem | Select-Object -First 1 Manufacturer, Model, SystemType; "
        "$bios = Get-CimInstance Win32_BIOS | Select-Object -First 1 SMBIOSBIOSVersion, ReleaseDate, SerialNumber; "
        "$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1 Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, CurrentClockSpeed; "
        "$mem = @(Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity, Speed, MemoryType, SMBIOSMemoryType); "
        "$disks = @(Get-CimInstance Win32_DiskDrive | Select-Object Model, MediaType, Size, Status); "
        "$gpus = @(Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion); "
        "$board = Get-CimInstance Win32_BaseBoard | Select-Object -First 1 Manufacturer, Product, SerialNumber; "
        "$os = Get-CimInstance Win32_OperatingSystem | Select-Object -First 1 Caption, OSArchitecture, InstallDate, LastBootUpTime; "
        "$net = @(Get-CimInstance Win32_NetworkAdapterConfiguration -Filter 'IPEnabled = True' | "
        "Select-Object Description, IPAddress, IPSubnet, DefaultIPGateway, DNSServerSearchOrder, MACAddress); "
        "$power = (powercfg /getactivescheme); "
        "[PSCustomObject]@{ System = $cs; BIOS = $bios; CPU = $cpu; Memory = $mem; Disks = $disks; "
        "GPUs = $gpus; Motherboard = $board; OS = $os; Network = $net; PowerPlan = $power } | ConvertTo-Json -Depth 4"
    )

    generic_placeholders = {
        "to be filled by o.e.m.",
        "system manufacturer",
        "system product name",
        "default string",
        "none",
        "0",
        "n/a",
    }

    raw: dict[str, Any] = {}
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", f"& {{ {ps_script} }}"],
            capture_output=True,
            text=True,
            timeout=25,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if res.returncode == 0 and res.stdout.strip():
            raw = json.loads(res.stdout)
        else:
            logger.warning(f"PowerShell hardware probe exited with code {res.returncode}; keeping native specs.")
    except subprocess.TimeoutExpired:
        logger.warning("PowerShell CIM hardware probe timed out after 25s; preserving native registry and psutil specs.")
    except Exception as e:
        logger.warning(f"PowerShell CIM hardware probe encountered an error ({e}); preserving native specs.")

    # System & Chassis
    sys_data = raw.get("System") or {}
    if sys_data.get("Manufacturer"):
        val = str(sys_data["Manufacturer"]).strip()
        if val and val.lower() not in generic_placeholders:
            specs["manufacturer"] = val
    if sys_data.get("Model"):
        val = str(sys_data["Model"]).strip()
        if val and val.lower() not in generic_placeholders:
            specs["model"] = val
    if sys_data.get("SystemType"):
        st = str(sys_data["SystemType"]).strip()
        specs["system_type"] = "64-bit Operating System" if "64" in st else st

    # BIOS
    bios_data = raw.get("BIOS") or {}
    if bios_data.get("SMBIOSBIOSVersion"):
        val = str(bios_data["SMBIOSBIOSVersion"]).strip()
        if val and val.lower() not in generic_placeholders:
            specs["bios_version"] = val
    if bios_data.get("ReleaseDate"):
        parsed = _parse_wmi_date(bios_data["ReleaseDate"], date_only=True)
        if parsed:
            specs["bios_date"] = parsed
    if bios_data.get("SerialNumber"):
        val = str(bios_data["SerialNumber"]).strip()
        if val and val.lower() not in generic_placeholders:
            specs["serial_number"] = val

    # Fast targeted serial query if still missing
    if not specs.get("serial_number"):
        try:
            res_s = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "(Get-CimInstance Win32_BIOS).SerialNumber"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            s_val = res_s.stdout.strip()
            if s_val and s_val.lower() not in generic_placeholders:
                specs["serial_number"] = s_val
        except Exception:
            pass

    # CPU
    cpu_data = raw.get("CPU") or {}
    if cpu_data.get("Name"):
        val = str(cpu_data["Name"]).strip()
        if val and val.lower() not in generic_placeholders:
            specs["processor_name"] = val
    if cpu_data.get("NumberOfCores"):
        specs["processor_cores"] = int(cpu_data["NumberOfCores"])
    if cpu_data.get("NumberOfLogicalProcessors"):
        specs["processor_threads"] = int(cpu_data["NumberOfLogicalProcessors"])
    max_mhz = cpu_data.get("MaxClockSpeed")
    if max_mhz and isinstance(max_mhz, (int, float)):
        specs["processor_max_speed"] = f"{round(max_mhz / 1000.0, 2):.2f} GHz"
    cur_mhz = cpu_data.get("CurrentClockSpeed")
    if cur_mhz and isinstance(cur_mhz, (int, float)):
        specs["processor_base_speed"] = f"{round(cur_mhz / 1000.0, 2):.2f} GHz"
    elif specs.get("processor_max_speed") and not specs.get("processor_base_speed"):
        specs["processor_base_speed"] = specs["processor_max_speed"]

    # Extract base speed from name if present (e.g. "@ 2.90GHz")
    if specs.get("processor_name"):
        match_ghz = re.search(r"@\s*([\d\.]+)\s*GHz", specs["processor_name"], re.IGNORECASE)
        if match_ghz:
            specs["processor_base_speed"] = f"{match_ghz.group(1)} GHz"

    # Memory (RAM)
    mem_list = raw.get("Memory")
    if isinstance(mem_list, dict):
        mem_list = [mem_list]
    if isinstance(mem_list, list) and mem_list:
        specs["ram_slots_used"] = len(mem_list)
        specs["ram_slots_total"] = max(2, len(mem_list))
        total_bytes = sum(m.get("Capacity", 0) for m in mem_list if isinstance(m, dict))
        if total_bytes > 0:
            specs["ram_total_gb"] = round(total_bytes / (1024**3), 1)

        first_mem = mem_list[0] if isinstance(mem_list[0], dict) else {}
        speed = first_mem.get("Speed")
        if speed:
            specs["ram_speed"] = f"{speed} MHz"
        smbios_type = first_mem.get("SMBIOSMemoryType") or first_mem.get("MemoryType")
        if smbios_type in _SMBIOS_MEMORY_TYPES:
            specs["ram_type"] = _SMBIOS_MEMORY_TYPES[smbios_type]
        elif smbios_type:
            specs["ram_type"] = f"DDR{smbios_type}"

    # Storage
    disk_list = raw.get("Disks")
    if isinstance(disk_list, dict):
        disk_list = [disk_list]
    if isinstance(disk_list, list) and disk_list:
        specs["storage_drives_count"] = len(disk_list)
        total_disk_bytes = sum(d.get("Size", 0) for d in disk_list if isinstance(d, dict))
        if total_disk_bytes > 0:
            specs["storage_total_gb"] = round(total_disk_bytes / (1024**3), 0)

        models = " ".join(str(d.get("Model", "")) for d in disk_list)
        types = " ".join(str(d.get("MediaType", "")) for d in disk_list)
        combined = f"{models} {types}".lower()
        if any(keyword in combined for keyword in ("nvme", "ssd", "solid state")):
            specs["storage_type"] = "SSD"
        elif "hard disk" in combined:
            specs["storage_type"] = "HDD"
        else:
            specs["storage_type"] = "SSD"

        statuses = [d.get("Status") for d in disk_list if isinstance(d, dict)]
        if all(s == "OK" for s in statuses if s):
            specs["storage_health"] = "Good"
        elif any(s and s != "OK" for s in statuses):
            specs["storage_health"] = "Warning"

    # Graphics (GPUs)
    gpu_list = raw.get("GPUs")
    if isinstance(gpu_list, dict):
        gpu_list = [gpu_list]
    if isinstance(gpu_list, list) and gpu_list:
        valid_gpus = [g for g in gpu_list if isinstance(g, dict) and g.get("Name")]
        if valid_gpus:
            chosen = max(valid_gpus, key=lambda g: g.get("AdapterRAM", 0))
            gpu_name = str(chosen.get("Name", "")).strip()
            if gpu_name and gpu_name.lower() not in generic_placeholders:
                specs["gpu_name"] = gpu_name
            drv_ver = str(chosen.get("DriverVersion", "")).strip()
            if drv_ver:
                specs["gpu_driver_version"] = drv_ver
            ram_bytes = chosen.get("AdapterRAM")
            if ram_bytes and isinstance(ram_bytes, (int, float)) and ram_bytes > 0:
                specs["gpu_memory_mb"] = round(ram_bytes / (1024**2), 0)

    # Motherboard
    board_data = raw.get("Motherboard") or {}
    if board_data.get("Manufacturer"):
        val = str(board_data["Manufacturer"]).strip()
        if val and val.lower() not in generic_placeholders:
            specs["motherboard_manufacturer"] = val
    if board_data.get("Product"):
        val = str(board_data["Product"]).strip()
        if val and val.lower() not in generic_placeholders:
            specs["motherboard_model"] = val
    if board_data.get("SerialNumber"):
        val = str(board_data["SerialNumber"]).strip()
        if val and val.lower() not in generic_placeholders:
            specs["motherboard_serial"] = val

    # Fast targeted motherboard serial query if still missing
    if not specs.get("motherboard_serial"):
        try:
            res_mb = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "(Get-CimInstance Win32_BaseBoard).SerialNumber"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            mb_val = res_mb.stdout.strip()
            if mb_val and mb_val.lower() not in generic_placeholders:
                specs["motherboard_serial"] = mb_val
        except Exception:
            pass

    # Detect Chipset
    if specs.get("processor_name"):
        if "intel" in specs["processor_name"].lower():
            specs["motherboard_chipset"] = "Intel"
        elif "amd" in specs["processor_name"].lower():
            specs["motherboard_chipset"] = "AMD"

    # Operating System
    os_data = raw.get("OS") or {}
    if os_data.get("InstallDate"):
        parsed = _parse_wmi_date(os_data["InstallDate"], date_only=True)
        if parsed:
            specs["os_install_date"] = parsed
    if os_data.get("LastBootUpTime"):
        dt_str = _parse_wmi_date(os_data["LastBootUpTime"], date_only=False)
        if dt_str:
            try:
                dt = datetime.strptime(dt_str, "%d-%m-%Y %H:%M")
                specs["last_boot_time"] = _format_boot_time(dt)
            except Exception:
                specs["last_boot_time"] = dt_str

    # Network
    net_list = raw.get("Network")
    if isinstance(net_list, dict):
        net_list = [net_list]
    if isinstance(net_list, list) and net_list:
        chosen_net = None
        for n in net_list:
            if isinstance(n, dict) and n.get("DefaultIPGateway"):
                chosen_net = n
                break
        if not chosen_net and net_list:
            chosen_net = net_list[0]

        if chosen_net and isinstance(chosen_net, dict):
            subnets = chosen_net.get("IPSubnet")
            if isinstance(subnets, list) and subnets:
                for sm in subnets:
                    if "." in str(sm):
                        specs["subnet_mask"] = str(sm)
                        break
            elif isinstance(subnets, str) and "." in subnets:
                specs["subnet_mask"] = subnets

            gateways = chosen_net.get("DefaultIPGateway")
            if isinstance(gateways, list) and gateways:
                for gw in gateways:
                    if "." in str(gw):
                        specs["default_gateway"] = str(gw)
                        break
            elif isinstance(gateways, str) and "." in gateways:
                specs["default_gateway"] = gateways

            dns = chosen_net.get("DNSServerSearchOrder")
            if isinstance(dns, list) and dns:
                ipv4_dns = [str(d) for d in dns if "." in str(d)]
                specs["dns_servers"] = ", ".join(ipv4_dns) if ipv4_dns else str(dns[0])
            elif isinstance(dns, str):
                specs["dns_servers"] = dns

            desc = str(chosen_net.get("Description", "")).lower()
            if any(w in desc for w in ("wi-fi", "wifi", "wireless", "802.11", "ax210")):
                specs["connection_type"] = "Wi-Fi"
            elif desc:
                specs["connection_type"] = "Ethernet"

    # Power Plan
    power_raw = raw.get("PowerPlan")
    if power_raw and isinstance(power_raw, str):
        match_plan = re.search(r"\(([^)]+)\)", power_raw)
        if match_plan:
            specs["power_plan"] = match_plan.group(1).strip()
        else:
            specs["power_plan"] = power_raw.strip()


# ============================================================================
# Hardware Fingerprinting & Change Detection
# ============================================================================

def compute_hardware_fingerprint(specs: dict[str, Any]) -> str:
    """
    Compute a deterministic SHA-256 fingerprint for static hardware specifications.
    Volatile/relative runtime fields (such as last_boot_time) are excluded from the
    fingerprint to prevent unnecessary churn.
    """
    if not specs:
        return hashlib.sha256(b"{}").hexdigest()

    excluded_fields = {"last_boot_time"}
    normalized = {}
    for k, v in sorted(specs.items()):
        if k in excluded_fields:
            continue
        normalized[k] = v

    canonical_json = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def load_hardware_state(state_file: str | None = None) -> dict:
    """
    Load persisted hardware state (last delivered fingerprint, last enqueued fingerprint).
    Returns a default dictionary if the file is missing or corrupted.
    """
    filepath = state_file or HARDWARE_STATE_FILE
    default_state = {
        "last_delivered_fingerprint": None,
        "last_enqueued_fingerprint": None,
        "last_delivery_time": None,
        "last_scan_time": None,
    }

    if not os.path.exists(filepath):
        return default_state

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {
                    "last_delivered_fingerprint": data.get("last_delivered_fingerprint"),
                    "last_enqueued_fingerprint": data.get("last_enqueued_fingerprint"),
                    "last_delivery_time": data.get("last_delivery_time"),
                    "last_scan_time": data.get("last_scan_time"),
                }
    except (json.JSONDecodeError, OSError, ValueError, TypeError) as e:
        logger.warning(f"Corrupted or unreadable hardware state file '{filepath}' ({e}); resetting state.")

    return default_state


def save_hardware_state(state: dict, state_file: str | None = None) -> None:
    """
    Atomically save hardware state to disk using tempfile + os.replace.
    Guarantees no partial or corrupted file can remain on disk upon crash.
    """
    filepath = state_file or HARDWARE_STATE_FILE
    target_dir = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(target_dir, exist_ok=True)

    normalized_state = {
        "last_delivered_fingerprint": state.get("last_delivered_fingerprint"),
        "last_enqueued_fingerprint": state.get("last_enqueued_fingerprint"),
        "last_delivery_time": state.get("last_delivery_time"),
        "last_scan_time": state.get("last_scan_time"),
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
        logger.exception(f"Failed to atomically persist hardware state to '{filepath}': {e}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def record_hardware_enqueued(fingerprint: str, state_file: str | None = None) -> None:
    """Record that hardware specs with this fingerprint was placed into the outbox."""
    state = load_hardware_state(state_file)
    state["last_enqueued_fingerprint"] = fingerprint
    save_hardware_state(state, state_file)


def record_hardware_delivered(fingerprint: str, state_file: str | None = None) -> None:
    """Record that hardware specs with this fingerprint was successfully acknowledged/delivered."""
    state = load_hardware_state(state_file)
    state["last_delivered_fingerprint"] = fingerprint
    state["last_delivery_time"] = time.time()
    save_hardware_state(state, state_file)
