from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.enrollment_key import EnrollmentKey
from app.auth import generate_token, hash_secret, verify_secret, generate_enrollment_key, normalize_key, ensure_utc

KEY_TTL_HOURS = 48

def create_enrollment_key(
    db: Session,
    created_by: int,
) -> tuple[EnrollmentKey, str]:
    plaintext = generate_enrollment_key()
    record = EnrollmentKey(
        key_hash = hash_secret(normalize_key(plaintext)),
        expires_at = datetime.now(timezone.utc) + timedelta(hours=KEY_TTL_HOURS),
        created_by = created_by
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
    plaintext_key: str
) -> EnrollmentKey | None:
    from sqlalchemy import select

    normalized = normalize_key(plaintext_key)

    candidates = db.scalars(
        select(EnrollmentKey).where(
            EnrollmentKey.used_at.is_(None)
        )
    ).all()

    for key in candidates:
        if verify_secret(normalized, key.key_hash):
            if ensure_utc(key.expires_at) < datetime.now(timezone.utc):
                return None
            return key

    return None
