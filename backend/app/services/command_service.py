from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.remote_command import RemoteCommand, CommandStatus
from app.models.command_result import CommandResult
from app.schemas.command_schema import CommandCreate, CommandResultSubmit
from app.websocket.connection_manager import manager


async def create_and_dispatch_command(
    db: Session,
    computer_id: int,
    command_data: CommandCreate,
    issued_by: int,
) -> RemoteCommand:
    """
    Create a remote command and immediately send it to the client
    if the client is currently connected.

    If the client is offline, the command remains pending.
    """

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

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    delivered = await manager.send_to_client(
        computer_id,
        {
            "type": "command",
            "command_id": command.id,
            "command_type": command.command_type.value,
            "payload": command.payload,
        },
    )

    if delivered:
        command.status = CommandStatus.delivered

        try:
            db.commit()
            db.refresh(command)

        except SQLAlchemyError:
            db.rollback()
            raise

    return command


async def dispatch_pending_commands(
    db: Session,
    computer_id: int,
) -> int:
    """
    Send all pending commands to a client when it reconnects.

    Returns the number of commands successfully delivered.
    """

    commands = list(
        db.scalars(
            select(RemoteCommand)
            .where(
                RemoteCommand.computer_id == computer_id,
                RemoteCommand.status == CommandStatus.pending,
            )
            .order_by(RemoteCommand.created_at.asc())
        ).all()
    )

    delivered_count = 0

    for command in commands:
        delivered = await manager.send_to_client(
            computer_id,
            {
                "type": "command",
                "command_id": command.id,
                "command_type": command.command_type.value,
                "payload": command.payload,
            },
        )

        if not delivered:
            break

        command.status = CommandStatus.delivered
        delivered_count += 1

    if delivered_count > 0:
        try:
            db.commit()

        except SQLAlchemyError:
            db.rollback()
            raise

    return delivered_count


def get_commands_for_computer(
    db: Session,
    computer_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[RemoteCommand]:

    return list(
        db.scalars(
            select(RemoteCommand)
            .where(
                RemoteCommand.computer_id == computer_id
            )
            .order_by(
                RemoteCommand.created_at.desc()
            )
            .limit(limit)
            .offset(offset)
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


def cancel_command(
    db: Session,
    command: RemoteCommand,
) -> RemoteCommand:

    if command.status != CommandStatus.pending:
        raise ValueError(
            "Command cannot be cancelled because its "
            f"current status is '{command.status.value}'."
        )

    command.status = CommandStatus.cancelled

    try:
        db.commit()
        db.refresh(command)

    except SQLAlchemyError:
        db.rollback()
        raise

    return command


def submit_result(
    db: Session,
    command: RemoteCommand,
    result_data: CommandResultSubmit,
) -> CommandResult:

    if command.result is not None:
        raise ValueError(
            "Command result already submitted"
        )

    if command.status == CommandStatus.cancelled:
        raise ValueError(
            "Cancelled command cannot receive a result"
        )

    if command.status not in (
        CommandStatus.delivered,
        CommandStatus.executed,
        CommandStatus.failed,
    ):
        raise ValueError(
            "Command has not been delivered to the client"
        )

    result = CommandResult(
        command_id=command.id,
        success=result_data.success,
        message=result_data.message,
    )

    command.status = (
        CommandStatus.executed
        if result_data.success
        else CommandStatus.failed
    )

    try:
        db.add(result)
        db.commit()
        db.refresh(result)

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return result