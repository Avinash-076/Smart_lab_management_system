from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_permission
from app.database import get_db
from app.models.audit_log import AuditResult
from app.models.user import User
from app.schemas.role_schema import (
    PermissionDefinition,
    RoleCreate,
    RolePermissionUpdateItem,
    RolePermissionsUpdateRequest,
    RoleResponse,
    RoleUpdate,
)
from app.services import audit_service, role_service


DbSession = Annotated[
    Session,
    Depends(get_db),
]


router = APIRouter(
    tags=["Role & Permission Management"],
)


@router.get(
    "/permissions",
    response_model=list[PermissionDefinition],
)
def get_permissions(
    _user: Annotated[User, Depends(require_permission("VIEW_COMPUTERS"))],
):
    """Retrieve catalog of all system permissions with descriptions and categories."""
    return role_service.get_available_permissions()


@router.get(
    "/roles",
    response_model=list[RoleResponse],
)
def get_roles(
    db: DbSession,
    _user: Annotated[User, Depends(require_permission("VIEW_COMPUTERS"))],
):
    """List all roles with user counts and assigned permissions."""
    return role_service.get_roles(db)


@router.get(
    "/roles/{role_id}",
    response_model=RoleResponse,
)
def get_role(
    role_id: int,
    db: DbSession,
    _user: Annotated[User, Depends(require_permission("VIEW_COMPUTERS"))],
):
    """Retrieve role details with permission matrix."""
    role = role_service.get_role_by_id(db, role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )
    user_count = role_service.get_role_user_count(db, role_id)
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        user_count=user_count,
        permissions=role.permissions,
    )


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_role(
    role_data: RoleCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission("MANAGE_ROLES"))],
):
    """Create a new role with optional initial permissions."""
    try:
        role = role_service.create_role(db, role_data)

        audit_service.log_action(
            db=db,
            action="CREATE_ROLE",
            target_type="role",
            target_id=role.id,
            result=AuditResult.success,
            user_id=current_user.id,
        )

        return RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            user_count=0,
            permissions=role.permissions,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role conflicts with existing data",
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create role",
        )


@router.patch(
    "/roles/{role_id}",
    response_model=RoleResponse,
)
def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission("MANAGE_ROLES"))],
):
    """Update role metadata (name, description)."""
    role = role_service.get_role_by_id(db, role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    try:
        updated_role = role_service.update_role(db, role, role_data)

        audit_service.log_action(
            db=db,
            action="UPDATE_ROLE",
            target_type="role",
            target_id=role.id,
            result=AuditResult.success,
            user_id=current_user.id,
        )

        user_count = role_service.get_role_user_count(db, role.id)
        return RoleResponse(
            id=updated_role.id,
            name=updated_role.name,
            description=updated_role.description,
            user_count=user_count,
            permissions=updated_role.permissions,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role conflicts with existing data",
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update role",
        )


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_role(
    role_id: int,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission("MANAGE_ROLES"))],
):
    """Delete a custom role if no users are currently assigned to it."""
    role = role_service.get_role_by_id(db, role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    try:
        role_service.delete_role(db, role)

        audit_service.log_action(
            db=db,
            action="DELETE_ROLE",
            target_type="role",
            target_id=role_id,
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
            detail="Role cannot be deleted because related records exist",
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete role",
        )


@router.put(
    "/roles/{role_id}/permissions",
    response_model=RoleResponse,
)
def update_role_permissions(
    role_id: int,
    payload: RolePermissionsUpdateRequest,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission("MANAGE_ROLES"))],
):
    """Update the permission matrix for a role."""
    role = role_service.get_role_by_id(db, role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    try:
        updated_perms = role_service.update_role_permissions(
            db,
            role,
            payload.permissions,
        )

        audit_service.log_action(
            db=db,
            action="UPDATE_ROLE_PERMISSIONS",
            target_type="role",
            target_id=role.id,
            result=AuditResult.success,
            user_id=current_user.id,
        )

        user_count = role_service.get_role_user_count(db, role.id)
        return RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            user_count=user_count,
            permissions=updated_perms,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Permission update conflicts with existing data",
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update role permissions",
        )
