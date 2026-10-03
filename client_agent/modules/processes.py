"""
SLMS Client Agent Process Monitoring Module.

Enumerates running processes on the host workstation with:
- System process filtering to remove Windows kernel/idle noise (E-02).
- Strict privacy protection with zero username collection (E-03).
- Bounded payload limits and deterministic resource-prioritized ordering (E-04).
"""

from __future__ import annotations

from datetime import datetime, timezone
import psutil

from config import (
    MAX_PROCESS_NAME_LENGTH,
    MAX_PROCESSES_INVENTORY,
)

# ============================================================================
# System Process Filtering (E-02)
# ============================================================================

SYSTEM_PROCESS_PIDS: set[int] = {0, 4}

SYSTEM_PROCESS_NAMES: set[str] = {
    "system idle process",
    "system",
    "registry",
    "memory compression",
    "secure system",
    "idle",
    "interrupts",
}


def is_system_process(pid: int, name: str) -> bool:
    """
    Determine if a process is a Windows kernel or system pseudo-process (E-02).

    Filtering Policy:
    - Excludes kernel PIDs (PID 0 = System Idle Process, PID 4 = System).
    - Excludes named Windows kernel memory/driver pseudo-processes that have
      no user-level executable context or image on disk.
    - Preserves legitimate Windows background services (svchost.exe, lsass.exe,
      services.exe, etc.) and user/student applications.
    """
    if pid in SYSTEM_PROCESS_PIDS:
        return True
    if name and name.strip().lower() in SYSTEM_PROCESS_NAMES:
        return True
    return False


# ============================================================================
# Process Enumeration
# ============================================================================

def get_running_processes(
    max_processes: int = MAX_PROCESSES_INVENTORY,
    max_name_len: int = MAX_PROCESS_NAME_LENGTH,
) -> list[dict]:
    """
    Collect currently active processes.

    Guarantees:
    - Filters system pseudo-processes (E-02).
    - Sets user to None; never queries or exposes Windows username (E-03).
    - Deterministically bounds inventory to max_processes (E-04).
    - Sorts by (-cpu_percent, -memory_percent, name, pid) for stable, deterministic payloads.
    """
    processes: list[dict] = []

    for process in psutil.process_iter(
        [
            "pid",
            "name",
            "cpu_percent",
            "memory_percent",
            "status",
            "create_time",
        ]
    ):
        try:
            info = process.info

            pid = info.get("pid")
            name = info.get("name")

            if pid is None or not name:
                continue

            # E-02: Exclude Windows kernel/idle pseudo-processes
            if is_system_process(pid, name):
                continue

            cpu_percent = info.get("cpu_percent") or 0
            memory_percent = info.get("memory_percent") or 0
            status = info.get("status")
            create_time = info.get("create_time")

            start_time = None
            if create_time:
                try:
                    start_time = datetime.fromtimestamp(
                        create_time,
                        tz=timezone.utc,
                    ).isoformat()
                except (ValueError, OSError):
                    start_time = None

            # E-04: Truncate process name to max length
            clean_name = str(name).strip()[:max_name_len]

            processes.append(
                {
                    "pid": int(pid),
                    "name": clean_name,
                    # E-03: Privacy guarantee - username is never collected
                    "user": None,
                    "cpu_percent": round(max(0.0, float(cpu_percent)), 2),
                    "memory_percent": round(max(0.0, float(memory_percent)), 2),
                    "status": str(status) if status else None,
                    "start_time": start_time,
                }
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue
        except Exception:
            continue

    # E-04: Deterministic ordering - resource hogs first, ties broken by name & pid
    processes.sort(
        key=lambda item: (
            -item["cpu_percent"],
            -item["memory_percent"],
            item["name"].casefold(),
            item["pid"],
        )
    )

    # E-04: Deterministic truncation to bounded limit
    if max_processes > 0 and len(processes) > max_processes:
        processes = processes[:max_processes]

    return processes