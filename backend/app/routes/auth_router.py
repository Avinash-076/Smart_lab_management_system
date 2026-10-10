from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    verify_password,
)
from app.database import get_db
from app.models.audit_log import AuditResult
from app.models.role_permission import RolePermission
from app.models.user import User
from app.schemas.auth_schema import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.role_schema import CurrentUserProfileResponse
from app.services import (
    audit_service,
    auth_service,
)


DbSession = Annotated[
    Session,
    Depends(get_db),
]


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    credentials: LoginRequest,
    db: DbSession,
    request: Request,
):
    username = credentials.username.strip()

    user = auth_service.get_user_by_username(
        db,
        username,
    )

    if (
        user is None
        or not verify_password(
            credentials.password,
            user.password_hash,
        )
    ):
        audit_service.log_action(
            db=db,
            action="LOGIN",
            result=AuditResult.failure,
            ip_address=(
                request.client.host
                if request.client
                else None
            ),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if not user.is_active:
        audit_service.log_action(
            db=db,
            action="LOGIN",
            result=AuditResult.failure,
            user_id=user.id,
            ip_address=(
                request.client.host
                if request.client
                else None
            ),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    audit_service.log_action(
        db=db,
        action="LOGIN",
        result=AuditResult.success,
        user_id=user.id,
        ip_address=(
            request.client.host
            if request.client
            else None
        ),
    )

    token_data = {
        "sub": str(user.id)
    }

    access_token = create_access_token(
        token_data
    )

    refresh_token = create_refresh_token(
        token_data
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
)
def refresh_access_token(
    payload: RefreshRequest,
    db: DbSession,
):
    decoded = decode_token(
        payload.refresh_token
    )

    if decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    user_id = decoded.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # Verify that the user still exists and is active
    user = auth_service.get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    new_access_token = create_access_token(
        {
            "sub": str(user.id)
        }
    )

    return AccessTokenResponse(
        access_token=new_access_token
    )


@router.get(
    "/me",
    response_model=CurrentUserProfileResponse,
)
def get_current_user_profile(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: DbSession,
):
    """Retrieve profile and permitted action codes for the currently authenticated user."""
    # Query permissions granted to this user's role
    allowed_perms = db.scalars(
        select(RolePermission.action_code).where(
            RolePermission.role_id == current_user.role_id,
            RolePermission.allowed.is_(True),
        )
    ).all()

    return CurrentUserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        email=current_user.email,
        role_id=current_user.role_id,
        role_name=current_user.role_name,
        is_active=current_user.is_active,
        permissions=list(allowed_perms),
    )