from app.schemas.command_schema import CommandResultSubmit
from app.models.remote_command import CommandStatus
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.remote_command import RemoteCommand
from app.models.command_result import CommandResult
from app.schemas.command_schema import CommandCreate, CommandResponse
from app.websocket.connection_manager import manager


async def create_and_dispatch_command(
    db: Session,
    computer_id: int,
    command_data: CommandCreate,
    issued_by: int,
) -> RemoteCommand:

    command = RemoteCommand(
        computer_id=computer_id,
        command_type=command_data.command_type,
        payload=command_data.payload,
        status=CommandStatus.pending,
        issued_by=issued_by,
    )

    try: 
        db.add(command)
        db.commit()
        db.refresh(command)

    except (IntegrityError, SQLAlchemyError) as e:
        db.rollback()
        raise ValueError(f"Failed to create command: {e}")

    delivered = await manager.send_to_client(
        computer_id,
        {
            "type": "command",
            "command_id": command.id,
            "command_type": command.command_type,
            "payload": command.payload
        }
    )

    if delivered:
        command.status = CommandStatus.delivered
        db.commit()
        db.refresh(command)

    return command


def get_commands_for_computer(
    db: Session, 
    computer_id: int, 
    limit: int = 100, 
    offset: int = 0
) -> list[RemoteCommand]:

    return list(
        db.scalars(
            select(RemoteCommand).where(
                RemoteCommand.computer_id == computer_id
            ).order_by(
                RemoteCommand.created_at.desc()
            ).limit(limit).offset(offset)
        ).all()
    )


def get_command_by_id(
    db: Session,
    command_id: int,
) -> RemoteCommand | None:
    return db.scalar(
        select(RemoteCommand).where(
            RemoteCommand.id == command_id
        )
    )


def submit_result(
    db: Session,
    command: RemoteCommand,
    result_data: CommandResultSubmit
) -> CommandResult:

    if command.result is not None:
        raise ValueError("Command result already submitted")
    
    result = CommandResult(
        command_id=command.id,
        success=result_data.success,
        message=result_data.message,
    )
    
    command.status = CommandStatus.executed if result_data.success else CommandStatus.failed

    try: 
        db.add(result)
        db.commit()
        db.refresh(result)

    except (IntegrityError, SQLAlchemyError) as e:
        db.rollback()
        raise ValueError(f"Failed to submit result: {e}")
    
    return result