from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

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

    return db.get(
        User,
        user_id,
    )


def get_user_by_username(
    db: Session,
    username: str,
) -> User | None:

    return db.scalar(
        select(User).where(
            User.username == username
        )
    )


def get_users(
    db: Session,
    limit: int = 100,
    offset: int = 0,
) -> list[User]:

    limit = min(
        max(limit, 1),
        500,
    )

    return list(
        db.scalars(
            select(User)
            .order_by(User.id.asc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


def get_role_by_id(
    db: Session,
    role_id: int,
) -> Role | None:

    return db.get(
        Role,
        role_id,
    )


def create_user(
    db: Session,
    user_data: UserCreate,
) -> User:

    username = user_data.username.strip()

    existing_user = get_user_by_username(
        db,
        username,
    )

    if existing_user is not None:
        raise ValueError(
            "Username already exists"
        )

    role = get_role_by_id(
        db,
        user_data.role_id,
    )

    if role is None:
        raise LookupError(
            "Role not found"
        )

    user = User(
        username=username,
        password_hash=hash_password(
            user_data.password
        ),
        role_id=user_data.role_id,
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
) -> User:

    if user_data.username is not None:

        username = user_data.username.strip()

        existing_user = db.scalar(
            select(User).where(
                User.username == username,
                User.id != user.id,
            )
        )

        if existing_user is not None:
            raise ValueError(
                "Username already exists"
            )

        user.username = username

    if user_data.password is not None:

        user.password_hash = hash_password(
            user_data.password
        )

    if user_data.role_id is not None:

        role = get_role_by_id(
            db,
            user_data.role_id,
        )

        if role is None:
            raise LookupError(
                "Role not found"
            )

        user.role_id = user_data.role_id

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


def count_users(
    db: Session,
) -> int:

    return int(
        db.scalar(
            select(
                func.count(User.id)
            )
        )
        or 0
    )


def delete_user(
    db: Session,
    user: User,
) -> None:

    user_count = count_users(db)

    if user_count <= 1:
        raise ValueError(
            "Cannot delete the last user"
        )

    try:
        db.delete(user)
        db.commit()

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise