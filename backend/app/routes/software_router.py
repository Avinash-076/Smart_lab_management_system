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
from app.schemas.software_schema import (
    SoftwareFleetItem,
    SoftwareFleetSummaryResponse,
    SoftwareResponse,
    SoftwareSummaryResponse,
    SoftwareUpload,
)
from app.services import (
    alert_service,
    computer_service,
    software_service,
)


DbSession = Annotated[
    Session,
    Depends(get_db),
]


router = APIRouter(
    prefix="/software",
    tags=["Software Inventory"],
)


@router.post(
    "",
    response_model=list[SoftwareResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_software_inventory(
    software_data: SoftwareUpload,
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
        records, new_names = software_service.replace_software_inventory(
            db=db,
            computer_id=computer_id,
            software_data=software_data,
        )
        if new_names:
            try:
                await alert_service.notify_software(db, computer_id, new_names)
            except Exception:
                pass
        return records

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Software inventory conflicts with existing data",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save software inventory",
        )


@router.get(
    "/fleet/summary",
    response_model=SoftwareFleetSummaryResponse,
)
def get_fleet_software_summary(
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
):
    return software_service.get_fleet_software_summary(db=db)


@router.get(
    "/fleet",
    response_model=list[SoftwareFleetItem],
)
def get_fleet_software_inventory(
    response: Response,
    db: DbSession,
    search: str | None = Query(default=None),
    publisher: str | None = Query(default=None),
    computer_id: int | None = Query(default=None),
    os_name: str | None = Query(default=None),
    sort_by: str = Query(default="name"),
    sort_order: str = Query(default="asc"),
    limit: int = Query(default=10, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
):
    items, total_count = software_service.get_fleet_software_items(
        db=db,
        search=search,
        publisher=publisher,
        computer_id=computer_id,
        os_name=os_name,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    response.headers["X-Total-Count"] = str(total_count)
    return items


@router.get(
    "/{computer_id}/summary",
    response_model=SoftwareSummaryResponse,
)
def get_software_summary(
    computer_id: int,
    db: DbSession,
    search: str | None = Query(default=None),
    publisher: str | None = Query(default=None),
    architecture: str | None = Query(default=None),
    date_range: str | None = Query(default=None),
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

    return software_service.get_software_summary_for_computer(
        db=db,
        computer_id=computer_id,
        search=search,
        publisher=publisher,
        architecture=architecture,
        date_range=date_range,
    )


@router.get(
    "/{computer_id}",
    response_model=list[SoftwareResponse],
)
def get_software_inventory(
    computer_id: int,
    response: Response,
    db: DbSession,
    search: str | None = Query(default=None),
    publisher: str | None = Query(default=None),
    architecture: str | None = Query(default=None),
    date_range: str | None = Query(default=None),
    sort_by: str = Query(default="name"),
    sort_order: str = Query(default="asc"),
    limit: int | None = Query(default=None, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
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

    total_count = software_service.get_software_count_for_computer(
        db=db,
        computer_id=computer_id,
        search=search,
        publisher=publisher,
        architecture=architecture,
        date_range=date_range,
    )
    response.headers["X-Total-Count"] = str(total_count)

    return software_service.get_software_for_computer(
        db=db,
        computer_id=computer_id,
        search=search,
        publisher=publisher,
        architecture=architecture,
        date_range=date_range,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )


@router.delete(
    "/{computer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_software_inventory(
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
        software_service.delete_software_for_computer(
            db=db,
            computer_id=computer_id,
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete software inventory",
        )