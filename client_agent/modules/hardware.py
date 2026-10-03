"""
SLMS Client Agent Hardware Information Module.

Collects CPU, RAM, Disk, and Boot time metrics.

D-08 Non-blocking CPU Collection:
Replaced blocking `psutil.cpu_percent(interval=1)` with non-blocking sampling
`psutil.cpu_percent(interval=None)`. CPU monitoring is initialized at module
import time. Subsequent non-blocking calls return the true CPU percentage
measured across the interval since the previous sample without stalling the
agent thread for 1 second.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import psutil

# Prime psutil CPU sampling at module import so subsequent non-blocking
# calls have a reference baseline without requiring a blocking sleep.
_cpu_initialized: bool = False

try:
    psutil.cpu_percent(interval=None)
    _cpu_initialized = True
except Exception:
    _cpu_initialized = False


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

    system_drive = os.environ.get("SystemDrive", "C:")
    # Ensure trailing slash for Windows drive root
    drive_path = system_drive.rstrip("\\") + "\\"
    disk = psutil.disk_usage(drive_path)

    boot_time = datetime.fromtimestamp(psutil.boot_time())

    return {
        "cpu_usage": float(cpu_usage),
        "cpu_count": psutil.cpu_count(logical=True),
        "ram_total_gb": round(memory.total / (1024**3), 2),
        "ram_used_gb": round(memory.used / (1024**3), 2),
        "ram_percent": float(memory.percent),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_percent": float(disk.percent),
        "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
    }
