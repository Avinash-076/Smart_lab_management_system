from datetime import datetime, timezone

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.computer import Computer
from app.models.maintenance import (
    MaintenanceRecord,
    MaintenanceStatus,
    MaintenanceType,
)
from app.schemas.maintenance_schema import (
    MaintenanceCreate,
    MaintenanceUpdate,
)


def get_maintenance_by_id(
    db: Session,
    maintenance_id: int,
) -> MaintenanceRecord | None:

    return db.get(
        MaintenanceRecord,
        maintenance_id,
    )


def get_maintenance_records(
    db: Session,
    computer_id: int | None = None,
    maintenance_status: MaintenanceStatus | None = None,
    maintenance_type: MaintenanceType | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[MaintenanceRecord]:

    limit = min(
        max(limit, 1),
        500,
    )

    offset = max(
        offset,
        0,
    )

    query = select(MaintenanceRecord)

    if computer_id is not None:
        query = query.where(
            MaintenanceRecord.computer_id == computer_id
        )

    if maintenance_status is not None:
        query = query.where(
            MaintenanceRecord.status == maintenance_status
        )

    if maintenance_type is not None:
        query = query.where(
            MaintenanceRecord.maintenance_type == maintenance_type
        )

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.outerjoin(
            Computer, MaintenanceRecord.computer_id == Computer.id
        ).where(
            or_(
                MaintenanceRecord.title.ilike(search_pattern),
                MaintenanceRecord.description.ilike(search_pattern),
                MaintenanceRecord.technician_name.ilike(search_pattern),
                MaintenanceRecord.work_performed.ilike(search_pattern),
                MaintenanceRecord.notes.ilike(search_pattern),
                Computer.hostname.ilike(search_pattern),
            )
        )

    query = (
        query
        .order_by(
            MaintenanceRecord.created_at.desc(),
            MaintenanceRecord.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    return list(
        db.scalars(query).all()
    )


def get_maintenance_stats(
    db: Session,
    computer_id: int | None = None,
) -> dict:

    query = select(
        func.count(MaintenanceRecord.id).label("total"),
        func.count(case((MaintenanceRecord.status == MaintenanceStatus.scheduled, 1))).label("scheduled"),
        func.count(case((MaintenanceRecord.status == MaintenanceStatus.in_progress, 1))).label("in_progress"),
        func.count(case((MaintenanceRecord.status == MaintenanceStatus.completed, 1))).label("completed"),
        func.count(case((MaintenanceRecord.status == MaintenanceStatus.cancelled, 1))).label("cancelled"),
        func.count(case((MaintenanceRecord.maintenance_type == MaintenanceType.preventive, 1))).label("preventive"),
        func.count(case((MaintenanceRecord.maintenance_type == MaintenanceType.corrective, 1))).label("corrective"),
        func.count(case((MaintenanceRecord.maintenance_type == MaintenanceType.emergency, 1))).label("emergency"),
        func.count(case((MaintenanceRecord.maintenance_type == MaintenanceType.software, 1))).label("software"),
        func.count(case((MaintenanceRecord.maintenance_type == MaintenanceType.hardware, 1))).label("hardware"),
    )

    if computer_id is not None:
        query = query.where(MaintenanceRecord.computer_id == computer_id)

    row = db.execute(query).one()

    return {
        "total": row.total or 0,
        "scheduled": row.scheduled or 0,
        "in_progress": row.in_progress or 0,
        "completed": row.completed or 0,
        "cancelled": row.cancelled or 0,
        "preventive": row.preventive or 0,
        "corrective": row.corrective or 0,
        "emergency": row.emergency or 0,
        "software": row.software or 0,
        "hardware": row.hardware or 0,
    }


def create_maintenance(
    db: Session,
    maintenance_data: MaintenanceCreate,
    created_by: int | None = None,
) -> MaintenanceRecord:

    record = MaintenanceRecord(
        computer_id=maintenance_data.computer_id,
        maintenance_type=maintenance_data.maintenance_type,
        title=maintenance_data.title.strip(),
        description=(
            maintenance_data.description.strip()
            if maintenance_data.description
            else None
        ),
        technician_name=(
            maintenance_data.technician_name.strip()
            if maintenance_data.technician_name
            else None
        ),
        scheduled_at=maintenance_data.scheduled_at,
        notes=(
            maintenance_data.notes.strip()
            if maintenance_data.notes
            else None
        ),
        created_by=created_by,
    )

    try:
        db.add(record)
        db.commit()
        db.refresh(record)

        return record

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise


def update_maintenance(
    db: Session,
    record: MaintenanceRecord,
    maintenance_data: MaintenanceUpdate,
) -> MaintenanceRecord:

    update_data = maintenance_data.model_dump(
        exclude_unset=True,
    )

    for field, value in update_data.items():

        if isinstance(value, str):
            value = value.strip()

        setattr(
            record,
            field,
            value,
        )

    now = datetime.now(timezone.utc)

    # Keep timestamps consistent with maintenance status.
    if record.status == MaintenanceStatus.scheduled:
        record.started_at = None
        record.completed_at = None

    elif record.status == MaintenanceStatus.in_progress:

        if record.started_at is None:
            record.started_at = now

        record.completed_at = None

    elif record.status == MaintenanceStatus.completed:

        if record.started_at is None:
            record.started_at = now

        if record.completed_at is None:
            record.completed_at = now

    elif record.status == MaintenanceStatus.cancelled:
        # A cancelled maintenance task should not appear
        # as completed.
        record.completed_at = None

    record.updated_at = now

    try:
        db.commit()
        db.refresh(record)

        return record

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise


def complete_maintenance(
    db: Session,
    record: MaintenanceRecord,
    work_performed: str | None = None,
    notes: str | None = None,
) -> MaintenanceRecord:

    now = datetime.now(timezone.utc)

    record.status = MaintenanceStatus.completed

    if work_performed:
        record.work_performed = work_performed.strip()

    if notes:
        record.notes = notes.strip()

    if record.started_at is None:
        record.started_at = now

    record.completed_at = now
    record.updated_at = now

    try:
        db.commit()
        db.refresh(record)

        return record

    except SQLAlchemyError:
        db.rollback()
        raise


def delete_maintenance(
    db: Session,
    record: MaintenanceRecord,
) -> None:

    try:
        db.delete(record)
        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise
