import math
from datetime import datetime, timezone
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.auth import hash_password
from app.models.role import Role
from app.models.user import User
from app.schemas.user_schema import (
    UserCreate,
    UserUpdate,
)


def get_user_by_id(
    db: Session,
    user_id: int,
) -> User | None:
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(joinedload(User.role))
    )


def get_user_by_username(
    db: Session,
    username: str,
) -> User | None:
    return db.scalar(
        select(User)
        .where(User.username == username)
        .options(joinedload(User.role))
    )


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    if not email:
        return None
    return db.scalar(
        select(User)
        .where(User.email == email)
        .options(joinedload(User.role))
    )


def get_users_paginated(
    db: Session,
    page: int = 1,
    limit: int = 25,
    search: str | None = None,
    role_id: int | None = None,
    role: str | None = None,
    status: str | None = None,
) -> dict:
    """Retrieve users with multi-parameter filtering, search, and pagination."""
    query = select(User).options(joinedload(User.role))
    count_query = select(func.count(User.id))

    # Apply search
    if search:
        search_pattern = f"%{search.strip()}%"
        search_filter = or_(
            User.username.ilike(search_pattern),
            User.full_name.ilike(search_pattern),
            User.email.ilike(search_pattern),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Filter by role_id
    if role_id is not None:
        query = query.where(User.role_id == role_id)
        count_query = count_query.where(User.role_id == role_id)

    # Filter by role name
    if role:
        query = query.join(Role).where(Role.name.ilike(role.strip()))
        count_query = count_query.join(Role).where(Role.name.ilike(role.strip()))

    # Filter by status (Active / Inactive)
    if status is not None:
        clean_status = status.strip().lower()
        if clean_status in ("active", "true", "1"):
            query = query.where(User.is_active.is_(True))
            count_query = count_query.where(User.is_active.is_(True))
        elif clean_status in ("inactive", "false", "0"):
            query = query.where(User.is_active.is_(False))
            count_query = count_query.where(User.is_active.is_(False))

    total = int(db.scalar(count_query) or 0)
    limit = max(1, min(limit, 500))
    total_pages = math.ceil(total / limit) if total > 0 else 1
    page = max(1, min(page, max(1, total_pages)))
    offset = (page - 1) * limit

    items = list(
        db.scalars(
            query.order_by(User.id.asc())
            .limit(limit)
            .offset(offset)
        ).all()
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


def get_users(
    db: Session,
    limit: int = 100,
    offset: int = 0,
) -> list[User]:
    """Legacy backward-compatible user list endpoint."""
    limit = min(max(limit, 1), 500)
    return list(
        db.scalars(
            select(User)
            .options(joinedload(User.role))
            .order_by(User.id.asc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


def count_users(
    db: Session,
) -> int:
    return int(
        db.scalar(
            select(func.count(User.id))
        )
        or 0
    )


def count_active_admins(
    db: Session,
) -> int:
    return int(
        db.scalar(
            select(func.count(User.id))
            .join(Role)
            .where(
                Role.name == "Administrator",
                User.is_active.is_(True),
            )
        )
        or 0
    )


def create_user(
    db: Session,
    user_data: UserCreate,
) -> User:
    username = user_data.username.strip()
    if not username:
        raise ValueError("Username cannot be empty")

    existing_user = get_user_by_username(db, username)
    if existing_user is not None:
        raise ValueError("Username already exists")

    email = user_data.email.strip() if user_data.email else None
    if email:
        existing_email = get_user_by_email(db, email)
        if existing_email is not None:
            raise ValueError("Email already in use by another user")

    role = db.get(Role, user_data.role_id)
    if role is None:
        raise LookupError("Role not found")

    full_name = user_data.full_name.strip() if user_data.full_name else None

    user = User(
        username=username,
        full_name=full_name,
        email=email,
        password_hash=hash_password(user_data.password),
        role_id=user_data.role_id,
        is_active=user_data.is_active,
        created_at=datetime.now(timezone.utc),
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


def update_user(
    db: Session,
    user: User,
    user_data: UserUpdate,
    current_user: User | None = None,
) -> User:
    if user_data.username is not None:
        username = user_data.username.strip()
        if not username:
            raise ValueError("Username cannot be empty")

        existing_user = db.scalar(
            select(User).where(
                User.username == username,
                User.id != user.id,
            )
        )
        if existing_user is not None:
            raise ValueError("Username already exists")
        user.username = username

    if user_data.full_name is not None:
        user.full_name = user_data.full_name.strip() or None

    if user_data.email is not None:
        email = user_data.email.strip() or None
        if email:
            existing_email = db.scalar(
                select(User).where(
                    User.email == email,
                    User.id != user.id,
                )
            )
            if existing_email is not None:
                raise ValueError("Email already in use by another user")
        user.email = email

    if user_data.password is not None:
        if len(user_data.password) < 6:
            raise ValueError("Password must be at least 6 characters")
        user.password_hash = hash_password(user_data.password)

    if user_data.role_id is not None:
        role = db.get(Role, user_data.role_id)
        if role is None:
            raise LookupError("Role not found")

        # Safety check: Cannot demote the last active Administrator
        if (
            user.role
            and user.role.name == "Administrator"
            and role.name != "Administrator"
        ):
            active_admins = count_active_admins(db)
            if active_admins <= 1:
                raise ValueError("Cannot demote the last active Administrator")

        user.role_id = user_data.role_id

    if user_data.is_active is not None:
        # Safety check: Prevent deactivating currently authenticated user
        if current_user and user.id == current_user.id and not user_data.is_active:
            raise ValueError("You cannot deactivate your own account")

        # Safety check: Prevent deactivating the last active Administrator
        if (
            user.role
            and user.role.name == "Administrator"
            and user.is_active
            and not user_data.is_active
        ):
            active_admins = count_active_admins(db)
            if active_admins <= 1:
                raise ValueError("Cannot deactivate the last active Administrator")

        user.is_active = user_data.is_active

    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


def delete_user(
    db: Session,
    user: User,
) -> None:
    user_count = count_users(db)
    if user_count <= 1:
        raise ValueError("Cannot delete the last user")

    if user.role and user.role.name == "Administrator":
        active_admins = count_active_admins(db)
        if active_admins <= 1:
            raise ValueError("Cannot delete the last active Administrator")

    try:
        from app.models.audit_log import AuditLog
        # Nullify nullable audit_logs.user_id references so audit history is preserved
        db.execute(
            update(AuditLog)
            .where(AuditLog.user_id == user.id)
            .values(user_id=None)
        )
        db.delete(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise