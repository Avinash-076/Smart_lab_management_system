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


def _recent_duplicate_exists(
    db: Session,
    computer_id: int | None,
    category: str,
    severity: NotificationSeverity,
) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=COOLDOWN_MINUTES)
    query = select(Notification).where(
        Notification.category == category,
        Notification.created_at >= cutoff,
    )
    if computer_id is not None:
        query = query.where(Notification.computer_id == computer_id)
    else:
        query = query.where(Notification.computer_id.is_(None))

    existing = db.scalars(query.order_by(Notification.created_at.desc())).first()
    if existing is None:
        return False

    # Escalation: If new severity is critical and previous was warning/info, allow the alert
    if severity == NotificationSeverity.critical and existing.severity != NotificationSeverity.critical:
        return False

    return True


async def _create_notification(
    db: Session,
    computer_id: int | None,
    category: str,
    severity: NotificationSeverity,
    message: str,
    bypass_cooldown: bool = False,
) -> Notification | None:
    if not bypass_cooldown and _recent_duplicate_exists(db, computer_id, category, severity):
        return None

    notification = Notification(
        computer_id=computer_id,
        category=category,
        severity=severity,
        message=message,
    )

    try:
        db.add(notification)
        db.commit()
        db.refresh(notification)
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        logger.warning(f"Failed to create notification for computer_id={computer_id}, category={category}")
        return None

    comp_hostname = None
    if computer_id is not None:
        from app.models.computer import Computer
        comp = db.get(Computer, computer_id)
        if comp:
            comp_hostname = comp.hostname

    payload = {
        "type": "notification",
        "id": notification.id,
        "computer_id": notification.computer_id,
        "computer_hostname": comp_hostname,
        "category": notification.category,
        "severity": notification.severity.value,
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
        "notification": {
            "id": notification.id,
            "computer_id": notification.computer_id,
            "computer_hostname": comp_hostname,
            "category": notification.category,
            "severity": notification.severity.value,
            "message": notification.message,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
        },
    }

    try:
        await manager.broadcast_to_dashboards(payload)
    except Exception as exc:
        logger.warning(f"Failed to broadcast notification: {exc}")

    return notification


async def _check_threshold(
    db: Session, computer_id: int, category: str, value: float, warning: float, critical: float
) -> None:
    if value >= critical:
        await _create_notification(db, computer_id, category, NotificationSeverity.critical, f"{category.upper()} usage critical: {value:.1f}%")
    elif value >= warning:
        await _create_notification(db, computer_id, category, NotificationSeverity.warning, f"{category.upper()} usage high: {value:.1f}%")


async def evaluate_metric(db: Session, computer_id: int, metric: SystemMetric) -> None:
    from app.services.setting_service import get_setting_value

    cpu_thresh = float(get_setting_value(db, "cpu_threshold", CPU_CRITICAL))
    ram_thresh = float(get_setting_value(db, "ram_threshold", RAM_CRITICAL))
    disk_thresh = float(get_setting_value(db, "disk_threshold", DISK_CRITICAL))
    disk_alerts_enabled = bool(get_setting_value(db, "disk_alerts", True))

    await _check_threshold(db, computer_id, "cpu", metric.cpu_usage, max(10.0, cpu_thresh - 10.0), cpu_thresh)
    await _check_threshold(db, computer_id, "ram", metric.ram_usage, max(10.0, ram_thresh - 10.0), ram_thresh)
    if disk_alerts_enabled:
        await _check_threshold(db, computer_id, "disk", metric.disk_usage, max(10.0, disk_thresh - 10.0), disk_thresh)


async def notify_offline(db: Session, computer_id: int) -> None:
    from app.services.setting_service import get_setting_value

    offline_alerts_enabled = bool(get_setting_value(db, "offline_alerts", True))
    if not offline_alerts_enabled:
        return
    await _create_notification(db, computer_id, "offline", NotificationSeverity.warning, "Computer went offline")


async def notify_issue(
    db: Session,
    computer_id: int,
    title: str,
    severity: str = "warning",
) -> None:
    from app.services.setting_service import get_setting_value

    issue_alerts_enabled = bool(get_setting_value(db, "issue_alerts", True))
    if not issue_alerts_enabled:
        return

    sev = (
        NotificationSeverity.critical
        if str(severity).lower() == "critical"
        else NotificationSeverity.warning
    )
    await _create_notification(
        db=db,
        computer_id=computer_id,
        category="issue",
        severity=sev,
        message=f"Issue reported: {title[:180]}",
        bypass_cooldown=True,
    )


async def notify_system(
    db: Session,
    category: str,
    severity: NotificationSeverity,
    message: str,
) -> Notification | None:
    """Dispatch a lab-wide or administrative system notification not bound to a specific computer."""
    return await _create_notification(
        db=db,
        computer_id=None,
        category=category,
        severity=severity,
        message=message,
        bypass_cooldown=True,
    )


async def notify_software(
    db: Session,
    computer_id: int,
    software_names: list[str],
) -> Notification | None:
    """Dispatch notification when new software is installed, if software_alerts is enabled."""
    from app.services.setting_service import get_setting_value

    software_alerts_enabled = bool(get_setting_value(db, "software_alerts", False))
    if not software_alerts_enabled or not software_names:
        return None

    sample_str = ", ".join(software_names[:3])
    if len(software_names) > 3:
        sample_str += f" (+{len(software_names) - 3} more)"

    return await _create_notification(
        db=db,
        computer_id=computer_id,
        category="software",
        severity=NotificationSeverity.info,
        message=f"New software detected: {sample_str}",
        bypass_cooldown=True,
    )
