from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_permission
from app.database import get_db
from app.models.user import User
from app.schemas.setting_schema import (
    SettingItemResponse,
    SettingsListResponse,
    SettingsResetRequest,
    SettingsUpdateRequest,
)
from app.services import setting_service

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get(
    "",
    response_model=SettingsListResponse,
    summary="Retrieve all application settings",
)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SettingsListResponse:
    """
    Retrieve all application configuration settings organized by category.
    Populates default values for any un-persisted items.
    """
    return setting_service.get_all_settings(db)


@router.get(
    "/{category}",
    response_model=list[SettingItemResponse],
    summary="Retrieve settings by category",
)
def get_settings_by_category(
    category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SettingItemResponse]:
    """
    Retrieve settings filtered by functional category (e.g. general, monitoring, notifications, agent).
    """
    items = setting_service.get_settings_by_category(db, category)
    if not items:
        if category.lower() not in setting_service.CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown category '{category}'. Available categories: {', '.join(setting_service.CATEGORIES)}",
            )
    return items


@router.patch(
    "",
    response_model=SettingsListResponse,
    summary="Update application settings",
)
@router.put(
    "",
    response_model=SettingsListResponse,
    summary="Update application settings",
)
def update_settings(
    request_data: dict[str, Any] | SettingsUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("MANAGE_SETTINGS")),
) -> SettingsListResponse:
    """
    Atomically update one or more application settings.
    Requires MANAGE_SETTINGS permission.
    Rejects unknown keys, invalid data types, or out-of-bounds values.
    """
    updates = (
        request_data.settings
        if isinstance(request_data, SettingsUpdateRequest)
        else request_data
    )
    if not isinstance(updates, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must be a dictionary of key-value pairs or a valid SettingsUpdateRequest",
        )

    client_ip = request.client.host if request.client else None

    try:
        return setting_service.update_settings(
            db=db,
            updates=updates,
            actor_id=current_user.id,
            actor_username=current_user.username,
            client_ip=client_ip,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/reset",
    response_model=SettingsListResponse,
    summary="Reset settings to system defaults",
)
def reset_settings(
    request_data: SettingsResetRequest | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("MANAGE_SETTINGS")),
) -> SettingsListResponse:
    """
    Reset specified settings (or all settings if no keys provided) to their catalog defaults.
    Requires MANAGE_SETTINGS permission.
    """
    keys = request_data.keys if request_data else None
    client_ip = request.client.host if request and request.client else None

    try:
        return setting_service.reset_settings(
            db=db,
            keys=keys,
            actor_id=current_user.id,
            actor_username=current_user.username,
            client_ip=client_ip,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
