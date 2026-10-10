from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database import get_db
from app.models.notification import NotificationSeverity
from app.schemas.notification_schema import (
    NotificationBulkDeleteResponse,
    NotificationBulkReadResponse,
    NotificationResponse,
    NotificationStatsResponse,
)
from app.services import notification_service

DbSession = Annotated[
    Session,
    Depends(get_db),
]

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "/stats",
    response_model=NotificationStatsResponse,
)
def get_notification_statistics(
    db: DbSession,
    computer_id: int | None = Query(default=None),
    _user=Depends(require_permission("VIEW_COMPUTERS")),
):
    """Retrieve summary counts for unread and severity-scoped notifications."""
    return notification_service.get_notification_stats(db, computer_id=computer_id)


@router.get(
    "/",
    response_model=list[NotificationResponse],
)
def get_all_notifications(
    db: DbSession,
    computer_id: int | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: NotificationSeverity | None = Query(default=None),
    unread_only: bool = Query(default=False),
    is_read: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_permission("VIEW_COMPUTERS")),
):
    """Fetch all notifications with optional filters for category, severity, status, search, and pagination."""
    filter_is_read = is_read
    if unread_only:
        filter_is_read = False

    return notification_service.get_notifications(
        db=db,
        computer_id=computer_id,
        category=category,
        severity=severity,
        is_read=filter_is_read,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/read-all",
    response_model=NotificationBulkReadResponse,
)
def mark_all_as_read(
    db: DbSession,
    computer_id: int | None = Query(default=None),
    _user=Depends(require_permission("VIEW_COMPUTERS")),
):
    """Mark all unread notifications as read."""
    count = notification_service.mark_all_notifications_read(db, computer_id=computer_id)
    return NotificationBulkReadResponse(updated_count=count)


@router.delete(
    "/clear-read",
    response_model=NotificationBulkDeleteResponse,
)
def clear_all_read(
    db: DbSession,
    computer_id: int | None = Query(default=None),
    _user=Depends(require_permission("VIEW_COMPUTERS")),
):
    """Delete all read notifications."""
    count = notification_service.clear_read_notifications(db, computer_id=computer_id)
    return NotificationBulkDeleteResponse(deleted_count=count)


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
)
def get_single_notification(
    notification_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
):
    """Fetch details for a specific notification."""
    notification = notification_service.get_notification_by_id(db, notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return notification


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_read(
    notification_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
):
    """Mark an individual notification as read."""
    notification = notification_service.mark_notification_read(db, notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return notification


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_notification_record(
    notification_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
):
    """Delete an individual notification."""
    success = notification_service.delete_notification(db, notification_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )