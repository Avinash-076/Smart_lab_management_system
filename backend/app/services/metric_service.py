from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.system_metric import SystemMetric
from app.schemas.metric_schema import MetricUpload
from app.services import alert_service

async def create_metric(
    db: Session,
    computer_id: int,
    metric_data: MetricUpload
) -> SystemMetric:
    metric = SystemMetric(
        computer_id= computer_id,
        **metric_data.model_dump(),
    )

    try:
        db.add(metric)
        db.commit()
        db.refresh(metric)
    except IntegrityError:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise    

    await alert_service.evaluate_metric(db, computer_id, metric)
    
    return metric   


MAX_LIMIT = 500

def get_metrics_for_computer(
    db: Session,
    computer_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[SystemMetric]:

    limit = min(limit, MAX_LIMIT)
    return list(
        db.scalars(
            select(SystemMetric).where(
                SystemMetric.computer_id==computer_id
            ).order_by(
                SystemMetric.recorded_at.desc()
            ).limit(limit).offset(offset)
        ).all()
    )