from datetime import datetime, timezone
import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import (
    generate_token,
    hash_secret,
    verify_secret,
)
from app.models.agent_credential import AgentCredential
from app.models.audit_log import AuditResult
from app.models.computer import Computer
from app.schemas.agent_schema import AgentRegisterResponse
from app.schemas.computer_schema import ComputerCreate
from app.services import (
    audit_service,
    computer_service,
    enrollment_service,
)


def register_with_enrollment_key(
    db: Session,
    enrollment_key: str,
    device: ComputerCreate,
) -> AgentRegisterResponse | None:

    # -------------------------------------------------
    # 1. Check for duplicate computer identity first.
    # -------------------------------------------------

    existing_hostname = (
        computer_service.get_computer_by_hostname(
            db,
            device.hostname,
        )
    )

    if existing_hostname is not None:
        raise ValueError(
            "hostname_conflict"
        )

    existing_mac = (
        computer_service.get_computer_by_mac(
            db,
            device.mac_address,
        )
    )

    if existing_mac is not None:
        raise ValueError(
            "mac_conflict"
        )

    # -------------------------------------------------
    # 2. Validate and consume enrollment key.
    #
    # The key is only flushed here.
    # It is committed together with the computer
    # and credential below.
    # -------------------------------------------------

    key_record = (
        enrollment_service.validate_and_consume_key(
            db,
            enrollment_key,
        )
    )

    if key_record is None:
        return None

    # -------------------------------------------------
    # 3. Generate agent credentials.
    # -------------------------------------------------

    agent_id = generate_token(
        prefix="AGT_",
        nbytes=6,
    )

    client_secret = generate_token(
        nbytes=32
    )

    # -------------------------------------------------
    # 4. Create computer and agent credential
    # in the same database transaction.
    # -------------------------------------------------

    computer = Computer(
        **device.model_dump(mode="json")
    )

    try:
        db.add(computer)

        db.flush()

        credential = AgentCredential(
            agent_id=agent_id,
            secret_hash=hash_secret(
                client_secret
            ),
            computer_id=computer.id,
            is_active=True,
        )

        db.add(credential)

        db.flush()

        # -------------------------------------------------
        # 5. Commit everything together.
        # -------------------------------------------------

        db.commit()

        db.refresh(computer)

        # -------------------------------------------------
        # 6. Audit successful registration.
        # -------------------------------------------------

        audit_service.log_action(
            db=db,
            action="AGENT_REGISTER",
            result=AuditResult.success,
            target_type="computer",
            target_id=computer.id,
        )

    except IntegrityError:
        db.rollback()

        raise ValueError(
            "Computer or credential conflicts "
            "with an existing record"
        )

    except SQLAlchemyError:
        db.rollback()

        raise

    return AgentRegisterResponse(
        computer_id=computer.id,
        agent_id=agent_id,
        client_secret=client_secret,
    )


def authenticate_agent(
    db: Session,
    agent_id: str,
    client_secret: str,
) -> AgentCredential | None:

    credential = db.scalar(
        select(AgentCredential).where(
            AgentCredential.agent_id == agent_id,
            AgentCredential.is_active.is_(True),
        )
    )

    # -------------------------------------------------
    # Invalid or revoked credential.
    # -------------------------------------------------

    if (
        credential is None
        or not verify_secret(
            client_secret,
            credential.secret_hash,
        )
    ):

        audit_service.log_action(
            db=db,
            action="AGENT_AUTH",
            result=AuditResult.failure,
            target_type="agent_credential",
            target_id=(
                credential.id
                if credential
                else None
            ),
        )

        return None

    # -------------------------------------------------
    # Successful authentication.
    # -------------------------------------------------

    credential.last_used_at = (
        datetime.now(timezone.utc)
    )

    try:
        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise

    audit_service.log_action(
        db=db,
        action="AGENT_AUTH",
        result=AuditResult.success,
        target_type="agent_credential",
        target_id=credential.id,
    )

    return credential