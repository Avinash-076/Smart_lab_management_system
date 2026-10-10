from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_db
from app.auth import (
    require_permission,
    get_current_agent,
)
from app.models.agent_credential import AgentCredential
from app.models.audit_log import AuditResult
from app.schemas.command_schema import (
    CommandCreate,
    CommandResponse,
    CommandResultSubmit,
    CommandResultResponse,
)
from app.services import (
    audit_service,
    command_service,
    computer_service,
)


DbSession = Annotated[
    Session,
    Depends(get_db),
]


router = APIRouter(
    prefix="/commands",
    tags=["Commands"],
)


@router.post(
    "/{computer_id}",
    response_model=CommandResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_command(
    computer_id: int,
    command_data: CommandCreate,
    db: DbSession,
    _user=Depends(
        require_permission("ISSUE_COMMAND")
    ),
):
    """
    Create a remote command for a computer.

    If the client is online, the command is immediately
    delivered through WebSocket.

    If the client is offline, the command remains pending.
    """

    computer = computer_service.get_computer_by_id(
        db,
        computer_id,
    )

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    try:
        command = await command_service.create_and_dispatch_command(
            db=db,
            computer_id=computer_id,
            command_data=command_data,
            issued_by=_user.id,
        )

        audit_service.log_action(
            db=db,
            result=AuditResult.success,
            action=f"ISSUE_COMMAND_{command.command_type.value.upper()}",
            user_id=_user.id,
            target_type="COMPUTER",
            target_id=computer_id,
        )

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid command data",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to issue command",
        )

    return command


@router.get(
    "/detail/{command_id}",
    response_model=CommandResponse,
)
def get_command_details(
    command_id: int,
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
):
    """
    Get detailed status and result for a single command.
    """

    command = command_service.get_command_by_id(
        db=db,
        command_id=command_id,
    )

    if command is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found",
        )

    return command


@router.get(
    "/{computer_id}",
    response_model=list[CommandResponse],
)
def get_command_history(
    computer_id: int,
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
):
    """
    Get command history for a computer.
    """

    computer = computer_service.get_computer_by_id(
        db,
        computer_id,
    )

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    return command_service.get_commands_for_computer(
        db=db,
        computer_id=computer_id,
    )


@router.post(
    "/{command_id}/cancel",
    response_model=CommandResponse,
)
def cancel_command(
    command_id: int,
    db: DbSession,
    _user=Depends(
        require_permission("ISSUE_COMMAND")
    ),
):
    """
    Cancel a command that is still pending.
    """

    command = command_service.get_command_by_id(
        db=db,
        command_id=command_id,
    )

    if command is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found",
        )

    try:
        cancelled_command = command_service.cancel_command(
            db=db,
            command=command,
        )

        audit_service.log_action(
            db=db,
            result=AuditResult.success,
            action="CANCEL_COMMAND",
            user_id=_user.id,
            target_type="COMMAND",
            target_id=command_id,
        )

        return cancelled_command

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel command",
        )


@router.post(
    "/{command_id}/result",
    response_model=CommandResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_command_result(
    db: DbSession,
    command_id: int,
    result_data: CommandResultSubmit,
    agent_credential: AgentCredential = Depends(
        get_current_agent
    ),
):
    """
    Receive command execution result from the client agent.
    """

    command = command_service.get_command_by_id(
        db,
        command_id,
    )

    if (
        command is None
        or command.computer_id
        != agent_credential.computer_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found",
        )

    try:
        already_had_result = command.result is not None
        result = command_service.submit_result(
            db,
            command,
            result_data,
        )

        if not already_had_result:
            audit_service.log_action(
                db=db,
                result=AuditResult.success if result_data.success else AuditResult.failure,
                action=f"COMMAND_{'EXECUTED' if result_data.success else 'FAILED'}_{command.command_type.value.upper()}",
                user_id=None,
                target_type="COMMAND",
                target_id=command_id,
            )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid command result",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save command result",
        )