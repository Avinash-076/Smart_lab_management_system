from datetime import datetime
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from app.models.audit_log import AuditLog, AuditResult
from app.models.user import User


def log_action(
    db: Session,
    result: AuditResult,
    action: str,
    user_id: int | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Persist an audit log entry transactionally.
    Sanitizes string inputs to prevent log injection and bounds lengths.
    """
    clean_action = str(action).strip()[:100] if action else "UNKNOWN"
    clean_target_type = str(target_type).strip()[:50] if target_type else None
    clean_ip = str(ip_address).strip()[:45] if ip_address else None

    entry = AuditLog(
        user_id=user_id,
        action=clean_action,
        result=result,
        target_type=clean_target_type,
        target_id=target_id,
        ip_address=clean_ip,
    )

    try:
        db.add(entry)
        db.commit()
        db.refresh(entry)
    except SQLAlchemyError:
        db.rollback()
        raise

    return entry


def get_audit_logs(
    db: Session,
    page: int = 1,
    limit: int = 50,
    action: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    user_id: int | None = None,
    result: AuditResult | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[AuditLog], int]:
    """
    Retrieve paginated audit logs with optional filtering and search.
    Returns (items, total_count).
    """
    base_query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    filters = []

    if action:
        filters.append(AuditLog.action == action.strip())

    if target_type:
        filters.append(AuditLog.target_type == target_type.strip())

    if target_id is not None:
        filters.append(AuditLog.target_id == target_id)

    if user_id is not None:
        filters.append(AuditLog.user_id == user_id)

    if result is not None:
        filters.append(AuditLog.result == result)

    if date_from is not None:
        filters.append(AuditLog.created_at >= date_from)

    if date_to is not None:
        filters.append(AuditLog.created_at <= date_to)

    if search:
        search_term = f"%{search.strip()}%"
        # Join with User for username searching
        base_query = base_query.outerjoin(AuditLog.user)
        count_query = count_query.outerjoin(AuditLog.user)
        search_filter = or_(
            AuditLog.action.ilike(search_term),
            AuditLog.target_type.ilike(search_term),
            AuditLog.ip_address.ilike(search_term),
            User.username.ilike(search_term),
        )
        filters.append(search_filter)

    if filters:
        base_query = base_query.where(*filters)
        count_query = count_query.where(*filters)

    total = db.scalar(count_query) or 0

    offset = (page - 1) * limit
    stmt = (
        base_query
        .options(joinedload(AuditLog.user))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )

    items = list(db.scalars(stmt).all())
    return items, total


def get_audit_log_by_id(
    db: Session,
    log_id: int,
) -> AuditLog | None:
    """
    Retrieve a single audit log entry by ID.
    """
    return db.scalar(
        select(AuditLog)
        .options(joinedload(AuditLog.user))
        .where(AuditLog.id == log_id)
    )