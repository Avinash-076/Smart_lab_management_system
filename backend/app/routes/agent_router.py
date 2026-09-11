from fastapi import APIRouter, Depends, status, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_agent
from app.schemas.agent_schema import AgentRegisterRequest, AgentRegisterResponse, AgentAuthRequest, AgentAuthResponse
from app.services import agent_service
from app.auth import require_permission, create_agent_access_token

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/agent", tags=["Agents"])


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
        result = agent_service.register_with_enrollment_key(db, payload.enrollment_key, payload.device)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid  or expired enrollment key",
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
    credential = agent_service.authenticate_agent(db, payload.agent_id, payload.client_secret)

    if credential is None:
        raise HTTPException( 
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked credentail"
        )

    token = create_agent_access_token(
        {
            "sub": credential.agent_id,
            "computer_id": credential.computer_id
        }
    )

    return AgentAuthResponse(access_token=token, expires_in=15*60)