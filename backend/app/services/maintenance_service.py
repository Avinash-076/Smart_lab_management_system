from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.maintenance import (
    MaintenanceRecord,
    MaintenanceStatus,
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
    limit: int = 100,
    offset: int = 0,
) -> list[MaintenanceRecord]:

    limit = min(
        max(limit, 1),
        500,
    )

    query = select(MaintenanceRecord)

    if computer_id is not None:
        query = query.where(
            MaintenanceRecord.computer_id
            == computer_id
        )

    if maintenance_status is not None:
        query = query.where(
            MaintenanceRecord.status
            == maintenance_status
        )

    query = (
        query
        .order_by(
            MaintenanceRecord.created_at.desc()
        )
        .limit(limit)
        .offset(offset)
    )

    return list(
        db.scalars(query).all()
    )


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

    if (
        record.status
        == MaintenanceStatus.in_progress
        and record.started_at is None
    ):
        record.started_at = now

    if (
        record.status
        == MaintenanceStatus.completed
        and record.completed_at is None
    ):
        record.completed_at = now

        if record.started_at is None:
            record.started_at = now

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