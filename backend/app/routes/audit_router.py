from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database import get_db
from app.models.audit_log import AuditResult
from app.schemas.audit_schema import (
    AuditLogListResponse,
    AuditLogResponse,
    AuditStatsResponse,
)
from app.services import audit_service

DbSession = Annotated[
    Session,
    Depends(get_db),
]

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


def parse_query_datetime(val: str | None, is_end_of_day: bool = False) -> datetime | None:
    if not val:
        return None
    cleaned = val.strip().replace(" ", "+")
    if cleaned.endswith("Z") or cleaned.endswith("z"):
        cleaned = cleaned[:-1] + "+00:00"

    # If the caller supplied a pure date like YYYY-MM-DD
    if len(cleaned) == 10 and cleaned.count("-") == 2:
        if is_end_of_day:
            cleaned = cleaned + "T23:59:59.999999"
        else:
            cleaned = cleaned + "T00:00:00"

    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {val}. Expected ISO-8601 string.",
        )


@router.get(
    "/stats",
    response_model=AuditStatsResponse,
)
def get_audit_stats(
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
):
    """
    Retrieve fast aggregated summary statistics for the audit log dashboard.
    """
    stats_data = audit_service.get_audit_stats(db=db)
    return AuditStatsResponse(**stats_data)


@router.get(
    "/export",
)
def export_audit_logs_csv(
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    result: AuditResult | None = Query(default=None),
    search: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=5000, ge=1, le=10000),
):
    """
    Export filtered audit logs as a downloadable sanitized CSV file.
    """
    parsed_date_from = parse_query_datetime(date_from, is_end_of_day=False)
    parsed_date_to = parse_query_datetime(date_to, is_end_of_day=True)

    csv_data = audit_service.export_audit_logs_csv(
        db=db,
        action=action,
        target_type=target_type,
        target_id=target_id,
        user_id=user_id,
        result=result,
        search=search,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
        limit=limit,
    )

    filename = f"slms-audit-logs-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )


@router.get(
    "",
    response_model=AuditLogListResponse,
)
def get_audit_logs(
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    result: AuditResult | None = Query(default=None),
    search: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    """
    Retrieve paginated audit logs with search and filtering.
    """
    parsed_date_from = parse_query_datetime(date_from, is_end_of_day=False)
    parsed_date_to = parse_query_datetime(date_to, is_end_of_day=True)

    items, total = audit_service.get_audit_logs(
        db=db,
        page=page,
        limit=limit,
        action=action,
        target_type=target_type,
        target_id=target_id,
        user_id=user_id,
        result=result,
        search=search,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
    )

    total_pages = (total + limit - 1) // limit if total > 0 else 0

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get(
    "/{log_id}",
    response_model=AuditLogResponse,
)
def get_audit_log_details(
    log_id: int,
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
):
    """
    Retrieve details for a single audit log entry.
    """
    entry = audit_service.get_audit_log_by_id(
        db=db,
        log_id=log_id,
    )

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found",
        )

    return entry
