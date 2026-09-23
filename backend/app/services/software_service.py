from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.software import Software
from app.schemas.software_schema import SoftwareUpload


MAX_SOFTWARE_ITEMS = 2000


def replace_software_inventory(
    db: Session,
    computer_id: int,
    software_data: SoftwareUpload,
) -> list[Software]:

    items = software_data.software[:MAX_SOFTWARE_ITEMS]

    try:
        db.execute(
            delete(Software).where(
                Software.computer_id == computer_id
            )
        )

        software_records = []

        seen: set[tuple[str, str]] = set()

        for item in items:

            name = item.name.strip()

            if not name:
                continue

            version = (
                item.version.strip()
                if item.version
                else None
            )

            publisher = (
                item.publisher.strip()
                if item.publisher
                else None
            )

            install_date = (
                item.install_date.strip()
                if item.install_date
                else None
            )

            identity = (
                name.casefold(),
                (version or "").casefold(),
            )

            if identity in seen:
                continue

            seen.add(identity)

            record = Software(
                computer_id=computer_id,
                name=name,
                version=version,
                publisher=publisher,
                install_date=install_date,
            )

            db.add(record)
            software_records.append(record)

        db.commit()

        for record in software_records:
            db.refresh(record)

        return software_records

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise


def get_software_for_computer(
    db: Session,
    computer_id: int,
) -> list[Software]:

    return list(
        db.scalars(
            select(Software)
            .where(
                Software.computer_id == computer_id
            )
            .order_by(
                Software.name.asc()
            )
        ).all()
    )


def delete_software_for_computer(
    db: Session,
    computer_id: int,
) -> None:

    try:
        db.execute(
            delete(Software).where(
                Software.computer_id == computer_id
            )
        )

        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise