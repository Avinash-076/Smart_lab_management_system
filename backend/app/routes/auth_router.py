from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.auth import create_access_token, create_refresh_token, decode_token, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth_schema import AccessTokenResponse, LoginRequest, RefreshRequest, TokenResponse

from app.services import auth_service
from app.services import audit_service
from app.models.audit_log import AuditResult


DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: DbSession, request: Request):
    user = auth_service.get_user_by_username(db, credentials.username)

    if user is None or not verify_password(credentials.password, user.password_hash):

        audit_service.log_action(
            db = db,
            action = "LOGIN",
            result = AuditResult.failure,
            ip_address = request.client.host if request.client else None,
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    audit_service.log_action(
        db = db,
        action = "LOGIN",
        result = AuditResult.success,
        user_id = user.id,
        ip_address = request.client.host if request.client else None,
    )

    token_data = {"sub": str(user.id)}

    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data)
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_access_token(payload: RefreshRequest):
    decoded = decode_token(payload.refresh_token)

    if decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user_id = decoded.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    new_access_token = create_access_token({"sub": user_id})

    return AccessTokenResponse(access_token = new_access_token)

