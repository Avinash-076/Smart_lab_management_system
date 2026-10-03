from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.system_metric import SystemMetric
from app.schemas.metric_schema import MetricUpload
from app.services import alert_service

from datetime import datetime, timezone
from app.websocket.connection_manager import manager

async def create_metric(
    db: Session,
    computer_id: int,
    metric_data: MetricUpload
) -> SystemMetric:
    if metric_data.idempotency_key:
        existing = db.scalars(
            select(SystemMetric).where(
                SystemMetric.idempotency_key == metric_data.idempotency_key
            )
        ).first()
        if existing:
            return existing

    metric = SystemMetric(
        computer_id=computer_id,
        **metric_data.model_dump(),
    )

    try:
        db.add(metric)
        db.commit()
        db.refresh(metric)
    except IntegrityError:
        db.rollback()
        if metric_data.idempotency_key:
            existing = db.scalars(
                select(SystemMetric).where(
                    SystemMetric.idempotency_key == metric_data.idempotency_key
                )
            ).first()
            if existing:
                return existing
        raise
    except SQLAlchemyError:
        db.rollback()
        raise    

    try:
        recorded_at_iso = (
            metric.recorded_at.isoformat()
            if metric.recorded_at
            else datetime.now(timezone.utc).isoformat()
        )
        await manager.broadcast_to_dashboards({
            "type": "metric_update",
            "computer_id": computer_id,
            "recorded_at": recorded_at_iso,
            "cpu_usage": metric.cpu_usage,
            "ram_usage": metric.ram_usage,
            "disk_usage": metric.disk_usage,
            "network_sent": metric.network_sent,
            "network_received": metric.network_received,
        })
    except Exception:
        pass

    await alert_service.evaluate_metric(db, computer_id, metric)
    
    return metric   



from datetime import datetime

MAX_LIMIT = 500

def get_metrics_for_computer(
    db: Session,
    computer_id: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[SystemMetric]:
    query = select(SystemMetric).where(SystemMetric.computer_id == computer_id)

    if start_time is not None:
        query = query.where(SystemMetric.recorded_at >= start_time)

    if end_time is not None:
        query = query.where(SystemMetric.recorded_at <= end_time)

    limit = min(limit, MAX_LIMIT)
    return list(
        db.scalars(
            query.order_by(
                SystemMetric.recorded_at.desc()
            ).limit(limit).offset(offset)
        ).all()
    )