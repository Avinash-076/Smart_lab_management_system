from datetime import datetime, timedelta, timezone
from typing import Annotated

import hashlib
import secrets

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.agent_credential import AgentCredential
from app.models.audit_log import AuditResult
from app.models.role_permission import RolePermission
from app.models.user import User


# ============================================================
# PASSWORD HASHING
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


# ============================================================
# USER ACCESS TOKEN
# ============================================================

def create_access_token(data: dict) -> str:

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    )

    to_encode.update(
        {
            "exp": expire,
            "type": "access",
        }
    )

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


# ============================================================
# USER REFRESH TOKEN
# ============================================================

def create_refresh_token(data: dict) -> str:

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            hours=settings.refresh_token_expire_hours
        )
    )

    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
        }
    )

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


# ============================================================
# AGENT ACCESS TOKEN
# ============================================================

AGENT_TOKEN_EXPIRE_MINUTES = 15


def create_agent_access_token(data: dict) -> str:

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=AGENT_TOKEN_EXPIRE_MINUTES
        )
    )

    to_encode.update(
        {
            "exp": expire,
            "type": "agent",
        }
    )

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


# ============================================================
# TOKEN DECODING
# ============================================================

def decode_token(token: str) -> dict:

    try:

        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[
                settings.jwt_algorithm
            ],
        )

    except JWTError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )


# ============================================================
# DATABASE SESSION
# ============================================================

DbSession = Annotated[
    Session,
    Depends(get_db),
]


# ============================================================
# BEARER AUTHENTICATION
# ============================================================

bearer_scheme = HTTPBearer()


# ============================================================
# CURRENT USER
# ============================================================

def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
    db: DbSession,
) -> User:

    token = credentials.credentials

    payload = decode_token(token)

    # --------------------------------------------------------
    # Token must be a USER access token.
    # --------------------------------------------------------

    if payload.get("type") != "access":

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # --------------------------------------------------------
    # Extract user ID.
    # --------------------------------------------------------

    user_id = payload.get("sub")

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

    # --------------------------------------------------------
    # Find user.
    # --------------------------------------------------------

    user = db.get(
        User,
        user_id,
    )

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return user


# ============================================================
# PERMISSION CHECK
# ============================================================

def require_permission(
    action_code: str,
):

    def dependency(
        current_user: Annotated[
            User,
            Depends(get_current_user),
        ],
        db: DbSession,
    ) -> User:

        permission = db.scalar(
            select(RolePermission).where(
                RolePermission.role_id
                == current_user.role_id,
                RolePermission.action_code
                == action_code,
                RolePermission.allowed.is_(True),
            )
        )

        if permission is None:

            from app.services import audit_service

            audit_service.log_action(
                db=db,
                action=action_code,
                result=AuditResult.failure,
                user_id=current_user.id,
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Your role does not have "
                    f"permission: {action_code}"
                ),
            )

        return current_user

    return dependency


# ============================================================
# CURRENT AGENT
# ============================================================

def get_current_agent(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
    db: DbSession,
) -> AgentCredential:

    token = credentials.credentials

    payload = decode_token(token)

    # --------------------------------------------------------
    # Token must be an AGENT token.
    # --------------------------------------------------------

    if payload.get("type") != "agent":

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # --------------------------------------------------------
    # Extract agent ID.
    # --------------------------------------------------------

    agent_id = payload.get("sub")

    if not agent_id:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent token payload",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # --------------------------------------------------------
    # Extract computer ID from token.
    # --------------------------------------------------------

    token_computer_id = payload.get(
        "computer_id"
    )

    if token_computer_id is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent token payload",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    try:
        token_computer_id = int(
            token_computer_id
        )

    except (TypeError, ValueError):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid computer identifier",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # --------------------------------------------------------
    # Find active credential.
    # --------------------------------------------------------

    credential = db.scalar(
        select(AgentCredential).where(
            AgentCredential.agent_id == agent_id,
            AgentCredential.is_active.is_(True),
        )
    )

    if credential is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked agent credential",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # --------------------------------------------------------
    # Ensure the token belongs to the same computer
    # as the stored credential.
    # --------------------------------------------------------

    if credential.computer_id != token_computer_id:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent computer mismatch",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return credential


# ============================================================
# SECRET / TOKEN GENERATION
# ============================================================

def generate_token(
    prefix: str = "",
    nbytes: int = 32,
) -> str:

    return (
        f"{prefix}"
        f"{secrets.token_hex(nbytes)}"
    )


def hash_secret(
    value: str,
) -> str:

    return hashlib.sha256(
        value.encode()
    ).hexdigest()


def verify_secret(
    value: str,
    hashed: str,
) -> bool:

    return secrets.compare_digest(
        hash_secret(value),
        hashed,
    )


# ============================================================
# ENROLLMENT KEY
# ============================================================

PRODUCT_KEY_ALPHABET = (
    "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
)


def generate_enrollment_key(
    segments: int = 4,
    segment_len: int = 4,
) -> str:

    parts = [
        "".join(
            secrets.choice(
                PRODUCT_KEY_ALPHABET
            )
            for _ in range(segment_len)
        )
        for _ in range(segments)
    ]

    return (
        "SLMS-"
        + "-".join(parts)
    )


def normalize_key(
    raw: str,
) -> str:

    return (
        raw
        .strip()
        .upper()
        .replace(" ", "")
    )


def ensure_utc(
    dt: datetime,
) -> datetime:
    """
    SQLite can remove timezone information when
    storing datetime values.

    This function guarantees that the returned
    datetime is timezone-aware UTC.
    """

    if dt.tzinfo is None:

        return dt.replace(
            tzinfo=timezone.utc
        )

    return dt