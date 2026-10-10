from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import case, delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.computer import Computer
from app.models.notification import Notification, NotificationSeverity
from app.schemas.notification_schema import NotificationCreate

logger = logging.getLogger("slms")


def get_notifications(
    db: Session,
    computer_id: int | None = None,
    category: str | None = None,
    severity: NotificationSeverity | None = None,
    is_read: bool | None = None,
    search: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[Notification]:
    """Retrieve notifications with optional filtering, search, and pagination."""
    query = (
        select(Notification)
        .options(joinedload(Notification.computer))
        .join(Computer, Notification.computer_id == Computer.id, isouter=True)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    )

    if computer_id is not None:
        query = query.where(Notification.computer_id == computer_id)

    if category is not None:
        query = query.where(Notification.category == category.lower())

    if severity is not None:
        query = query.where(Notification.severity == severity)

    if is_read is not None:
        query = query.where(Notification.is_read.is_(is_read))

    if start_time is not None:
        query = query.where(Notification.created_at >= start_time)

    if end_time is not None:
        query = query.where(Notification.created_at <= end_time)

    if search:
        search_pattern = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(Notification.message).like(search_pattern)
            | func.lower(Notification.category).like(search_pattern)
            | func.lower(Computer.hostname).like(search_pattern)
        )

    query = query.offset(offset).limit(limit)
    return db.scalars(query).all()


def get_notification_by_id(db: Session, notification_id: int) -> Notification | None:
    """Fetch a single notification by primary key."""
    query = (
        select(Notification)
        .options(joinedload(Notification.computer))
        .where(Notification.id == notification_id)
    )
    return db.scalar(query)


def get_notification_stats(db: Session, computer_id: int | None = None) -> dict[str, int]:
    """Compute aggregated notification stats directly from the database."""
    base_filter = []
    if computer_id is not None:
        base_filter.append(Notification.computer_id == computer_id)

    total_query = select(func.count(Notification.id))
    if base_filter:
        total_query = total_query.where(*base_filter)
    total = db.scalar(total_query) or 0

    unread_query = select(func.count(Notification.id)).where(Notification.is_read.is_(False))
    if base_filter:
        unread_query = unread_query.where(*base_filter)
    unread = db.scalar(unread_query) or 0

    critical_query = select(func.count(Notification.id)).where(
        Notification.severity == NotificationSeverity.critical
    )
    if base_filter:
        critical_query = critical_query.where(*base_filter)
    critical = db.scalar(critical_query) or 0

    warning_query = select(func.count(Notification.id)).where(
        Notification.severity == NotificationSeverity.warning
    )
    if base_filter:
        warning_query = warning_query.where(*base_filter)
    warning = db.scalar(warning_query) or 0

    info_query = select(func.count(Notification.id)).where(
        Notification.severity == NotificationSeverity.info
    )
    if base_filter:
        info_query = info_query.where(*base_filter)
    info = db.scalar(info_query) or 0

    return {
        "total": total,
        "unread": unread,
        "critical": critical,
        "warning": warning,
        "info": info,
    }


def mark_notification_read(db: Session, notification_id: int) -> Notification | None:
    """Mark an individual notification as read."""
    notification = get_notification_by_id(db, notification_id)
    if notification is None:
        return None

    if not notification.is_read:
        notification.is_read = True
        try:
            db.commit()
            db.refresh(notification)
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Failed to mark notification %d as read", notification_id)
            raise

    return notification


def mark_all_notifications_read(db: Session, computer_id: int | None = None) -> int:
    """Mark all unread notifications as read (optionally scoped to a computer)."""
    stmt = (
        update(Notification)
        .where(Notification.is_read.is_(False))
        .values(is_read=True)
    )
    if computer_id is not None:
        stmt = stmt.where(Notification.computer_id == computer_id)

    try:
        result = db.execute(stmt)
        db.commit()
        return result.rowcount
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to mark all notifications as read")
        raise


def delete_notification(db: Session, notification_id: int) -> bool:
    """Delete a notification by ID."""
    notification = db.get(Notification, notification_id)
    if notification is None:
        return False

    try:
        db.delete(notification)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to delete notification %d", notification_id)
        raise


def clear_read_notifications(db: Session, computer_id: int | None = None) -> int:
    """Delete all read notifications from the database."""
    stmt = delete(Notification).where(Notification.is_read.is_(True))
    if computer_id is not None:
        stmt = stmt.where(Notification.computer_id == computer_id)

    try:
        result = db.execute(stmt)
        db.commit()
        return result.rowcount
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to clear read notifications")
        raise
