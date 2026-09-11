import secrets
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException, status

from app.models.agent_credential import AgentCredential
from app.models.computer import Computer
from app.models.audit_log import AuditResult
from app.schemas.computer_schema import ComputerCreate
from app.schemas.agent_schema import AgentRegisterResponse
from app.auth import generate_token, hash_secret, verify_secret
from app.services import enrollment_service, computer_service, audit_service



def register_with_enrollment_key(
    db: Session,
    enrollment_key: str,
    device: ComputerCreate,
) -> AgentRegisterResponse | None:

    key_record = enrollment_service.validate_and_consume_key(db, enrollment_key)

    if key_record is None:
        return None

    if computer_service.get_computer_by_hostname(db, device.hostname) is not None:
        raise ValueError("hostname_conflict")
    if computer_service.get_computer_by_mac(db, device.mac_address) is not None:
        raise ValueError("mac_conflict")

    computer = Computer(**device.model_dump(mode="json"))

    agent_id = generate_token(prefix="AGT_", nbytes=6)
    client_secret = generate_token(nbytes=32)

    try:
        db.add(computer)
        db.flush()

        credential = AgentCredential(
            agent_id = agent_id,
            secret_hash = hash_secret(client_secret),
            computer_id = computer.id,
            is_active = True
        )

        db.add(credential)

        key_record.used_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(computer)

        audit_service.log_action(
            db=db,
            action="AGENT_REGISTER",
            result=AuditResult.success,
            target_type="computer",
            target_id=computer.id
        )

    except IntegrityError as e:
        db.rollback()
        print(f"DEBUG IntegrityError: {e}")   # temporary — remove after debugging
        raise ValueError("Computer or Credential conflicts with an existing record")

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register agent",
        )

    return AgentRegisterResponse(
        computer_id=computer.id,
        agent_id=agent_id,
        client_secret=client_secret,
    )

def authenticate_agent(
    db: Session,
    agent_id: str, 
    client_secret: str
) -> AgentCredential | None:
    credential = db.scalar(
        select(AgentCredential).where(
            AgentCredential.agent_id == agent_id,
            AgentCredential.is_active == True,
        )
    )

    if credential is None or not verify_secret(client_secret, credential.secret_hash):
        audit_service.log_action(
            db = db,
            action="AGENT_AUTH",
            result=AuditResult.failure,
            target_type="agent_credential",
            target_id=credential.id if credential else None
        )
        return None

    credential.last_used_at = datetime.now(timezone.utc)

    audit_service.log_action(
        db=db,
        action="AGENT_AUTH",
        result=AuditResult.success,
        target_type="agent_credential",
        target_id=credential.id,
    )

    db.commit()

    return credential
