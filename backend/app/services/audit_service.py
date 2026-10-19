import csv
import io
from datetime import datetime, timezone, timedelta
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from app.models.audit_log import AuditLog, AuditResult
from app.models.user import User


def _sanitize_csv_cell(value: object) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s



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


def get_audit_stats(db: Session) -> dict:
    """
    Compute aggregated metric totals for the audit dashboard in a single fast query.
    """
    now = datetime.now(timezone.utc)
    twenty_four_hours_ago = now - timedelta(hours=24)

    total_query = select(
        func.count(AuditLog.id).label("total"),
        func.count(case((AuditLog.result == AuditResult.success, 1))).label("success"),
        func.count(case((AuditLog.result == AuditResult.failure, 1))).label("failure"),
        func.count(case((AuditLog.action.ilike("%COMMAND%"), 1))).label("commands"),
        func.count(case((AuditLog.created_at >= twenty_four_hours_ago, 1))).label("last_24h"),
    )

    row = db.execute(total_query).first()
    if row:
        return {
            "total": int(row.total or 0),
            "success": int(row.success or 0),
            "failure": int(row.failure or 0),
            "commands": int(row.commands or 0),
            "last_24h": int(row.last_24h or 0),
        }
    return {
        "total": 0,
        "success": 0,
        "failure": 0,
        "commands": 0,
        "last_24h": 0,
    }


def export_audit_logs_csv(
    db: Session,
    action: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    user_id: int | None = None,
    result: AuditResult | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 5000,
) -> str:
    """
    Generate an audit trail CSV export sanitized against formula injection.
    """
    items, _ = get_audit_logs(
        db=db,
        page=1,
        limit=limit,
        action=action,
        target_type=target_type,
        target_id=target_id,
        user_id=user_id,
        result=result,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Audit Log ID",
        "Timestamp (UTC)",
        "Actor Username",
        "User ID",
        "Action Code",
        "Target Resource",
        "Target ID",
        "Outcome",
        "Source IP Address",
    ])

    for entry in items:
        username = entry.username or ("SYSTEM / AGENT" if not entry.user_id else f"User #{entry.user_id}")
        writer.writerow([
            entry.id,
            entry.created_at.isoformat() if entry.created_at else "",
            _sanitize_csv_cell(username),
            entry.user_id or "",
            _sanitize_csv_cell(entry.action),
            _sanitize_csv_cell(entry.target_type or ""),
            entry.target_id or "",
            entry.result.value if hasattr(entry.result, "value") else str(entry.result),
            _sanitize_csv_cell(entry.ip_address or ""),
        ])

    return output.getvalue()