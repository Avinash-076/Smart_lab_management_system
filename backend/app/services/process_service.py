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
                Process.name.asc(),
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