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

from app.auth import require_permission
from app.database import get_db
from app.models.maintenance import MaintenanceStatus
from app.schemas.maintenance_schema import (
    MaintenanceCreate,
    MaintenanceResponse,
    MaintenanceUpdate,
)
from app.services import (
    computer_service,
    maintenance_service,
)


DbSession = Annotated[
    Session,
    Depends(get_db),
]


router = APIRouter(
    prefix="/maintenance",
    tags=["Maintenance Records"],
)


@router.get(
    "",
    response_model=list[MaintenanceResponse],
)
def get_maintenance_records(
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
    computer_id: int | None = Query(
        default=None,
        gt=0,
    ),
    maintenance_status: MaintenanceStatus | None = Query(
        default=None,
        alias="status",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
):

    return maintenance_service.get_maintenance_records(
        db=db,
        computer_id=computer_id,
        maintenance_status=maintenance_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{maintenance_id}",
    response_model=MaintenanceResponse,
)
def get_maintenance(
    maintenance_id: int,
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
):

    record = maintenance_service.get_maintenance_by_id(
        db,
        maintenance_id,
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance record not found",
        )

    return record


@router.post(
    "",
    response_model=MaintenanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_maintenance(
    maintenance_data: MaintenanceCreate,
    db: DbSession,
    user=Depends(
        require_permission("UPDATE_COMPUTER")
    ),
):

    computer = computer_service.get_computer_by_id(
        db,
        maintenance_data.computer_id,
    )

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    try:
        return maintenance_service.create_maintenance(
            db=db,
            maintenance_data=maintenance_data,
            created_by=user.id,
        )

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to create maintenance record",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save maintenance record",
        )


@router.patch(
    "/{maintenance_id}",
    response_model=MaintenanceResponse,
)
def update_maintenance(
    maintenance_id: int,
    maintenance_data: MaintenanceUpdate,
    db: DbSession,
    _user=Depends(
        require_permission("UPDATE_COMPUTER")
    ),
):

    record = maintenance_service.get_maintenance_by_id(
        db,
        maintenance_id,
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance record not found",
        )

    try:
        return maintenance_service.update_maintenance(
            db=db,
            record=record,
            maintenance_data=maintenance_data,
        )

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid maintenance update",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update maintenance record",
        )


@router.delete(
    "/{maintenance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_maintenance(
    maintenance_id: int,
    db: DbSession,
    _user=Depends(
        require_permission("DELETE_COMPUTER")
    ),
):

    record = maintenance_service.get_maintenance_by_id(
        db,
        maintenance_id,
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance record not found",
        )

    try:
        maintenance_service.delete_maintenance(
            db,
            record,
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete maintenance record",
        )