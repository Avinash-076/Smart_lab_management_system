from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.computer_hardware import ComputerHardware
from app.models.process import Process
from app.schemas.process_schema import ProcessUpload


MAX_PROCESS_ITEMS = 5000


def replace_process_inventory(
    db: Session,
    computer_id: int,
    process_data: ProcessUpload,
) -> list[Process]:
    items = process_data.processes[:MAX_PROCESS_ITEMS]

    hardware = db.scalars(
        select(ComputerHardware).where(ComputerHardware.computer_id == computer_id)
    ).first()
    total_ram_mb = (
        (hardware.ram_total_gb * 1024.0)
        if (hardware and hardware.ram_total_gb)
        else (16.0 * 1024.0)
    )

    try:
        # Remove the previous snapshot for this computer.
        db.execute(
            delete(Process).where(
                Process.computer_id == computer_id
            )
        )

        process_records = []
        seen: set[tuple[int, str]] = set()

        for item in items:
            name = item.name.strip()
            if not name:
                continue

            identity = (
                item.pid,
                name.casefold(),
            )

            if identity in seen:
                continue

            seen.add(identity)

            mem_pct = max(0.0, float(item.memory_percent or 0))
            if item.memory_mb is not None and item.memory_mb > 0:
                mem_mb = round(float(item.memory_mb), 1)
            else:
                mem_mb = round((mem_pct / 100.0) * total_ram_mb, 1) if mem_pct > 0 else 0.0

            record = Process(
                computer_id=computer_id,
                pid=item.pid,
                name=name,
                user=(
                    item.user.strip()
                    if item.user
                    else None
                ),
                cpu_percent=max(
                    0.0,
                    float(item.cpu_percent or 0),
                ),
                memory_percent=mem_pct,
                memory_mb=mem_mb,
                executable_path=(
                    item.executable_path.strip()[:500]
                    if item.executable_path
                    else None
                ),
                status=(
                    item.status.strip()
                    if item.status
                    else None
                ),
                start_time=(
                    item.start_time.strip()
                    if item.start_time
                    else None
                ),
            )

            db.add(record)
            process_records.append(record)

        db.commit()

        for record in process_records:
            db.refresh(record)

        return process_records

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise


def _build_process_filter_conditions(
    computer_id: int,
    search: str | None = None,
    status: str | None = None,
    cpu_min: float | None = None,
    memory_min_mb: float | None = None,
    user: str | None = None,
) -> list[Any]:
    conditions: list[Any] = [Process.computer_id == computer_id]

    if search and search.strip():
        term = search.strip()
        pattern = f"%{term.lower()}%"
        if term.isdigit():
            pid_val = int(term)
            conditions.append(
                func.lower(Process.name).like(pattern)
                | (Process.pid == pid_val)
                | func.lower(func.coalesce(Process.executable_path, "")).like(pattern)
            )
        else:
            conditions.append(
                func.lower(Process.name).like(pattern)
                | func.lower(func.coalesce(Process.executable_path, "")).like(pattern)
                | func.lower(func.coalesce(Process.user, "")).like(pattern)
            )

    if status and status.strip() and status.lower() != "all":
        st = status.strip().lower()
        if st in ("all processes", "all"):
            pass
        elif st == "others":
            conditions.append(
                ~func.lower(func.coalesce(Process.status, "")).in_(
                    ["running", "suspended", "not responding", "zombie"]
                )
            )
        else:
            conditions.append(
                func.lower(func.coalesce(Process.status, "")) == st
            )

    if cpu_min is not None and cpu_min > 0:
        conditions.append(Process.cpu_percent >= cpu_min)

    if memory_min_mb is not None and memory_min_mb > 0:
        conditions.append(Process.memory_mb >= memory_min_mb)

    if user and user.strip() and user.lower() not in ("all", "all users"):
        conditions.append(func.lower(func.coalesce(Process.user, "")) == user.strip().lower())

    return conditions


def get_processes_count_for_computer(
    db: Session,
    computer_id: int,
    search: str | None = None,
    status: str | None = None,
    cpu_min: float | None = None,
    memory_min_mb: float | None = None,
    user: str | None = None,
) -> int:
    conditions = _build_process_filter_conditions(
        computer_id=computer_id,
        search=search,
        status=status,
        cpu_min=cpu_min,
        memory_min_mb=memory_min_mb,
        user=user,
    )
    return db.scalar(
        select(func.count(Process.id)).where(*conditions)
    ) or 0


def get_processes_for_computer(
    db: Session,
    computer_id: int,
    search: str | None = None,
    status: str | None = None,
    cpu_min: float | None = None,
    memory_min_mb: float | None = None,
    user: str | None = None,
    sort_by: str = "cpu_percent",
    sort_order: str = "desc",
    limit: int | None = 500,
    offset: int = 0,
) -> list[Process]:
    conditions = _build_process_filter_conditions(
        computer_id=computer_id,
        search=search,
        status=status,
        cpu_min=cpu_min,
        memory_min_mb=memory_min_mb,
        user=user,
    )

    query = select(Process).where(*conditions)

    # Sorting resolution
    sort_col_map = {
        "name": Process.name,
        "pid": Process.pid,
        "status": Process.status,
        "cpu": Process.cpu_percent,
        "cpu_percent": Process.cpu_percent,
        "memory": Process.memory_mb,
        "memory_mb": Process.memory_mb,
        "memory_percent": Process.memory_percent,
        "user": Process.user,
        "start_time": Process.start_time,
        "collected_at": Process.collected_at,
    }

    sort_col = sort_col_map.get(sort_by, Process.cpu_percent)

    if sort_order.lower() == "asc":
        query = query.order_by(sort_col.asc(), Process.name.asc(), Process.pid.asc())
    else:
        query = query.order_by(sort_col.desc(), Process.name.asc(), Process.pid.asc())

    if limit is not None:
        clamped_limit = min(max(limit, 1), 5000)
        query = query.limit(clamped_limit).offset(max(offset, 0))
    elif offset > 0:
        query = query.offset(offset)

    return list(db.scalars(query).all())


def get_process_summary_for_computer(
    db: Session,
    computer_id: int,
    search: str | None = None,
    status: str | None = None,
    cpu_min: float | None = None,
    memory_min_mb: float | None = None,
    user: str | None = None,
) -> dict:
    """
    Computes real-time process statistics for the summary cards,
    donut status distribution, and top CPU consumer bars.
    """
    hardware = db.scalars(
        select(ComputerHardware).where(ComputerHardware.computer_id == computer_id)
    ).first()
    system_ram_gb = hardware.ram_total_gb if hardware else 16.0
    total_ram_mb = system_ram_gb * 1024.0

    all_computer_procs = list(
        db.scalars(
            select(Process)
            .where(Process.computer_id == computer_id)
            .order_by(Process.cpu_percent.desc())
        ).all()
    )

    total_running = len(all_computer_procs)
    total_cpu = round(sum(p.cpu_percent for p in all_computer_procs), 1)

    # Calculate total memory MB
    total_mem_mb = 0.0
    for p in all_computer_procs:
        if p.memory_mb is not None and p.memory_mb > 0:
            total_mem_mb += p.memory_mb
        elif p.memory_percent:
            total_mem_mb += (p.memory_percent / 100.0) * total_ram_mb
    total_mem_mb = round(total_mem_mb, 1)

    total_mem_percent = (
        round((total_mem_mb / total_ram_mb) * 100.0, 1)
        if total_ram_mb > 0
        else 0.0
    )

    last_scan = None
    if all_computer_procs:
        last_scan = max(p.collected_at for p in all_computer_procs)

    # Status distribution
    # Supported categories matching the design: Running, Suspended, Not Responding, Zombie, Others
    status_counts: dict[str, int] = {
        "Running": 0,
        "Suspended": 0,
        "Not Responding": 0,
        "Zombie": 0,
        "Others": 0,
    }

    for p in all_computer_procs:
        st_raw = (p.status or "").strip().lower()
        if st_raw in ("running", "active"):
            status_counts["Running"] += 1
        elif st_raw in ("suspended", "sleeping", "wait"):
            status_counts["Suspended"] += 1
        elif st_raw in ("not responding", "unresponsive", "hung"):
            status_counts["Not Responding"] += 1
        elif st_raw in ("zombie", "defunct"):
            status_counts["Zombie"] += 1
        else:
            status_counts["Others"] += 1

    status_distribution = []
    for cat_name in ["Running", "Suspended", "Not Responding", "Zombie", "Others"]:
        count = status_counts[cat_name]
        pct = round((count / total_running) * 100.0, 1) if total_running > 0 else 0.0
        status_distribution.append(
            {
                "status": cat_name,
                "count": count,
                "percentage": pct,
            }
        )

    # Top processes by CPU
    top_cpu_processes = []
    for p in all_computer_procs[:6]:
        top_cpu_processes.append(
            {
                "pid": p.pid,
                "name": p.name,
                "cpu_percent": round(p.cpu_percent, 1),
                "user": p.user or "System",
            }
        )

    # Distinct users
    user_set = {p.user.strip() for p in all_computer_procs if p.user and p.user.strip()}
    users = sorted(list(user_set))

    # Distinct statuses
    status_set = {p.status.strip() for p in all_computer_procs if p.status and p.status.strip()}
    statuses = sorted(list(status_set))

    return {
        "total_running": total_running,
        "total_cpu_percent": total_cpu,
        "total_memory_mb": total_mem_mb,
        "total_memory_percent": total_mem_percent,
        "system_ram_gb": system_ram_gb,
        "last_scan": last_scan,
        "status_distribution": status_distribution,
        "top_cpu_processes": top_cpu_processes,
        "users": users,
        "statuses": statuses,
    }


def delete_processes_for_computer(
    db: Session,
    computer_id: int,
) -> None:
    try:
        db.execute(
            delete(Process).where(
                Process.computer_id == computer_id
            )
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def get_process_rankings(
    db: Session,
    computer_id: int,
    limit: int = 5,
) -> dict:
    """
    Retrieve ranked process lists for Matrix tab monitoring:
    - Top CPU consumers
    - Top Memory consumers
    - Platform network attribution metadata
    """
    limit = min(max(limit, 1), 20)

    hardware = db.scalars(
        select(ComputerHardware).where(ComputerHardware.computer_id == computer_id)
    ).first()
    total_ram_mb = (
        (hardware.ram_total_gb * 1024.0)
        if (hardware and hardware.ram_total_gb)
        else (16.0 * 1024.0)
    )

    # Top CPU processes
    cpu_procs = list(
        db.scalars(
            select(Process)
            .where(Process.computer_id == computer_id)
            .order_by(
                Process.cpu_percent.desc(),
                Process.memory_percent.desc(),
                Process.name.asc(),
            )
            .limit(limit)
        ).all()
    )

    # Top Memory processes
    mem_procs = list(
        db.scalars(
            select(Process)
            .where(Process.computer_id == computer_id)
            .order_by(
                Process.memory_percent.desc(),
                Process.cpu_percent.desc(),
                Process.name.asc(),
            )
            .limit(limit)
        ).all()
    )

    def _format_item(rank: int, p: Process) -> dict:
        if p.memory_mb is not None and p.memory_mb > 0:
            mem_mb = p.memory_mb
        else:
            mem_mb = round((p.memory_percent / 100.0) * total_ram_mb, 1) if p.memory_percent else 0.0
        return {
            "rank": rank,
            "pid": p.pid,
            "name": p.name,
            "user": p.user or "System",
            "cpu_percent": round(p.cpu_percent, 1),
            "memory_percent": round(p.memory_percent, 1),
            "memory_mb": mem_mb,
            "download_mb": None,
            "upload_mb": None,
            "total_mb": None,
        }

    top_cpu = [_format_item(i + 1, p) for i, p in enumerate(cpu_procs)]
    top_mem = [_format_item(i + 1, p) for i, p in enumerate(mem_procs)]

    return {
        "computer_id": computer_id,
        "top_cpu": top_cpu,
        "top_memory": top_mem,
        "network": {
            "supported": False,
            "status": "unavailable",
            "reason": "Platform attribution unavailable: user-space process socket I/O is not reliably attributable without kernel-mode drivers on Windows.",
            "items": [],
        },
    }