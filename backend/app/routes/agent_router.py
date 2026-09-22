from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import (
    create_agent_access_token,
)
from app.database import get_db
from app.schemas.agent_schema import (
    AgentAuthRequest,
    AgentAuthResponse,
    AgentRegisterRequest,
    AgentRegisterResponse,
)
from app.services import agent_service


DbSession = Annotated[
    Session,
    Depends(get_db),
]


router = APIRouter(
    prefix="/agent",
    tags=["Agents"],
)


@router.post(
    "/register",
    response_model=AgentRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_agent(
    payload: AgentRegisterRequest,
    db: DbSession,
):
    try:

        result = (
            agent_service.register_with_enrollment_key(
                db=db,
                enrollment_key=payload.enrollment_key,
                device=payload.device,
            )
        )

    except ValueError as e:

        detail = str(e)

        if detail == "hostname_conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A computer with this hostname "
                    "already exists"
                ),
            )

        if detail == "mac_conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A computer with this MAC address "
                    "already exists"
                ),
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register agent",
        )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired enrollment key",
        )

    return result


@router.post(
    "/auth",
    response_model=AgentAuthResponse,
)
def auth_agent(
    payload: AgentAuthRequest,
    db: DbSession,
):

    try:

        credential = (
            agent_service.authenticate_agent(
                db=db,
                agent_id=payload.agent_id,
                client_secret=payload.client_secret,
            )
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent authentication failed",
        )

    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked credential",
        )

    token = create_agent_access_token(
        {
            "sub": credential.agent_id,
            "computer_id": credential.computer_id,
        }
    )

    return AgentAuthResponse(
        access_token=token,
        expires_in=15 * 60,
    )