from app.auth import require_permission
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db 
from app.models.notification import Notification
from app.schemas.notification_schema import NotificationResponse

Dbsession =  Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model = list[NotificationResponse])
def get_all_notifications(
    db:Dbsession,
    _user = Depends(require_permission("VIEW_COMPUTERS")),
    unread_only: bool = False,
    limit: int = Query(default=100, le=500)
):

    query = select(Notification).order_by(Notification.created_at.desc()).limit(limit)

    if unread_only:
        query = query.where(
            Notification.is_read.is_(False)
        )
    
    return list(db.scalars(query).all())


@router.patch("/{notification_id}/read", response_model = NotificationResponse)
def mark_read(
    notification_id: int,
    db: Dbsession,
    _user = Depends(require_permission("VIEW_COMPUTERS")),
):
    notification = db.get(Notification, notification_id)

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with ID {notification_id} not found"
        )

    notification.is_read = True
    
    db.commit()
    db.refresh(notification)
    
    return notification