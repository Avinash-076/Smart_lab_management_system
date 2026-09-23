from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.usage_session import UsageSession
from app.schemas.usage_schema import (
    UsageSessionCreate,
    UsageUpload,
)

MAX_USAGE_SESSIONS = 2000


def create_usage_session(
    db: Session,
    computer_id: int,
    session_data: UsageSessionCreate,
) -> UsageSession:

    duration = session_data.duration_seconds

    if (
        duration == 0
        and session_data.ended_at is not None
    ):
        calculated = (
            session_data.ended_at
            - session_data.started_at
        ).total_seconds()

        duration = max(
            0,
            int(calculated),
        )

    record = UsageSession(
        computer_id=computer_id,
        application_name=session_data.application_name.strip(),
        started_at=session_data.started_at,
        ended_at=session_data.ended_at,
        duration_seconds=duration,
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


def create_usage_sessions(
    db: Session,
    computer_id: int,
    usage_data: UsageUpload,
) -> list[UsageSession]:

    records: list[UsageSession] = []

    try:
        for item in usage_data.sessions[:MAX_USAGE_SESSIONS]:

            application_name = (
                item.application_name.strip()
            )

            if not application_name:
                continue

            duration = item.duration_seconds

            if (
                duration == 0
                and item.ended_at is not None
            ):
                calculated = (
                    item.ended_at
                    - item.started_at
                ).total_seconds()

                duration = max(
                    0,
                    int(calculated),
                )

            record = UsageSession(
                computer_id=computer_id,
                application_name=application_name,
                started_at=item.started_at,
                ended_at=item.ended_at,
                duration_seconds=duration,
            )

            db.add(record)
            records.append(record)

        db.commit()

        for record in records:
            db.refresh(record)

        return records

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise


def get_usage_for_computer(
    db: Session,
    computer_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[UsageSession]:

    limit = min(
        max(limit, 1),
        500,
    )

    return list(
        db.scalars(
            select(UsageSession)
            .where(
                UsageSession.computer_id
                == computer_id
            )
            .order_by(
                UsageSession.started_at.desc()
            )
            .limit(limit)
            .offset(offset)
        ).all()
    )


def delete_usage_for_computer(
    db: Session,
    computer_id: int,
) -> None:

    try:
        db.execute(
            delete(UsageSession).where(
                UsageSession.computer_id
                == computer_id
            )
        )

        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise