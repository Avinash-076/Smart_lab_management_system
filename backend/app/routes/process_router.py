from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)

from sqlalchemy.orm import Session

from app.auth import (
    get_current_agent,
    require_permission,
)

from app.database import get_db

from app.models.agent_credential import AgentCredential

from app.schemas.process_schema import (
    ProcessResponse,
    ProcessUpload,
)

from app.services import (
    computer_service,
    process_service,
)


DbSession = Annotated[
    Session,
    Depends(get_db),
]


router = APIRouter(
    prefix="/processes",
    tags=["Process Monitoring"],
)


# ============================================================
# AGENT PROCESS UPLOAD
# ============================================================

@router.post(
    "",
    response_model=list[ProcessResponse],
    status_code=status.HTTP_201_CREATED,
)
def upload_processes(
    process_data: ProcessUpload,
    db: DbSession,
    agent_credential: AgentCredential = Depends(
        get_current_agent
    ),
):

    computer_id = agent_credential.computer_id

    if computer_id is None:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Agent credential is not associated "
                "with a computer"
            ),
        )

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

        return process_service.replace_process_inventory(
            db=db,
            computer_id=computer_id,
            process_data=process_data,
        )

    except IntegrityError:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Process data conflicts "
                "with existing data"
            ),
        )

    except SQLAlchemyError:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save process data",
        )


# ============================================================
# GET PROCESSES
# ============================================================

@router.get(
    "/{computer_id}",
    response_model=list[ProcessResponse],
)
def get_processes(
    computer_id: int,
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
    limit: int = Query(
        default=500,
        ge=1,
        le=5000,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
):

    computer = computer_service.get_computer_by_id(
        db,
        computer_id,
    )

    if computer is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    return process_service.get_processes_for_computer(
        db=db,
        computer_id=computer_id,
        limit=limit,
        offset=offset,
    )


# ============================================================
# DELETE PROCESSES
# ============================================================

@router.delete(
    "/{computer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_processes(
    computer_id: int,
    db: DbSession,
    _user=Depends(
        require_permission("DELETE_COMPUTER")
    ),
):

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

        process_service.delete_processes_for_computer(
            db=db,
            computer_id=computer_id,
        )

    except SQLAlchemyError:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete process data",
        )