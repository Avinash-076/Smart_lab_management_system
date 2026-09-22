from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import (
    generate_enrollment_key,
    hash_secret,
    normalize_key,
    verify_secret,
)
from app.models.enrollment_key import EnrollmentKey


KEY_TTL_HOURS = 48


def create_enrollment_key(
    db: Session,
    created_by: int,
) -> tuple[EnrollmentKey, str]:

    plaintext = generate_enrollment_key()

    record = EnrollmentKey(
        key_hash=hash_secret(
            normalize_key(plaintext)
        ),
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(hours=KEY_TTL_HOURS)
        ),
        created_by=created_by,
    )

    try:
        db.add(record)
        db.commit()
        db.refresh(record)

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return record, plaintext


def validate_and_consume_key(
    db: Session,
    plaintext_key: str,
) -> EnrollmentKey | None:

    normalized_key = normalize_key(
        plaintext_key
    )

    if not normalized_key:
        return None

    unused_keys = db.scalars(
        select(EnrollmentKey).where(
            EnrollmentKey.used_at.is_(None)
        )
    ).all()

    now = datetime.now(timezone.utc)

    for key_record in unused_keys:

        if not verify_secret(
            normalized_key,
            key_record.key_hash,
        ):
            continue

        expires_at = key_record.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc
            )

        if expires_at <= now:
            return None

        # Consume the key inside the current
        # registration transaction.
        #
        # The caller must commit the transaction
        # only after computer + credential creation
        # succeeds.
        key_record.used_at = now

        db.flush()

        return key_record

    return None