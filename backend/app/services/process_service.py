from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.process import Process
from app.schemas.process_schema import ProcessUpload


MAX_PROCESS_ITEMS = 5000


def replace_process_inventory(
    db: Session,
    computer_id: int,
    process_data: ProcessUpload,
) -> list[Process]:

    items = process_data.processes[
        :MAX_PROCESS_ITEMS
    ]

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
                    0,
                    item.cpu_percent,
                ),
                memory_percent=max(
                    0,
                    item.memory_percent,
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


def get_processes_for_computer(
    db: Session,
    computer_id: int,
    limit: int = 500,
    offset: int = 0,
) -> list[Process]:

    limit = min(
        max(limit, 1),
        5000,
    )

    return list(
        db.scalars(
            select(Process)
            .where(
                Process.computer_id == computer_id
            )
            .order_by(
                Process.cpu_percent.desc(),
                Process.memory_percent.desc(),
                Process.name.asc(),
                Process.pid.asc(),
            )
            .limit(limit)
            .offset(offset)
        ).all()
    )


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
    from app.models.computer_hardware import ComputerHardware

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