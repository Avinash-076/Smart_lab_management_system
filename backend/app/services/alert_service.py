import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session


from app.models.notification import Notification, NotificationSeverity
from app.models.system_metric import SystemMetric
from app.websocket.connection_manager import manager

CPU_WARNING, CPU_CRITICAL = 80, 90
RAM_WARNING, RAM_CRITICAL = 80, 90
DISK_WARNING, DISK_CRITICAL = 80, 90

COOLDOWN_MINUTES = 30

logger = logging.getLogger("slms")


def _recent_duplicate_exists(db: Session, computer_id: int, category: str) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=COOLDOWN_MINUTES)
    existing = db.scalar(
        select(Notification).where(
            Notification.computer_id == computer_id,
            Notification.category == category,
            Notification.created_at >= cutoff,
        )
    )
    return existing is not None


async def _create_notification(
    db: Session, computer_id: int, category: str, severity: NotificationSeverity, message: str
) -> None:
    if _recent_duplicate_exists(db, computer_id, category):
        return

    try:
        db.add(Notification(computer_id=computer_id, category=category, severity=severity, message=message))
        db.commit()
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        logger.warning(f"Failed to create notification for computer_id={computer_id}, category={category}")
        return   # <-- don't broadcast something that was never saved

    await manager.broadcast_to_dashboards({
        "type": "notification",
        "computer_id": computer_id,
        "message": message,
        "severity": severity.value,
        "category": category,
    })


async def _check_threshold(
    db: Session, computer_id: int, category: str, value: float, warning: float, critical: float
) -> None:
    if value >= critical:
        await _create_notification(db, computer_id, category, NotificationSeverity.critical, f"{category.upper()} usage critical: {value:.1f}%")
    elif value >= warning:
        await _create_notification(db, computer_id, category, NotificationSeverity.warning, f"{category.upper()} usage high: {value:.1f}%")


async def evaluate_metric(db: Session, computer_id: int, metric: SystemMetric) -> None:
    await _check_threshold(db, computer_id, "cpu", metric.cpu_usage, CPU_WARNING, CPU_CRITICAL)
    await _check_threshold(db, computer_id, "ram", metric.ram_usage, RAM_WARNING, RAM_CRITICAL)
    await _check_threshold(db, computer_id, "disk", metric.disk_usage, DISK_WARNING, DISK_CRITICAL)


async def notify_offline(db: Session, computer_id: int) -> None:
    await _create_notification(db, computer_id, "offline", NotificationSeverity.warning, "Computer went offline")