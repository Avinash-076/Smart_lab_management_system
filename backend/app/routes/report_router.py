from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_permission
from app.database import get_db
from app.models.user import User
from app.schemas.report_schema import (
    AuditReportResponse,
    CommandReportResponse,
    IssueReportResponse,
    MaintenanceReportResponse,
    ReportOverviewResponse,
    SoftwareReportResponse,
    UtilizationReportResponse,
)
from app.services import report_service


DbSession = Annotated[
    Session,
    Depends(get_db),
]


router = APIRouter(
    prefix="/reports",
    tags=["Reports & Analytics"],
)


@router.get(
    "/summary",
    response_model=ReportOverviewResponse,
)
@router.get(
    "/overview",
    response_model=ReportOverviewResponse,
)
def get_report_overview(
    db: DbSession,
    _user: Annotated[User, Depends(require_permission("VIEW_COMPUTERS"))],
):
    """Retrieve high-level overview metrics across all reporting domains."""
    return report_service.get_report_overview(db)


@router.get(
    "/utilization",
    response_model=UtilizationReportResponse,
)
def get_utilization_report(
    db: DbSession,
    _user: Annotated[User, Depends(require_permission("VIEW_COMPUTERS"))],
    period: str = Query(default="24h", description="Time window: 24h, 7d, 30d, custom"),
    from_date: str | None = Query(default=None, description="Start date (ISO format)"),
    to_date: str | None = Query(default=None, description="End date (ISO format)"),
    computer_id: int | None = Query(default=None, description="Filter by computer ID"),
):
    """Retrieve computer telemetry and system resource utilization aggregates."""
    try:
        return report_service.get_utilization_report(
            db=db,
            period=period,
            from_date=from_date,
            to_date=to_date,
            computer_id=computer_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/software",
    response_model=SoftwareReportResponse,
)
def get_software_report(
    db: DbSession,
    _user: Annotated[User, Depends(require_permission("VIEW_COMPUTERS"))],
    computer_id: int | None = Query(default=None, description="Filter by computer ID"),
    search: str | None = Query(default=None, description="Search software name or publisher"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=500),
):
    """Retrieve software inventory report and application statistics."""
    return report_service.get_software_report(
        db=db,
        computer_id=computer_id,
        search=search,
        page=page,
        limit=limit,
    )


@router.get(
    "/issues",
    response_model=IssueReportResponse,
)
def get_issue_report(
    db: DbSession,
    _user: Annotated[User, Depends(require_permission("VIEW_COMPUTERS"))],
    computer_id: int | None = Query(default=None, description="Filter by computer ID"),
    severity: str | None = Query(default=None, description="Filter by severity (low, medium, high, critical)"),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status (open, in_progress, resolved)"),
    from_date: str | None = Query(default=None, description="Start date (ISO format)"),
    to_date: str | None = Query(default=None, description="End date (ISO format)"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=500),
):
    """Retrieve issue tracking statistics, breakdown by status and severity."""
    try:
        return report_service.get_issue_report(
            db=db,
            computer_id=computer_id,
            severity=severity,
            status=status_filter,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/maintenance",
    response_model=MaintenanceReportResponse,
)
def get_maintenance_report(
    db: DbSession,
    _user: Annotated[User, Depends(require_permission("VIEW_COMPUTERS"))],
    computer_id: int | None = Query(default=None, description="Filter by computer ID"),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status (scheduled, in_progress, completed, cancelled)"),
    maintenance_type: str | None = Query(default=None, description="Filter by type (preventive, corrective, emergency, software, hardware)"),
    from_date: str | None = Query(default=None, description="Start date (ISO format)"),
    to_date: str | None = Query(default=None, description="End date (ISO format)"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=500),
):
    """Retrieve maintenance operational history and status breakdown."""
    try:
        return report_service.get_maintenance_report(
            db=db,
            computer_id=computer_id,
            status=status_filter,
            maintenance_type=maintenance_type,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/commands",
    response_model=CommandReportResponse,
)
def get_command_report(
    db: DbSession,
    _user: Annotated[User, Depends(require_permission("VIEW_COMPUTERS"))],
    computer_id: int | None = Query(default=None, description="Filter by computer ID"),
    command_type: str | None = Query(default=None, description="Filter by command type (message, lock, restart, shutdown)"),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status (pending, delivered, executed, failed, cancelled)"),
    from_date: str | None = Query(default=None, description="Start date (ISO format)"),
    to_date: str | None = Query(default=None, description="End date (ISO format)"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=500),
):
    """Retrieve remote command execution metrics and outcome rates."""
    try:
        return report_service.get_command_report(
            db=db,
            computer_id=computer_id,
            command_type=command_type,
            status=status_filter,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/audit",
    response_model=AuditReportResponse,
)
def get_audit_report(
    db: DbSession,
    _user: Annotated[User, Depends(require_permission("MANAGE_USERS"))],
    action: str | None = Query(default=None, description="Filter by action code"),
    user_id: int | None = Query(default=None, description="Filter by user ID"),
    result: str | None = Query(default=None, description="Filter by result (success, failure)"),
    from_date: str | None = Query(default=None, description="Start date (ISO format)"),
    to_date: str | None = Query(default=None, description="End date (ISO format)"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=500),
):
    """Retrieve security audit events breakdown and activity timeline."""
    try:
        return report_service.get_audit_report(
            db=db,
            action=action,
            user_id=user_id,
            result=result,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/export",
)
def export_report_csv(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    report_type: str = Query(default="computer", description="Report domain: computer, software, issue, maintenance, command, audit"),
    period: str = Query(default="24h"),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    computer_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    maintenance_type: str | None = Query(default=None),
    command_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    result: str | None = Query(default=None),
):
    """
    Export reports as sanitized CSV files.
    Enforces authorization based on the exported report domain.
    """
    clean_type = report_type.lower().strip().replace(" ", "_")

    # Authorize export according to report domain
    if clean_type in ("audit", "audit_log", "audit_report"):
        # Audit logs require MANAGE_USERS or MANAGE_ROLES
        has_perm = any(
            p.action_code in ("MANAGE_USERS", "MANAGE_ROLES") and p.allowed
            for p in current_user.role.permissions
        ) if current_user.role else False
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not have permission to export audit reports",
            )
    else:
        # Standard computer/software/issue/maintenance reports require VIEW_COMPUTERS
        has_perm = any(
            p.action_code == "VIEW_COMPUTERS" and p.allowed
            for p in current_user.role.permissions
        ) if current_user.role else False
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not have permission to export reports",
            )

    try:
        csv_data, filename = report_service.export_report_csv(
            report_type=report_type,
            db=db,
            period=period,
            from_date=from_date,
            to_date=to_date,
            computer_id=computer_id,
            search=search,
            status=status_filter,
            severity=severity,
            maintenance_type=maintenance_type,
            command_type=command_type,
            action=action,
            result=result,
        )

        return Response(
            content=csv_data,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "text/csv; charset=utf-8",
            },
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
