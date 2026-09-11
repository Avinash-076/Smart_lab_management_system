from typing import Annotated
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.database import get_db
from app.models.computer import Computer
from app.models.agent_credential import AgentCredential
from app.schemas.computer_schema import (
    ComputerCreate,
    ComputerResponse,
    ComputerUpdate,
    ComputerPatch,
)
from app.services import audit_service

from app.services import computer_service
from app.auth import get_current_user, require_permission,get_current_agent
from app.models.audit_log import AuditResult

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(
    prefix="/clients",
    tags=["Computers"],
)

# routes from here

@router.get(
    "",
    response_model=list[ComputerResponse],
)
def get_all_computers(
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
    status: str | None = None,
):
    return computer_service.get_all_computers(db, status=status)


@router.get(
    "/{computer_id}",
    response_model=ComputerResponse,
)
def get_computer(
    computer_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
):
    computer = computer_service.get_computer_by_id(db, computer_id)

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    return computer


@router.put(
    "/{computer_id}",
    response_model=ComputerResponse,
)
def update_computer(
    computer_id: int,
    computer: ComputerUpdate,
    db: DbSession,
    _user = Depends(require_permission("UPDATE_COMPUTER")),
):
    existing_computer = computer_service.get_computer_by_id(
        db,
        computer_id,
    )

    if existing_computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found.",
        )
    if computer_service.has_identity_conflict(
        db,
        computer_id,
        computer.hostname,
        computer.mac_address,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hostname or MAC address already belongs to another computer.",
        )

    try:
        
        computer =  computer_service.update_computer(
            db,
            existing_computer,
            computer,
        )
    
        audit_service.log_action(
            db=db,
            action="UPDATE_COMPUTER",
            result=AuditResult.success,
            user_id=_user.id,
            target_type="computer",
            target_id=computer_id,
        )

        return computer
    

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Computer data conflicts with an existing computer.",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update computer.",
        )


@router.patch(
    "/{computer_id}",
    response_model=ComputerResponse,
)
def patch_computer(
    computer_id: int,
    computer: ComputerPatch,
    db: DbSession,
    _user = Depends(require_permission("UPDATE_COMPUTER")),
):
    existing_computer = computer_service.get_computer_by_id(
        db,
        computer_id,
    )

    if existing_computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found.",
        )

    if computer_service.has_patch_identity_conflict(
        db,
        computer_id,
        computer.hostname,
        computer.mac_address,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hostname or MAC address already belongs to another computer.",
        )

    try:
        computer = computer_service.patch_computer(
            db,
            existing_computer,
            computer,
        )

        audit_service.log_action(
            db=db,
            action="PATCH_COMPUTER",
            result=AuditResult.success,
            user_id=_user.id,
            target_type="computer",
            target_id=computer_id,
        )

        return computer

        

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Computer data conflicts with an existing computer.",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update computer.",
        )
    


@router.delete(
    "/{computer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_computer(
    computer_id: int,
    db: DbSession,
    _user = Depends(require_permission("DELETE_COMPUTER")),
) -> None:
    computer = computer_service.get_computer_by_id(
        db,
        computer_id,
    )

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found.",
        )

    try:
        computer_service.delete_computer(
            db,
            computer,
        )

        audit_service.log_action(
            db=db,
            action="DELETE_COMPUTER",
            result=AuditResult.success,
            user_id=_user.id,
            target_type="computer",
            target_id=computer_id,
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete computer.",
        )


# @router.post(
#     "/heartbeat",
#     status_code=status.HTTP_200_OK
# )
# def heartbeat(
#     agent_credential: AgentCredential = Depends(get_current_agent)
# ):

#     # if agent_credential.computer_id is None:
#     #     raise HTTPException(
#     #         status_code=status.HTTP_400_BAD_REQUEST,
#     #         detail="The credential has not completed registration yet."
#     #     )
    
#     # computer = computer_service.get_computer_by_id(db, agent_credential.computer_id)

#     # if computer is None:
#     #     raise HTTPException(
#     #         status_code=status.HTTP_404_NOT_FOUND,
#     #         detail="Computer is not found",
#     #     )

#     # try:
#     #     return computer_service.record_heartbeat(db, computer)
#     # except:
#     #     raise HTTPException(
#     #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
#     #         detail="Failed to record heartbeat",
#     #     )

#     # Kept temporarily as a lightweight "am I still authenticated" check.
#     # Will be replaced by POST /api/v1/metrics once metrics upload is built.
#     return {"message": "Credential valid"}

@router.post(
    "/heartbeat",
    status_code=status.HTTP_200_OK
)
def heartbeat(
    db: DbSession,
    agent_credential: AgentCredential = Depends(get_current_agent)
):
    if agent_credential.computer_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This credential has not completed registration yet.",
        )

    agent_credential.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Credential valid"}