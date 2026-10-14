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

import json
import os
import platform
import re
import subprocess
from datetime import datetime
from typing import Any

import psutil

try:
    from config import VERSION as AGENT_VERSION
except Exception:
    AGENT_VERSION = "1.0.0"

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
    """Parse WMI / CIM date strings into human-readable format."""
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
    Uses resilient platform probes (PowerShell / CIM on Windows with psutil/platform fallback).
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
        specs["system_type"] = f"{arch} Operating System" if arch else None
    except Exception:
        pass

    # 2. Windows-specific deep probe via PowerShell CimInstance
    if os.name == "nt":
        _probe_windows_hardware(specs)

    # 3. Canonical network identity fallback if not set by Windows probe
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
        except Exception:
            pass

    return specs


def _probe_windows_hardware(specs: dict[str, Any]) -> None:
    """Execute PowerShell CimInstance probe and enrich specs dict."""
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

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", f"& {{ {ps_script} }}"],
            capture_output=True,
            text=True,
            timeout=12,
        )
        if res.returncode != 0 or not res.stdout.strip():
            return

        raw = json.loads(res.stdout)
    except Exception:
        return

    # System & Chassis
    sys_data = raw.get("System") or {}
    if sys_data.get("Manufacturer"):
        specs["manufacturer"] = str(sys_data["Manufacturer"]).strip()
    if sys_data.get("Model"):
        specs["model"] = str(sys_data["Model"]).strip()
    if sys_data.get("SystemType"):
        st = str(sys_data["SystemType"]).strip()
        specs["system_type"] = "64-bit Operating System" if "64" in st else st

    # BIOS
    bios_data = raw.get("BIOS") or {}
    if bios_data.get("SMBIOSBIOSVersion"):
        specs["bios_version"] = str(bios_data["SMBIOSBIOSVersion"]).strip()
    if bios_data.get("ReleaseDate"):
        specs["bios_date"] = _parse_wmi_date(bios_data["ReleaseDate"], date_only=True)
    if bios_data.get("SerialNumber"):
        specs["serial_number"] = str(bios_data["SerialNumber"]).strip()

    # CPU
    cpu_data = raw.get("CPU") or {}
    if cpu_data.get("Name"):
        specs["processor_name"] = str(cpu_data["Name"]).strip()
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
    elif specs["processor_max_speed"]:
        specs["processor_base_speed"] = specs["processor_max_speed"]

    # Extract base speed from name if present (e.g. "@ 2.90GHz")
    if specs["processor_name"]:
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
        # Sort to prefer dedicated GPU with higher AdapterRAM
        valid_gpus = [g for g in gpu_list if isinstance(g, dict) and g.get("Name")]
        if valid_gpus:
            chosen = max(valid_gpus, key=lambda g: g.get("AdapterRAM", 0))
            specs["gpu_name"] = str(chosen.get("Name", "")).strip()
            specs["gpu_driver_version"] = str(chosen.get("DriverVersion", "")).strip() or None
            ram_bytes = chosen.get("AdapterRAM")
            if ram_bytes and isinstance(ram_bytes, (int, float)) and ram_bytes > 0:
                specs["gpu_memory_mb"] = round(ram_bytes / (1024**2), 0)

    # Motherboard
    board_data = raw.get("Motherboard") or {}
    if board_data.get("Manufacturer"):
        specs["motherboard_manufacturer"] = str(board_data["Manufacturer"]).strip()
    if board_data.get("Product"):
        specs["motherboard_model"] = str(board_data["Product"]).strip()
    if board_data.get("SerialNumber"):
        specs["motherboard_serial"] = str(board_data["SerialNumber"]).strip()
    # Detect Chipset
    if specs["processor_name"]:
        if "intel" in specs["processor_name"].lower():
            specs["motherboard_chipset"] = "Intel"
        elif "amd" in specs["processor_name"].lower():
            specs["motherboard_chipset"] = "AMD"

    # Operating System
    os_data = raw.get("OS") or {}
    if os_data.get("InstallDate"):
        specs["os_install_date"] = _parse_wmi_date(os_data["InstallDate"], date_only=True)
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
        # Find active network configuration that has default gateway or valid IP
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
                # pick IPv4 subnet mask (e.g. 255.255.255.0)
                for sm in subnets:
                    if "." in str(sm):
                        specs["subnet_mask"] = str(sm)
                        break
            elif isinstance(subnets, str):
                specs["subnet_mask"] = subnets

            gateways = chosen_net.get("DefaultIPGateway")
            if isinstance(gateways, list) and gateways:
                for gw in gateways:
                    if "." in str(gw):
                        specs["default_gateway"] = str(gw)
                        break
            elif isinstance(gateways, str):
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
            else:
                specs["connection_type"] = "Ethernet"

    # Power Plan
    power_raw = raw.get("PowerPlan")
    if power_raw and isinstance(power_raw, str):
        match_plan = re.search(r"\(([^)]+)\)", power_raw)
        if match_plan:
            specs["power_plan"] = match_plan.group(1).strip()
        else:
            specs["power_plan"] = power_raw.strip()
