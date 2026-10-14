from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
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
    ProcessRankingsResponse,
    ProcessResponse,
    ProcessSummaryResponse,
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
# GET PROCESS SUMMARY
# ============================================================

@router.get(
    "/{computer_id}/summary",
    response_model=ProcessSummaryResponse,
)
def get_process_summary(
    computer_id: int,
    db: DbSession,
    search: str | None = Query(default=None),
    process_status: str | None = Query(default=None, alias="status"),
    cpu_min: float | None = Query(default=None),
    memory_min_mb: float | None = Query(default=None),
    user: str | None = Query(default=None),
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
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

    return process_service.get_process_summary_for_computer(
        db=db,
        computer_id=computer_id,
        search=search,
        status=process_status,
        cpu_min=cpu_min,
        memory_min_mb=memory_min_mb,
        user=user,
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
    response: Response,
    db: DbSession,
    search: str | None = Query(default=None),
    process_status: str | None = Query(default=None, alias="status"),
    cpu_min: float | None = Query(default=None),
    memory_min_mb: float | None = Query(default=None),
    user: str | None = Query(default=None),
    sort_by: str = Query(default="cpu_percent"),
    sort_order: str = Query(default="desc"),
    limit: int | None = Query(
        default=500,
        ge=1,
        le=5000,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
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

    total_count = process_service.get_processes_count_for_computer(
        db=db,
        computer_id=computer_id,
        search=search,
        status=process_status,
        cpu_min=cpu_min,
        memory_min_mb=memory_min_mb,
        user=user,
    )
    response.headers["X-Total-Count"] = str(total_count)

    return process_service.get_processes_for_computer(
        db=db,
        computer_id=computer_id,
        search=search,
        status=process_status,
        cpu_min=cpu_min,
        memory_min_mb=memory_min_mb,
        user=user,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{computer_id}/rankings",
    response_model=ProcessRankingsResponse,
)
def get_process_rankings(
    computer_id: int,
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
    limit: int = Query(
        default=5,
        ge=1,
        le=20,
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

    return process_service.get_process_rankings(
        db=db,
        computer_id=computer_id,
        limit=limit,
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