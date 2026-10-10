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

from app.auth import get_current_user, require_permission
from app.database import get_db
from app.models.audit_log import AuditResult
from app.models.user import User
from app.schemas.user_schema import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.services import audit_service, user_service


DbSession = Annotated[
    Session,
    Depends(get_db),
]


router = APIRouter(
    prefix="/users",
    tags=["User Management"],
)


@router.get(
    "",
    response_model=UserListResponse,
)
def get_users(
    db: DbSession,
    _user: Annotated[User, Depends(require_permission("MANAGE_USERS"))],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=500),
    search: str | None = Query(default=None),
    role_id: int | None = Query(default=None, gt=0),
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    offset: int | None = Query(default=None, ge=0),
):
    """List users with multi-parameter filtering, search, and pagination."""
    if offset is not None and offset > 0 and page == 1:
        # Backward compatibility for offset-based queries
        page = (offset // limit) + 1

    result = user_service.get_users_paginated(
        db=db,
        page=page,
        limit=limit,
        search=search,
        role_id=role_id,
        role=role,
        status=status,
    )

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in result["items"]],
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
        total_pages=result["total_pages"],
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
def get_user(
    user_id: int,
    db: DbSession,
    _user: Annotated[User, Depends(require_permission("MANAGE_USERS"))],
):
    """Retrieve an individual user's details."""
    user = user_service.get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    user_data: UserCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission("MANAGE_USERS"))],
):
    """Create a new user account with validated fields and authorized role assignment."""
    try:
        user = user_service.create_user(
            db=db,
            user_data=user_data,
        )

        audit_service.log_action(
            db=db,
            action="CREATE_USER",
            target_type="user",
            target_id=user.id,
            result=AuditResult.success,
            user_id=current_user.id,
        )

        return UserResponse.model_validate(user)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User conflicts with existing data",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission("MANAGE_USERS"))],
):
    """Update user details, role assignment, or active status."""
    user = user_service.get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        updated_user = user_service.update_user(
            db=db,
            user=user,
            user_data=user_data,
            current_user=current_user,
        )

        audit_service.log_action(
            db=db,
            action="UPDATE_USER",
            target_type="user",
            target_id=user.id,
            result=AuditResult.success,
            user_id=current_user.id,
        )

        return UserResponse.model_validate(updated_user)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User conflicts with existing data",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: int,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission("MANAGE_USERS"))],
):
    """Delete a user account."""
    user = user_service.get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent an administrator from deleting their own currently authenticated account
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    try:
        user_service.delete_user(
            db,
            user,
        )

        audit_service.log_action(
            db=db,
            action="DELETE_USER",
            target_type="user",
            target_id=user_id,
            result=AuditResult.success,
            user_id=current_user.id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User cannot be deleted because related records exist",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        )