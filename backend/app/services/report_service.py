import csv
import io
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog, AuditResult
from app.models.client_status import ClientStatus
from app.models.command_result import CommandResult
from app.models.computer import Computer
from app.models.issue import Issue, IssueSeverity, IssueStatus
from app.models.maintenance import MaintenanceRecord, MaintenanceStatus, MaintenanceType
from app.models.remote_command import CommandStatus, CommandType, RemoteCommand
from app.models.software import Software
from app.models.system_metric import SystemMetric
from app.models.user import User


# ============================================================
# CSV FORMULA INJECTION SANITIZER
# ============================================================

def sanitize_csv_cell(value: Any) -> str:
    """
    Sanitize value to prevent CSV formula injection in spreadsheet software.
    If the value begins with =, +, -, @, tab, or CR, prefix with a single quote.
    """
    if value is None:
        return ""
    text = str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{text}"
    return text


# ============================================================
# TIME RANGE PARSER & VALIDATOR
# ============================================================

def parse_time_range(
    period: str = "24h",
    from_date: datetime | str | None = None,
    to_date: datetime | str | None = None,
) -> tuple[datetime, datetime]:
    """
    Parse and validate a time range in UTC.
    Supported periods: 24h, 7d, 30d, custom.
    """
    now = datetime.now(timezone.utc)

    if from_date is not None or to_date is not None or period == "custom":
        if isinstance(from_date, str):
            try:
                from_date = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("Invalid from_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
        if isinstance(to_date, str):
            try:
                to_date = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("Invalid to_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")

        start = from_date if from_date else (now - timedelta(days=30))
        end = to_date if to_date else now

        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        if start > end:
            raise ValueError("from_date must be before or equal to to_date")
    elif period == "7d":
        start = now - timedelta(days=7)
        end = now
    elif period == "30d":
        start = now - timedelta(days=30)
        end = now
    else:
        # Default 24h
        start = now - timedelta(hours=24)
        end = now

    return start, end


# ============================================================
# OVERVIEW SUMMARY
# ============================================================

def get_report_overview(db: Session) -> dict[str, int]:
    """Retrieve high-level counts across all reporting domains."""
    total_computers = int(db.scalar(select(func.count(Computer.id))) or 0)
    online_computers = int(
        db.scalar(
            select(func.count(ClientStatus.id)).where(ClientStatus.status == "online")
        )
        or 0
    )
    offline_computers = max(0, total_computers - online_computers)

    total_software = int(db.scalar(select(func.count(Software.id))) or 0)
    unique_software = int(
        db.scalar(select(func.count(func.distinct(Software.name)))) or 0
    )

    total_issues = int(db.scalar(select(func.count(Issue.id))) or 0)
    open_issues = int(
        db.scalar(
            select(func.count(Issue.id)).where(
                Issue.status.in_([IssueStatus.open, IssueStatus.in_progress])
            )
        )
        or 0
    )
    resolved_issues = int(
        db.scalar(
            select(func.count(Issue.id)).where(Issue.status == IssueStatus.resolved)
        )
        or 0
    )
    critical_issues = int(
        db.scalar(
            select(func.count(Issue.id)).where(
                Issue.severity == IssueSeverity.critical,
                Issue.status != IssueStatus.resolved,
            )
        )
        or 0
    )

    total_maintenance = int(db.scalar(select(func.count(MaintenanceRecord.id))) or 0)
    pending_maintenance = int(
        db.scalar(
            select(func.count(MaintenanceRecord.id)).where(
                MaintenanceRecord.status.in_([MaintenanceStatus.scheduled, MaintenanceStatus.in_progress])
            )
        )
        or 0
    )
    completed_maintenance = int(
        db.scalar(
            select(func.count(MaintenanceRecord.id)).where(
                MaintenanceRecord.status == MaintenanceStatus.completed
            )
        )
        or 0
    )

    now = datetime.now(timezone.utc)
    overdue_maintenance = int(
        db.scalar(
            select(func.count(MaintenanceRecord.id)).where(
                MaintenanceRecord.status == MaintenanceStatus.scheduled,
                MaintenanceRecord.scheduled_at < now,
            )
        )
        or 0
    )

    total_commands = int(db.scalar(select(func.count(RemoteCommand.id))) or 0)
    executed_commands = int(
        db.scalar(
            select(func.count(RemoteCommand.id)).where(
                RemoteCommand.status == CommandStatus.executed
            )
        )
        or 0
    )
    failed_commands = int(
        db.scalar(
            select(func.count(RemoteCommand.id)).where(
                RemoteCommand.status == CommandStatus.failed
            )
        )
        or 0
    )

    total_audit_events = int(db.scalar(select(func.count(AuditLog.id))) or 0)

    return {
        "total_computers": total_computers,
        "online_computers": online_computers,
        "offline_computers": offline_computers,
        "total_software_records": total_software,
        "unique_software_count": unique_software,
        "total_issues": total_issues,
        "open_issues": open_issues,
        "resolved_issues": resolved_issues,
        "critical_issues": critical_issues,
        "total_maintenance": total_maintenance,
        "pending_maintenance": pending_maintenance,
        "completed_maintenance": completed_maintenance,
        "overdue_maintenance": overdue_maintenance,
        "total_commands": total_commands,
        "executed_commands": executed_commands,
        "failed_commands": failed_commands,
        "total_audit_events": total_audit_events,
    }


# ============================================================
# COMPUTER & UTILIZATION REPORT
# ============================================================

def get_utilization_report(
    db: Session,
    period: str = "24h",
    from_date: datetime | str | None = None,
    to_date: datetime | str | None = None,
    computer_id: int | None = None,
) -> dict[str, Any]:
    """Calculate aggregate and per-computer utilization metrics."""
    start_dt, end_dt = parse_time_range(period, from_date, to_date)

    # Registered computers
    comp_query = select(Computer).options(joinedload(Computer.status_info))
    if computer_id is not None:
        comp_query = comp_query.where(Computer.id == computer_id)
    computers = list(db.scalars(comp_query.order_by(Computer.id.asc())).all())

    total_computers = len(computers)
    online_count = sum(1 for c in computers if c.status == "online")
    offline_count = total_computers - online_count

    # Metrics filter
    metric_filter = [
        SystemMetric.recorded_at >= start_dt,
        SystemMetric.recorded_at <= end_dt,
    ]
    if computer_id is not None:
        metric_filter.append(SystemMetric.computer_id == computer_id)

    # Overall aggregate metrics
    agg_query = select(
        func.avg(SystemMetric.cpu_usage).label("avg_cpu"),
        func.max(SystemMetric.cpu_usage).label("max_cpu"),
        func.avg(SystemMetric.ram_usage).label("avg_ram"),
        func.max(SystemMetric.ram_usage).label("max_ram"),
        func.avg(SystemMetric.disk_usage).label("avg_disk"),
        func.max(SystemMetric.disk_usage).label("max_disk"),
    ).where(*metric_filter)

    agg_result = db.execute(agg_query).one()

    metrics_summary = {
        "avg_cpu_percent": round(float(agg_result.avg_cpu or 0.0), 2),
        "max_cpu_percent": round(float(agg_result.max_cpu or 0.0), 2),
        "avg_ram_percent": round(float(agg_result.avg_ram or 0.0), 2),
        "max_ram_percent": round(float(agg_result.max_ram or 0.0), 2),
        "avg_disk_percent": round(float(agg_result.avg_disk or 0.0), 2),
        "max_disk_percent": round(float(agg_result.max_disk or 0.0), 2),
    }

    # Per-computer metrics map
    per_comp_query = (
        select(
            SystemMetric.computer_id,
            func.avg(SystemMetric.cpu_usage).label("avg_cpu"),
            func.avg(SystemMetric.ram_usage).label("avg_ram"),
            func.avg(SystemMetric.disk_usage).label("avg_disk"),
            func.count(SystemMetric.id).label("sample_count"),
        )
        .where(*metric_filter)
        .group_by(SystemMetric.computer_id)
    )
    per_comp_data = {
        row.computer_id: {
            "avg_cpu": round(float(row.avg_cpu or 0.0), 2),
            "avg_ram": round(float(row.avg_ram or 0.0), 2),
            "avg_disk": round(float(row.avg_disk or 0.0), 2),
            "sample_count": int(row.sample_count or 0),
        }
        for row in db.execute(per_comp_query).all()
    }

    computer_items = []
    for c in computers:
        c_metrics = per_comp_data.get(
            c.id,
            {"avg_cpu": 0.0, "avg_ram": 0.0, "avg_disk": 0.0, "sample_count": 0},
        )
        computer_items.append({
            "id": c.id,
            "hostname": c.hostname,
            "ip_address": c.ip_address,
            "mac_address": c.mac_address,
            "os_name": c.os_name,
            "os_version": c.os_version,
            "status": c.status,
            "last_seen": c.last_seen,
            "registered_at": c.registered_at,
            "avg_cpu": c_metrics["avg_cpu"],
            "avg_ram": c_metrics["avg_ram"],
            "avg_disk": c_metrics["avg_disk"],
            "sample_count": c_metrics["sample_count"],
        })

    # Timeline aggregation (e.g. hourly or samples)
    timeline_query = (
        select(
            SystemMetric.recorded_at,
            SystemMetric.cpu_usage,
            SystemMetric.ram_usage,
            SystemMetric.disk_usage,
        )
        .where(*metric_filter)
        .order_by(SystemMetric.recorded_at.asc())
        .limit(100)
    )
    timeline_rows = db.execute(timeline_query).all()
    timeline = [
        {
            "timestamp": row.recorded_at,
            "avg_cpu": round(float(row.cpu_usage or 0.0), 2),
            "avg_ram": round(float(row.ram_usage or 0.0), 2),
            "avg_disk": round(float(row.disk_usage or 0.0), 2),
        }
        for row in timeline_rows
    ]

    return {
        "period": period,
        "from_date": start_dt,
        "to_date": end_dt,
        "total_computers": total_computers,
        "online_computers": online_count,
        "offline_computers": offline_count,
        "metrics_summary": metrics_summary,
        "timeline": timeline,
        "computers": computer_items,
    }


# ============================================================
# SOFTWARE REPORT
# ============================================================

def get_software_report(
    db: Session,
    computer_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 25,
) -> dict[str, Any]:
    """Retrieve software inventory report and application statistics."""
    query = select(Software).options(joinedload(Software.computer))
    count_query = select(func.count(Software.id))

    if computer_id is not None:
        query = query.where(Software.computer_id == computer_id)
        count_query = count_query.where(Software.computer_id == computer_id)

    if search:
        pattern = f"%{search.strip()}%"
        search_filter = or_(
            Software.name.ilike(pattern),
            Software.publisher.ilike(pattern),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_records = int(db.scalar(count_query) or 0)
    unique_software = int(
        db.scalar(select(func.count(func.distinct(Software.name)))) or 0
    )

    # Top installed software
    top_query = (
        select(
            Software.name,
            Software.publisher,
            func.count(Software.id).label("inst_count"),
        )
        .group_by(Software.name, Software.publisher)
        .order_by(func.count(Software.id).desc())
        .limit(10)
    )
    top_installed = [
        {"name": r.name, "publisher": r.publisher, "count": int(r.inst_count)}
        for r in db.execute(top_query).all()
    ]

    limit = max(1, min(limit, 500))
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 1
    page = max(1, min(page, max(1, total_pages)))
    offset = (page - 1) * limit

    records = list(
        db.scalars(
            query.order_by(Software.name.asc(), Software.id.asc())
            .limit(limit)
            .offset(offset)
        ).all()
    )

    items = [
        {
            "id": s.id,
            "name": s.name,
            "version": s.version,
            "publisher": s.publisher,
            "install_date": s.install_date,
            "collected_at": s.collected_at,
            "computer_id": s.computer_id,
            "computer_hostname": s.computer.hostname if s.computer else None,
        }
        for s in records
    ]

    return {
        "total_records": total_records,
        "unique_software_count": unique_software,
        "top_installed": top_installed,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "items": items,
    }


# ============================================================
# ISSUE REPORT
# ============================================================

def get_issue_report(
    db: Session,
    computer_id: int | None = None,
    severity: str | None = None,
    status: str | None = None,
    from_date: datetime | str | None = None,
    to_date: datetime | str | None = None,
    page: int = 1,
    limit: int = 25,
) -> dict[str, Any]:
    """Retrieve issue tracking report with status/severity groupings."""
    query = select(Issue).options(joinedload(Issue.computer))
    count_query = select(func.count(Issue.id))

    if computer_id is not None:
        query = query.where(Issue.computer_id == computer_id)
        count_query = count_query.where(Issue.computer_id == computer_id)

    if severity:
        try:
            sev_enum = IssueSeverity(severity.lower().strip())
            query = query.where(Issue.severity == sev_enum)
            count_query = count_query.where(Issue.severity == sev_enum)
        except ValueError:
            pass

    if status:
        try:
            stat_enum = IssueStatus(status.lower().strip())
            query = query.where(Issue.status == stat_enum)
            count_query = count_query.where(Issue.status == stat_enum)
        except ValueError:
            pass

    if from_date or to_date:
        start_dt, end_dt = parse_time_range("custom", from_date, to_date)
        query = query.where(Issue.created_at >= start_dt, Issue.created_at <= end_dt)
        count_query = count_query.where(Issue.created_at >= start_dt, Issue.created_at <= end_dt)

    total_issues = int(db.scalar(count_query) or 0)

    # Group by status
    by_status_raw = db.execute(
        select(Issue.status, func.count(Issue.id)).group_by(Issue.status)
    ).all()
    by_status = {str(r[0].value if hasattr(r[0], "value") else r[0]): int(r[1]) for r in by_status_raw}

    # Group by severity
    by_sev_raw = db.execute(
        select(Issue.severity, func.count(Issue.id)).group_by(Issue.severity)
    ).all()
    by_severity = {str(r[0].value if hasattr(r[0], "value") else r[0]): int(r[1]) for r in by_sev_raw}

    limit = max(1, min(limit, 500))
    total_pages = math.ceil(total_issues / limit) if total_issues > 0 else 1
    page = max(1, min(page, max(1, total_pages)))
    offset = (page - 1) * limit

    records = list(
        db.scalars(
            query.order_by(Issue.created_at.desc(), Issue.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )

    items = [
        {
            "id": iss.id,
            "computer_id": iss.computer_id,
            "computer_hostname": iss.computer.hostname if iss.computer else None,
            "title": iss.title,
            "description": iss.description,
            "severity": iss.severity.value if hasattr(iss.severity, "value") else str(iss.severity),
            "status": iss.status.value if hasattr(iss.status, "value") else str(iss.status),
            "source": iss.source.value if hasattr(iss.source, "value") else str(iss.source),
            "resolution_notes": iss.resolution_notes,
            "created_at": iss.created_at,
            "updated_at": iss.updated_at,
            "resolved_at": iss.resolved_at,
        }
        for iss in records
    ]

    return {
        "total_issues": total_issues,
        "by_status": by_status,
        "by_severity": by_severity,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "items": items,
    }


# ============================================================
# MAINTENANCE REPORT
# ============================================================

def get_maintenance_report(
    db: Session,
    computer_id: int | None = None,
    status: str | None = None,
    maintenance_type: str | None = None,
    from_date: datetime | str | None = None,
    to_date: datetime | str | None = None,
    page: int = 1,
    limit: int = 25,
) -> dict[str, Any]:
    """Retrieve maintenance operations report."""
    query = select(MaintenanceRecord).options(joinedload(MaintenanceRecord.computer))
    count_query = select(func.count(MaintenanceRecord.id))

    if computer_id is not None:
        query = query.where(MaintenanceRecord.computer_id == computer_id)
        count_query = count_query.where(MaintenanceRecord.computer_id == computer_id)

    if status:
        try:
            stat_enum = MaintenanceStatus(status.lower().strip())
            query = query.where(MaintenanceRecord.status == stat_enum)
            count_query = count_query.where(MaintenanceRecord.status == stat_enum)
        except ValueError:
            pass

    if maintenance_type:
        try:
            type_enum = MaintenanceType(maintenance_type.lower().strip())
            query = query.where(MaintenanceRecord.maintenance_type == type_enum)
            count_query = count_query.where(MaintenanceRecord.maintenance_type == type_enum)
        except ValueError:
            pass

    if from_date or to_date:
        start_dt, end_dt = parse_time_range("custom", from_date, to_date)
        query = query.where(
            MaintenanceRecord.created_at >= start_dt,
            MaintenanceRecord.created_at <= end_dt,
        )
        count_query = count_query.where(
            MaintenanceRecord.created_at >= start_dt,
            MaintenanceRecord.created_at <= end_dt,
        )

    total_records = int(db.scalar(count_query) or 0)

    # Group by status
    by_stat_raw = db.execute(
        select(MaintenanceRecord.status, func.count(MaintenanceRecord.id)).group_by(
            MaintenanceRecord.status
        )
    ).all()
    by_status = {str(r[0].value if hasattr(r[0], "value") else r[0]): int(r[1]) for r in by_stat_raw}

    # Group by type
    by_type_raw = db.execute(
        select(
            MaintenanceRecord.maintenance_type,
            func.count(MaintenanceRecord.id),
        ).group_by(MaintenanceRecord.maintenance_type)
    ).all()
    by_type = {str(r[0].value if hasattr(r[0], "value") else r[0]): int(r[1]) for r in by_type_raw}

    now = datetime.now(timezone.utc)
    upcoming_count = int(
        db.scalar(
            select(func.count(MaintenanceRecord.id)).where(
                MaintenanceRecord.status == MaintenanceStatus.scheduled,
                MaintenanceRecord.scheduled_at >= now,
            )
        )
        or 0
    )
    overdue_count = int(
        db.scalar(
            select(func.count(MaintenanceRecord.id)).where(
                MaintenanceRecord.status == MaintenanceStatus.scheduled,
                MaintenanceRecord.scheduled_at < now,
            )
        )
        or 0
    )

    limit = max(1, min(limit, 500))
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 1
    page = max(1, min(page, max(1, total_pages)))
    offset = (page - 1) * limit

    records = list(
        db.scalars(
            query.order_by(MaintenanceRecord.created_at.desc(), MaintenanceRecord.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )

    items = [
        {
            "id": m.id,
            "computer_id": m.computer_id,
            "computer_hostname": m.computer.hostname if m.computer else None,
            "title": m.title,
            "description": m.description,
            "maintenance_type": m.maintenance_type.value if hasattr(m.maintenance_type, "value") else str(m.maintenance_type),
            "status": m.status.value if hasattr(m.status, "value") else str(m.status),
            "technician_name": m.technician_name,
            "scheduled_at": m.scheduled_at,
            "started_at": m.started_at,
            "completed_at": m.completed_at,
            "created_at": m.created_at,
        }
        for m in records
    ]

    return {
        "total_records": total_records,
        "by_status": by_status,
        "by_type": by_type,
        "upcoming_count": upcoming_count,
        "overdue_count": overdue_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "items": items,
    }


# ============================================================
# COMMAND REPORT
# ============================================================

def get_command_report(
    db: Session,
    computer_id: int | None = None,
    command_type: str | None = None,
    status: str | None = None,
    from_date: datetime | str | None = None,
    to_date: datetime | str | None = None,
    page: int = 1,
    limit: int = 25,
) -> dict[str, Any]:
    """Retrieve remote command execution metrics and outcomes."""
    query = select(RemoteCommand).options(
        joinedload(RemoteCommand.computer),
        joinedload(RemoteCommand.issuer),
        joinedload(RemoteCommand.result),
    )
    count_query = select(func.count(RemoteCommand.id))

    if computer_id is not None:
        query = query.where(RemoteCommand.computer_id == computer_id)
        count_query = count_query.where(RemoteCommand.computer_id == computer_id)

    if command_type:
        try:
            type_enum = CommandType(command_type.lower().strip())
            query = query.where(RemoteCommand.command_type == type_enum)
            count_query = count_query.where(RemoteCommand.command_type == type_enum)
        except ValueError:
            pass

    if status:
        try:
            stat_enum = CommandStatus(status.lower().strip())
            query = query.where(RemoteCommand.status == stat_enum)
            count_query = count_query.where(RemoteCommand.status == stat_enum)
        except ValueError:
            pass

    if from_date or to_date:
        start_dt, end_dt = parse_time_range("custom", from_date, to_date)
        query = query.where(
            RemoteCommand.created_at >= start_dt,
            RemoteCommand.created_at <= end_dt,
        )
        count_query = count_query.where(
            RemoteCommand.created_at >= start_dt,
            RemoteCommand.created_at <= end_dt,
        )

    total_commands = int(db.scalar(count_query) or 0)

    # Group by type
    by_type_raw = db.execute(
        select(RemoteCommand.command_type, func.count(RemoteCommand.id)).group_by(
            RemoteCommand.command_type
        )
    ).all()
    by_type = {str(r[0].value if hasattr(r[0], "value") else r[0]): int(r[1]) for r in by_type_raw}

    # Group by status
    by_stat_raw = db.execute(
        select(RemoteCommand.status, func.count(RemoteCommand.id)).group_by(
            RemoteCommand.status
        )
    ).all()
    by_status = {str(r[0].value if hasattr(r[0], "value") else r[0]): int(r[1]) for r in by_stat_raw}

    executed_count = by_status.get("executed", 0)
    failed_count = by_status.get("failed", 0)
    finished_total = executed_count + failed_count
    success_rate = (
        round((executed_count / finished_total) * 100.0, 2)
        if finished_total > 0
        else 0.0
    )

    limit = max(1, min(limit, 500))
    total_pages = math.ceil(total_commands / limit) if total_commands > 0 else 1
    page = max(1, min(page, max(1, total_pages)))
    offset = (page - 1) * limit

    records = list(
        db.scalars(
            query.order_by(RemoteCommand.created_at.desc(), RemoteCommand.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )

    items = [
        {
            "id": cmd.id,
            "computer_id": cmd.computer_id,
            "computer_hostname": cmd.computer.hostname if cmd.computer else None,
            "command_type": cmd.command_type.value if hasattr(cmd.command_type, "value") else str(cmd.command_type),
            "payload": cmd.payload,
            "status": cmd.status.value if hasattr(cmd.status, "value") else str(cmd.status),
            "issued_by": cmd.issued_by,
            "issued_by_username": cmd.issuer.username if cmd.issuer else None,
            "created_at": cmd.created_at,
            "success": cmd.result.success if cmd.result else None,
            "result_message": cmd.result.message if cmd.result else None,
            "completed_at": cmd.result.completed_at if cmd.result else None,
        }
        for cmd in records
    ]

    return {
        "total_commands": total_commands,
        "by_type": by_type,
        "by_status": by_status,
        "success_rate": success_rate,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "items": items,
    }


# ============================================================
# AUDIT REPORT
# ============================================================

def get_audit_report(
    db: Session,
    action: str | None = None,
    user_id: int | None = None,
    result: str | None = None,
    from_date: datetime | str | None = None,
    to_date: datetime | str | None = None,
    page: int = 1,
    limit: int = 25,
) -> dict[str, Any]:
    """Retrieve system security audit log report."""
    query = select(AuditLog).options(joinedload(AuditLog.user))
    count_query = select(func.count(AuditLog.id))

    if action:
        query = query.where(AuditLog.action.ilike(f"%{action.strip()}%"))
        count_query = count_query.where(AuditLog.action.ilike(f"%{action.strip()}%"))

    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)

    if result:
        try:
            res_enum = AuditResult(result.lower().strip())
            query = query.where(AuditLog.result == res_enum)
            count_query = count_query.where(AuditLog.result == res_enum)
        except ValueError:
            pass

    if from_date or to_date:
        start_dt, end_dt = parse_time_range("custom", from_date, to_date)
        query = query.where(
            AuditLog.created_at >= start_dt,
            AuditLog.created_at <= end_dt,
        )
        count_query = count_query.where(
            AuditLog.created_at >= start_dt,
            AuditLog.created_at <= end_dt,
        )

    total_events = int(db.scalar(count_query) or 0)

    # Group by action
    by_act_raw = db.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
    ).all()
    by_action = {str(r[0]): int(r[1]) for r in by_act_raw}

    # Group by result
    by_res_raw = db.execute(
        select(AuditLog.result, func.count(AuditLog.id)).group_by(AuditLog.result)
    ).all()
    by_result = {str(r[0].value if hasattr(r[0], "value") else r[0]): int(r[1]) for r in by_res_raw}

    limit = max(1, min(limit, 500))
    total_pages = math.ceil(total_events / limit) if total_events > 0 else 1
    page = max(1, min(page, max(1, total_pages)))
    offset = (page - 1) * limit

    records = list(
        db.scalars(
            query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )

    items = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "username": log.username,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "result": log.result.value if hasattr(log.result, "value") else str(log.result),
            "ip_address": log.ip_address,
            "created_at": log.created_at,
        }
        for log in records
    ]

    return {
        "total_events": total_events,
        "by_action": by_action,
        "by_result": by_result,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "items": items,
    }


# ============================================================
# CSV EXPORT GENERATOR
# ============================================================

def export_report_csv(
    report_type: str,
    db: Session,
    period: str = "24h",
    from_date: datetime | str | None = None,
    to_date: datetime | str | None = None,
    computer_id: int | None = None,
    search: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    maintenance_type: str | None = None,
    command_type: str | None = None,
    action: str | None = None,
    result: str | None = None,
) -> tuple[str, str]:
    """
    Generate CSV content and filename for the requested report type.
    Includes formula injection sanitization.
    """
    clean_type = report_type.lower().strip().replace(" ", "_")
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    if clean_type in ("computer", "computers", "utilization", "computer_report"):
        filename = f"SLMS-Computer-Utilization-Report-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}.csv"
        headers = [
            "Computer ID",
            "Hostname",
            "IP Address",
            "MAC Address",
            "Operating System",
            "Status",
            "Last Seen",
            "Average CPU (%)",
            "Average RAM (%)",
            "Average Disk (%)",
            "Telemetry Samples",
        ]
        writer.writerow(headers)

        report = get_utilization_report(
            db,
            period=period,
            from_date=from_date,
            to_date=to_date,
            computer_id=computer_id,
        )
        for c in report["computers"]:
            writer.writerow([
                sanitize_csv_cell(c["id"]),
                sanitize_csv_cell(c["hostname"]),
                sanitize_csv_cell(c["ip_address"]),
                sanitize_csv_cell(c["mac_address"]),
                sanitize_csv_cell(f"{c['os_name']} {c['os_version']}"),
                sanitize_csv_cell(c["status"]),
                sanitize_csv_cell(c["last_seen"].isoformat() if c["last_seen"] else "Never"),
                sanitize_csv_cell(c["avg_cpu"]),
                sanitize_csv_cell(c["avg_ram"]),
                sanitize_csv_cell(c["avg_disk"]),
                sanitize_csv_cell(c["sample_count"]),
            ])

    elif clean_type in ("software", "software_report"):
        filename = f"SLMS-Software-Inventory-Report-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}.csv"
        headers = [
            "ID",
            "Software Name",
            "Version",
            "Publisher",
            "Computer ID",
            "Computer Hostname",
            "Install Date",
            "Collected At",
        ]
        writer.writerow(headers)

        report = get_software_report(
            db,
            computer_id=computer_id,
            search=search,
            page=1,
            limit=5000,
        )
        for s in report["items"]:
            writer.writerow([
                sanitize_csv_cell(s["id"]),
                sanitize_csv_cell(s["name"]),
                sanitize_csv_cell(s["version"] or "N/A"),
                sanitize_csv_cell(s["publisher"] or "Unknown"),
                sanitize_csv_cell(s["computer_id"]),
                sanitize_csv_cell(s["computer_hostname"] or "Unknown"),
                sanitize_csv_cell(s["install_date"] or "N/A"),
                sanitize_csv_cell(s["collected_at"].isoformat() if s["collected_at"] else ""),
            ])

    elif clean_type in ("issue", "issues", "issue_report"):
        filename = f"SLMS-Issue-Report-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}.csv"
        headers = [
            "Issue ID",
            "Computer ID",
            "Computer Hostname",
            "Title",
            "Severity",
            "Status",
            "Source",
            "Created At",
            "Resolved At",
            "Resolution Notes",
        ]
        writer.writerow(headers)

        report = get_issue_report(
            db,
            computer_id=computer_id,
            severity=severity,
            status=status,
            from_date=from_date,
            to_date=to_date,
            page=1,
            limit=5000,
        )
        for iss in report["items"]:
            writer.writerow([
                sanitize_csv_cell(iss["id"]),
                sanitize_csv_cell(iss["computer_id"]),
                sanitize_csv_cell(iss["computer_hostname"] or "Unknown"),
                sanitize_csv_cell(iss["title"]),
                sanitize_csv_cell(iss["severity"]),
                sanitize_csv_cell(iss["status"]),
                sanitize_csv_cell(iss["source"]),
                sanitize_csv_cell(iss["created_at"].isoformat() if iss["created_at"] else ""),
                sanitize_csv_cell(iss["resolved_at"].isoformat() if iss["resolved_at"] else "Unresolved"),
                sanitize_csv_cell(iss["resolution_notes"] or ""),
            ])

    elif clean_type in ("maintenance", "maintenance_report"):
        filename = f"SLMS-Maintenance-Report-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}.csv"
        headers = [
            "Record ID",
            "Computer ID",
            "Computer Hostname",
            "Title",
            "Type",
            "Status",
            "Technician",
            "Scheduled At",
            "Completed At",
            "Created At",
        ]
        writer.writerow(headers)

        report = get_maintenance_report(
            db,
            computer_id=computer_id,
            status=status,
            maintenance_type=maintenance_type,
            from_date=from_date,
            to_date=to_date,
            page=1,
            limit=5000,
        )
        for m in report["items"]:
            writer.writerow([
                sanitize_csv_cell(m["id"]),
                sanitize_csv_cell(m["computer_id"]),
                sanitize_csv_cell(m["computer_hostname"] or "Unknown"),
                sanitize_csv_cell(m["title"]),
                sanitize_csv_cell(m["maintenance_type"]),
                sanitize_csv_cell(m["status"]),
                sanitize_csv_cell(m["technician_name"] or "Unassigned"),
                sanitize_csv_cell(m["scheduled_at"].isoformat() if m["scheduled_at"] else "Not scheduled"),
                sanitize_csv_cell(m["completed_at"].isoformat() if m["completed_at"] else "Not completed"),
                sanitize_csv_cell(m["created_at"].isoformat() if m["created_at"] else ""),
            ])

    elif clean_type in ("command", "commands", "command_report"):
        filename = f"SLMS-Remote-Commands-Report-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}.csv"
        headers = [
            "Command ID",
            "Computer ID",
            "Computer Hostname",
            "Command Type",
            "Status",
            "Issued By",
            "Success",
            "Result Message",
            "Created At",
            "Completed At",
        ]
        writer.writerow(headers)

        report = get_command_report(
            db,
            computer_id=computer_id,
            command_type=command_type,
            status=status,
            from_date=from_date,
            to_date=to_date,
            page=1,
            limit=5000,
        )
        for cmd in report["items"]:
            writer.writerow([
                sanitize_csv_cell(cmd["id"]),
                sanitize_csv_cell(cmd["computer_id"]),
                sanitize_csv_cell(cmd["computer_hostname"] or "Unknown"),
                sanitize_csv_cell(cmd["command_type"]),
                sanitize_csv_cell(cmd["status"]),
                sanitize_csv_cell(cmd["issued_by_username"] or f"User #{cmd['issued_by']}"),
                sanitize_csv_cell("Yes" if cmd["success"] is True else ("No" if cmd["success"] is False else "Pending")),
                sanitize_csv_cell(cmd["result_message"] or ""),
                sanitize_csv_cell(cmd["created_at"].isoformat() if cmd["created_at"] else ""),
                sanitize_csv_cell(cmd["completed_at"].isoformat() if cmd["completed_at"] else ""),
            ])

    elif clean_type in ("audit", "audit_log", "audit_report"):
        filename = f"SLMS-Security-Audit-Report-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}.csv"
        headers = [
            "Event ID",
            "Timestamp",
            "Action",
            "Result",
            "User ID",
            "Username",
            "Target Type",
            "Target ID",
            "IP Address",
        ]
        writer.writerow(headers)

        report = get_audit_report(
            db,
            action=action,
            user_id=None,
            result=result,
            from_date=from_date,
            to_date=to_date,
            page=1,
            limit=5000,
        )
        for a in report["items"]:
            writer.writerow([
                sanitize_csv_cell(a["id"]),
                sanitize_csv_cell(a["created_at"].isoformat() if a["created_at"] else ""),
                sanitize_csv_cell(a["action"]),
                sanitize_csv_cell(a["result"]),
                sanitize_csv_cell(a["user_id"] or "System"),
                sanitize_csv_cell(a["username"] or "System"),
                sanitize_csv_cell(a["target_type"] or "N/A"),
                sanitize_csv_cell(a["target_id"] or "N/A"),
                sanitize_csv_cell(a["ip_address"] or "Unknown"),
            ])
    else:
        raise ValueError(f"Unknown report export type: {report_type}")

    return output.getvalue(), filename
