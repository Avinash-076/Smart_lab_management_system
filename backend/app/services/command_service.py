from datetime import datetime, timezone
from sqlalchemy import cast, distinct, func, or_, select, String
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.remote_command import RemoteCommand, CommandStatus
from app.models.command_result import CommandResult
from app.models.user import User
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


def _build_command_filter_conditions(
    computer_id: int,
    search: str | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    conditions = [RemoteCommand.computer_id == computer_id]

    if status and status.lower() != "all":
        status_clean = status.lower().strip()
        if status_clean in ("success", "executed"):
            conditions.append(RemoteCommand.status == CommandStatus.executed)
        elif status_clean in ("failed", "failure"):
            conditions.append(RemoteCommand.status == CommandStatus.failed)
        elif status_clean in ("pending",):
            conditions.append(RemoteCommand.status == CommandStatus.pending)
        elif status_clean in ("delivered",):
            conditions.append(RemoteCommand.status == CommandStatus.delivered)
        elif status_clean in ("cancelled", "canceled"):
            conditions.append(RemoteCommand.status == CommandStatus.cancelled)

    if start_date:
        conditions.append(RemoteCommand.created_at >= start_date)

    if end_date:
        conditions.append(RemoteCommand.created_at <= end_date)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(cast(RemoteCommand.command_type, String)).like(term),
                func.lower(RemoteCommand.payload).like(term),
                func.lower(CommandResult.message).like(term),
                func.lower(User.username).like(term),
            )
        )

    return conditions


def get_commands_for_computer(
    db: Session,
    computer_id: int,
    search: str | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[RemoteCommand]:
    conditions = _build_command_filter_conditions(
        computer_id=computer_id,
        search=search,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )

    query = (
        select(RemoteCommand)
        .outerjoin(CommandResult, RemoteCommand.id == CommandResult.command_id)
        .outerjoin(User, RemoteCommand.issued_by == User.id)
        .options(
            joinedload(RemoteCommand.result),
            joinedload(RemoteCommand.issuer),
        )
        .where(*conditions)
        .order_by(RemoteCommand.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(db.scalars(query).unique().all())


def get_commands_count_for_computer(
    db: Session,
    computer_id: int,
    search: str | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> int:
    conditions = _build_command_filter_conditions(
        computer_id=computer_id,
        search=search,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )

    query = (
        select(func.count(distinct(RemoteCommand.id)))
        .select_from(RemoteCommand)
        .outerjoin(CommandResult, RemoteCommand.id == CommandResult.command_id)
        .outerjoin(User, RemoteCommand.issued_by == User.id)
        .where(*conditions)
    )

    return db.scalar(query) or 0


def get_command_summary_for_computer(
    db: Session,
    computer_id: int,
) -> dict:
    status_counts = dict(
        db.execute(
            select(RemoteCommand.status, func.count(RemoteCommand.id))
            .where(RemoteCommand.computer_id == computer_id)
            .group_by(RemoteCommand.status)
        ).all()
    )

    executed_count = status_counts.get(CommandStatus.executed, 0)
    failed_count = status_counts.get(CommandStatus.failed, 0)
    pending_count = status_counts.get(CommandStatus.pending, 0)
    delivered_count = status_counts.get(CommandStatus.delivered, 0)
    cancelled_count = status_counts.get(CommandStatus.cancelled, 0)

    total_commands = sum(status_counts.values())

    success_rate = round((executed_count / total_commands * 100), 1) if total_commands > 0 else 0.0
    failure_rate = round((failed_count / total_commands * 100), 1) if total_commands > 0 else 0.0

    latest_cmd = db.scalar(
        select(RemoteCommand)
        .options(joinedload(RemoteCommand.result), joinedload(RemoteCommand.issuer))
        .where(
            RemoteCommand.computer_id == computer_id,
            RemoteCommand.status.in_([CommandStatus.executed, CommandStatus.failed]),
        )
        .order_by(RemoteCommand.created_at.desc())
        .limit(1)
    )
    last_execution_at = None
    if latest_cmd:
        last_execution_at = (
            latest_cmd.result.completed_at
            if latest_cmd.result and latest_cmd.result.completed_at
            else latest_cmd.created_at
        )

    recent_activities = list(
        db.scalars(
            select(RemoteCommand)
            .options(joinedload(RemoteCommand.result), joinedload(RemoteCommand.issuer))
            .where(RemoteCommand.computer_id == computer_id)
            .order_by(RemoteCommand.created_at.desc())
            .limit(5)
        ).unique().all()
    )

    return {
        "total_commands": total_commands,
        "successful_commands": executed_count,
        "failed_commands": failed_count,
        "pending_commands": pending_count,
        "delivered_commands": delivered_count,
        "cancelled_commands": cancelled_count,
        "success_rate_percent": success_rate,
        "failure_rate_percent": failure_rate,
        "last_execution_at": last_execution_at,
        "recent_activities": recent_activities,
    }


def get_command_by_id(
    db: Session,
    command_id: int,
) -> RemoteCommand | None:
    return db.scalar(
        select(RemoteCommand)
        .options(
            joinedload(RemoteCommand.result),
            joinedload(RemoteCommand.issuer),
        )
        .where(
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
        if (
            command.result.success == result_data.success
            and command.result.message == result_data.message
        ):
            return command.result
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

    duration_sec = result_data.duration_seconds
    if duration_sec is None and command.created_at:
        now_utc = datetime.now(timezone.utc)
        created = command.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        duration_sec = max(0.0, round((now_utc - created).total_seconds(), 2))

    result = CommandResult(
        command_id=command.id,
        success=result_data.success,
        message=result_data.message,
        duration_seconds=duration_sec,
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
        db.refresh(command)
        if command.result is not None:
            if (
                command.result.success == result_data.success
                and command.result.message == result_data.message
            ):
                return command.result
            raise ValueError(
                "Command result already submitted"
            )
        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return result