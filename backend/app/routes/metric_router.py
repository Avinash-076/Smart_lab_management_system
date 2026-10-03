from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException, Query   
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.auth import get_current_agent, require_permission
from app.schemas.metric_schema import MetricUpload, MetricRespond
from app.models.agent_credential import AgentCredential
from app.database import get_db
from app.services import metric_service, computer_service

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
)

DbSession = Annotated[Session, Depends(get_db)]

@router.post(
    "",
    response_model=MetricRespond,
    status_code=status.HTTP_201_CREATED,
)
async def upload_metric(
    db: DbSession,
    metric_data: MetricUpload,
    agent_credential: AgentCredential = Depends(get_current_agent),
):
    if agent_credential.computer_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This credential has not registered with a computer"
        )

    try:
        return await metric_service.create_metric(db, agent_credential.computer_id, metric_data)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Failed to save metrics - invaid computer reference")

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save metrics"
        )

def parse_query_datetime(val: str | None) -> datetime | None:
    if not val:
        return None
    cleaned = val.strip().replace(" ", "+")
    if cleaned.endswith("Z") or cleaned.endswith("z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {val}. Expected ISO-8601 string.",
        )


@router.get(
    "/{computer_id}",
    response_model=list[MetricRespond],
)
def get_computer_metric(
    computer_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    computer = computer_service.get_computer_by_id(db, computer_id)
    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    parsed_start = parse_query_datetime(start_time)
    parsed_end = parse_query_datetime(end_time)

    if parsed_start is not None and parsed_end is not None and parsed_start > parsed_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be before or equal to end_time",
        )

    return metric_service.get_metrics_for_computer(
        db,
        computer_id,
        start_time=parsed_start,
        end_time=parsed_end,
        limit=limit,
        offset=offset,
    )


