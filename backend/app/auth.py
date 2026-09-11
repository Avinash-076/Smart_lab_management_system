from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import hashlib
import secrets

from app.config import settings
from app.database import get_db
from app.models.user import User

from sqlalchemy import select
from app.models.role_permission import RolePermission
from app.models.agent_credential import AgentCredential
from app.models.audit_log import AuditResult

# PASSWORD HASHING 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# TOKEN CREATION

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        hours=settings.refresh_token_expire_hours
    )

    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

AGENT_TOKEN_EXPIRE_MINUTES = 15

def create_agent_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=AGENT_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "agent"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# CURRENT-USER DEPENDENCY


DbSession = Annotated[Session, Depends(get_db)]

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.get(User, int(user_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user

def require_permission(action_code: str):
    def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        db: DbSession,
    ) -> User:
        permission = db.scalar(
            select(RolePermission).where(
                RolePermission.role_id == current_user.role_id,
                RolePermission.action_code == action_code,
                RolePermission.allowed == True
            )
        )

        if permission is None:

            from app.services import audit_service

            audit_service.log_action(
                db = db,
                action = action_code,
                result = AuditResult.failure,
                user_id = current_user.id,
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your role does not have permission: {action_code}",
            )

        return current_user

    return dependency




# client agent

def get_current_agent(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: DbSession
) -> AgentCredential:
    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "agent":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    agent_id = payload.get("sub")

    credential = db.scalar(
        select(AgentCredential).where(
            AgentCredential.agent_id == agent_id,
            AgentCredential.is_active == True,
        )
    )

    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked agent credential",
        )


    return credential

# token for enrollemtn and agent credential

def generate_token(prefix: str = "", nbytes: int = 32) -> str:
    return f"{prefix}{secrets.token_hex(nbytes)}"

def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def verify_secret(value: str, hashed: str) -> bool:
    return secrets.compare_digest(hash_secret(value), hashed)

PRODUCT_KEY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O/1/I/L

def generate_enrollment_key(segments: int = 4, segment_len: int = 4 ) -> str:
    parts = [
        "".join(secrets.choice(PRODUCT_KEY_ALPHABET) for _ in range(segment_len))
        for _ in range(segments)
    ]

    return "SLMS-" + "-".join(parts)

def normalize_key(raw: str) -> str:
    return raw.strip().upper().replace(" ","")

def ensure_utc(dt: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip, so normalize before comparing."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt