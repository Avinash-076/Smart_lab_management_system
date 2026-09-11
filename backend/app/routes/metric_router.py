from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException, Query   
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.auth import get_current_agent,require_permission
from app.schemas.metric_schema import MetricUpload, MetricRespond
from app.models.agent_credential import AgentCredential
from app.database import get_db
from app.services import metric_service

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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to save metrics - invaid computer reference"
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save metrics"
        )

@router.get(
    "/{computer_id}",
    response_model=list[MetricRespond],
)
def get_computer_metric(
    computer_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    return metric_service.get_metrics_for_computer(db, computer_id, limit=limit, offset=offset)
