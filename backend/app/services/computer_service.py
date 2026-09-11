from datetime import datetime, timezone
from sqlalchemy import select, or_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session

from app.models.computer import Computer
from app.models.agent_credential import AgentCredential
from app.models.client_status import ClientStatus
from app.schemas.computer_schema import (
    ComputerCreate,
    ComputerPatch,
    ComputerUpdate,
)
from app.services import alert_service



def get_all_computers(
    db: Session,
    status: str | None = None
) -> list[Computer]:
    query = select(Computer)

    if status is not None:
        query = query.join(Computer.status_info).where(
            ClientStatus.status == status
        )

    return list(db.scalars(query).all())

def get_computer_by_id(
    db: Session,
    computer_id: int,
) -> Computer | None:
    return db.scalar(
        select(Computer).where(
            Computer.id == computer_id
        )
    )

def get_computer_by_hostname(
    db: Session,
    hostname: str,
) -> Computer | None:
    return db.scalar(
        select(Computer).where(
            Computer.hostname == hostname
        )
    )

def get_computer_by_mac(
    db: Session,
    mac_address: str,
) -> Computer | None:
    return db.scalar(
        select(Computer).where(
            Computer.mac_address == mac_address
        )
    )

def has_identity_conflict(
    db: Session,
    computer_id: int,
    hostname:str,
    mac_address: str,
) -> bool:
    conflict = db.scalar(select(Computer).where(
        Computer.id != computer_id,
            (
                (Computer.hostname == hostname) | (Computer.mac_address == mac_address)
            )
        )
    )

    return conflict is not None

def has_patch_identity_conflict(
    db: Session,
    computer_id: int,
    hostname: str | None,
    mac_address: str | None,
) -> bool:
    conditions = []

    if hostname is not None:
        conditions.append(
            Computer.hostname == hostname
        )

    if mac_address is not None:
        conditions.append(
            Computer.mac_address == mac_address
        )

    if not conditions:
        return False

    conflict = db.scalar(
        select(Computer).where(
            Computer.id != computer_id,
            or_(*conditions)
        )
    )

    return conflict is not None

def create_computer(
    db: Session,
    computer_data: ComputerCreate,
    agent_credential: "AgentCredential"
) -> Computer:
        # new_computer = Computer(
        #     hostname = computer.hostname,
        #     ip_address = computer.ip_address,
        #     mac_address = computer.mac_address,
        #     os_name = computer.os_name,
        #     os_version = computer.os_version,
        # )
    
    computer = Computer(
        **computer_data.model_dump(mode='json')
    )

    try:
        db.add(computer)
        db.flush()

        agent_credential.computer_id = computer.id

        db.commit()
        db.refresh(computer)

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return computer

def update_computer(
    db: Session,
    computer: Computer,
    computer_data: ComputerUpdate,
) -> Computer:
    update_data = computer_data.model_dump(mode="json")

    for key, value in update_data.items():
        setattr(computer, key, value)

    try: 
        db.commit()
        db.refresh(computer)

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return computer

def patch_computer(
    db: Session,
    computer: Computer,
    computer_data: ComputerPatch,
) -> Computer:
    update_data = computer_data.model_dump(
        exclude_unset=True, mode="json"
    )

    for field, value in update_data.items():
        setattr(computer, field, value)

    try:
        db.commit()
        db.refresh(computer)

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return computer

def delete_computer(
    db: Session,
    computer: Computer,
) -> None:
    try:
        db.delete(computer)
        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise

def record_heartbeat(
        db: Session,
        computer: Computer,
) -> Computer:

    if computer.status_info is None:
        computer.status_info = ClientStatus(computer_id = computer.id)
    computer.status_info.status = "online"
    computer.status_info.last_seen = datetime.now(timezone.utc)

    try: 
        db.commit()
        db.refresh(computer)
    except SQLAlchemyError:
        db.rollback()

        raise

    return computer


def set_online(
    db: Session,
    computer: Computer,
) -> None:
    
    if computer.status_info is None:
        computer.status_info = ClientStatus(computer_id = computer.id)

    computer.status_info.status = "online"
    computer.status_info.last_seen = datetime.now(timezone.utc)

    db.commit()


async def set_offline(
    db: Session,
    computer: Computer,
) -> None:
    if computer.status_info is not None:
        computer.status_info.status = "offline"
        db.commit()
        await alert_service.notify_offline(db, computer.id)