from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
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
    SoftwareResponse,
    SoftwareUpload,
)
from app.services import (
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
def upload_software_inventory(
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
        return software_service.replace_software_inventory(
            db=db,
            computer_id=computer_id,
            software_data=software_data,
        )

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
    "/{computer_id}",
    response_model=list[SoftwareResponse],
)
def get_software_inventory(
    computer_id: int,
    db: DbSession,
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

    return software_service.get_software_for_computer(
        db=db,
        computer_id=computer_id,
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