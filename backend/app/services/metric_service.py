from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.system_metric import SystemMetric
from app.schemas.metric_schema import MetricUpload
from app.services import alert_service
from app.websocket.connection_manager import manager

MAX_LIMIT = 500


async def create_metric(
    db: Session,
    computer_id: int,
    metric_data: MetricUpload,
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


async def create_metrics_batch(
    db: Session,
    computer_id: int,
    metrics_data: list[MetricUpload],
) -> list[SystemMetric]:
    """
    Ingest a batch of metrics from the client agent with idempotency handling.
    """
    created_or_existing: list[SystemMetric] = []
    latest_metric: SystemMetric | None = None

    for item in metrics_data:
        if item.idempotency_key:
            existing = db.scalars(
                select(SystemMetric).where(
                    SystemMetric.idempotency_key == item.idempotency_key
                )
            ).first()
            if existing:
                created_or_existing.append(existing)
                continue

        metric = SystemMetric(
            computer_id=computer_id,
            **item.model_dump(),
        )
        db.add(metric)
        try:
            db.commit()
            db.refresh(metric)
            created_or_existing.append(metric)
            latest_metric = metric
        except IntegrityError:
            db.rollback()
            if item.idempotency_key:
                existing = db.scalars(
                    select(SystemMetric).where(
                        SystemMetric.idempotency_key == item.idempotency_key
                    )
                ).first()
                if existing:
                    created_or_existing.append(existing)
                    continue
            raise

    if latest_metric is not None:
        try:
            recorded_at_iso = (
                latest_metric.recorded_at.isoformat()
                if latest_metric.recorded_at
                else datetime.now(timezone.utc).isoformat()
            )
            await manager.broadcast_to_dashboards({
                "type": "metric_update",
                "computer_id": computer_id,
                "recorded_at": recorded_at_iso,
                "cpu_usage": latest_metric.cpu_usage,
                "ram_usage": latest_metric.ram_usage,
                "disk_usage": latest_metric.disk_usage,
                "network_sent": latest_metric.network_sent,
                "network_received": latest_metric.network_received,
            })
        except Exception:
            pass

        await alert_service.evaluate_metric(db, computer_id, latest_metric)

    return created_or_existing


def get_metric_summary_for_computer(
    db: Session,
    computer_id: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    time_range_preset: str = "1h",
) -> dict:
    """
    Compute structured summary and time series metrics for Matrix tab.
    Calculates window statistics: Current, Average, Maximum, Minimum,
    network throughput, memory capacity details, and partition usage.
    """
    from app.models.computer_hardware import ComputerHardware

    query = select(SystemMetric).where(SystemMetric.computer_id == computer_id)
    if start_time is not None:
        query = query.where(SystemMetric.recorded_at >= start_time)
    if end_time is not None:
        query = query.where(SystemMetric.recorded_at <= end_time)

    metrics = list(
        db.scalars(
            query.order_by(SystemMetric.recorded_at.asc()).limit(MAX_LIMIT)
        ).all()
    )

    # Hardware specifications for capacity details
    hardware = db.scalars(
        select(ComputerHardware).where(ComputerHardware.computer_id == computer_id)
    ).first()

    total_ram_gb = hardware.ram_total_gb if (hardware and hardware.ram_total_gb) else 16.0
    total_disk_gb = hardware.storage_total_gb if (hardware and hardware.storage_total_gb) else 512.0

    sample_count = len(metrics)

    if sample_count == 0:
        # Check if there is ANY latest metric for this computer to populate current capacity
        latest_any = db.scalars(
            select(SystemMetric)
            .where(SystemMetric.computer_id == computer_id)
            .order_by(SystemMetric.recorded_at.desc())
            .limit(1)
        ).first()

        current_cpu = latest_any.cpu_usage if latest_any else None
        current_ram = latest_any.ram_usage if latest_any else None
        current_disk = latest_any.disk_usage if latest_any else None

        in_use_ram_gb = round(total_ram_gb * (current_ram / 100.0), 2) if current_ram is not None else None
        available_ram_gb = round(total_ram_gb - in_use_ram_gb, 2) if in_use_ram_gb is not None else None
        used_disk_gb = round(total_disk_gb * (current_disk / 100.0), 1) if current_disk is not None else None
        free_disk_gb = round(total_disk_gb - used_disk_gb, 1) if used_disk_gb is not None else None

        partitions = []
        if current_disk is not None:
            partitions.append({
                "device": "C:",
                "mountpoint": "C:\\",
                "name": "C: (System)",
                "total_gb": total_disk_gb,
                "used_gb": used_disk_gb,
                "free_gb": free_disk_gb,
                "percent": current_disk,
            })

        return {
            "computer_id": computer_id,
            "time_range": time_range_preset,
            "start_time": start_time,
            "end_time": end_time,
            "sample_count": 0,
            "cpu": {"current": current_cpu, "average": None, "maximum": None, "minimum": None},
            "memory": {"current": current_ram, "average": None, "maximum": None, "minimum": None},
            "disk": {"current": current_disk, "average": None, "maximum": None, "minimum": None},
            "network": {
                "current_download_mbps": None,
                "current_upload_mbps": None,
                "average_download_mbps": None,
                "average_upload_mbps": None,
                "maximum_download_mbps": None,
                "maximum_upload_mbps": None,
            },
            "memory_details": {
                "in_use_gb": in_use_ram_gb,
                "available_gb": available_ram_gb,
                "total_gb": total_ram_gb,
                "in_use_percent": current_ram,
            },
            "disk_partitions": partitions,
            "network_details": {
                "download_mbps": None,
                "upload_mbps": None,
                "total_sent_bytes": latest_any.network_sent if latest_any else None,
                "total_received_bytes": latest_any.network_received if latest_any else None,
                "total_sent_gb": round((latest_any.network_sent or 0) / (1024**3), 2) if latest_any else None,
                "total_received_gb": round((latest_any.network_received or 0) / (1024**3), 2) if latest_any else None,
            },
            "time_series": [],
        }

    # Compute series points and throughput rates
    time_series = []
    down_rates: list[float] = []
    up_rates: list[float] = []

    for i, m in enumerate(metrics):
        down_mbps: float | None = None
        up_mbps: float | None = None

        if i > 0 and m.recorded_at and metrics[i - 1].recorded_at:
            dt = (m.recorded_at - metrics[i - 1].recorded_at).total_seconds()
            if dt > 0:
                prev_sent = metrics[i - 1].network_sent
                prev_recv = metrics[i - 1].network_received
                curr_sent = m.network_sent
                curr_recv = m.network_received

                if curr_sent is not None and prev_sent is not None and curr_sent >= prev_sent:
                    up_mbps = round(((curr_sent - prev_sent) * 8.0) / (dt * 1_000_000.0), 2)
                    up_rates.append(up_mbps)
                if curr_recv is not None and prev_recv is not None and curr_recv >= prev_recv:
                    down_mbps = round(((curr_recv - prev_recv) * 8.0) / (dt * 1_000_000.0), 2)
                    down_rates.append(down_mbps)

        time_series.append({
            "timestamp": m.recorded_at,
            "cpu_usage": m.cpu_usage,
            "ram_usage": m.ram_usage,
            "disk_usage": m.disk_usage,
            "download_mbps": down_mbps,
            "upload_mbps": up_mbps,
            "network_sent": m.network_sent,
            "network_received": m.network_received,
        })

    # Calculations for CPU, RAM, Disk
    cpu_vals = [m.cpu_usage for m in metrics]
    ram_vals = [m.ram_usage for m in metrics]
    disk_vals = [m.disk_usage for m in metrics]

    def _stats(vals: list[float]) -> dict:
        if not vals:
            return {"current": None, "average": None, "maximum": None, "minimum": None}
        return {
            "current": round(vals[-1], 1),
            "average": round(sum(vals) / len(vals), 1),
            "maximum": round(max(vals), 1),
            "minimum": round(min(vals), 1),
        }

    cpu_stats = _stats(cpu_vals)
    ram_stats = _stats(ram_vals)
    disk_stats = _stats(disk_vals)

    # Network rates
    curr_down = down_rates[-1] if down_rates else None
    curr_up = up_rates[-1] if up_rates else None
    avg_down = round(sum(down_rates) / len(down_rates), 2) if down_rates else None
    avg_up = round(sum(up_rates) / len(up_rates), 2) if up_rates else None
    max_down = round(max(down_rates), 2) if down_rates else None
    max_up = round(max(up_rates), 2) if up_rates else None

    # Memory breakdown
    current_ram_pct = ram_stats["current"] or 0.0
    in_use_ram_gb = round(total_ram_gb * (current_ram_pct / 100.0), 2)
    available_ram_gb = round(max(0.0, total_ram_gb - in_use_ram_gb), 2)

    # Disk partitions
    current_disk_pct = disk_stats["current"] or 0.0
    used_disk_gb = round(total_disk_gb * (current_disk_pct / 100.0), 1)
    free_disk_gb = round(max(0.0, total_disk_gb - used_disk_gb), 1)

    partitions = [
        {
            "device": "C:",
            "mountpoint": "C:\\",
            "name": "C: (System)",
            "total_gb": total_disk_gb,
            "used_gb": used_disk_gb,
            "free_gb": free_disk_gb,
            "percent": current_disk_pct,
        }
    ]

    # Cumulative traffic
    latest_metric_obj = metrics[-1]
    sent_bytes = latest_metric_obj.network_sent
    recv_bytes = latest_metric_obj.network_received
    sent_gb = round(sent_bytes / (1024**3), 2) if sent_bytes is not None else None
    recv_gb = round(recv_bytes / (1024**3), 2) if recv_bytes is not None else None

    return {
        "computer_id": computer_id,
        "time_range": time_range_preset,
        "start_time": start_time,
        "end_time": end_time,
        "sample_count": sample_count,
        "cpu": cpu_stats,
        "memory": ram_stats,
        "disk": disk_stats,
        "network": {
            "current_download_mbps": curr_down,
            "current_upload_mbps": curr_up,
            "average_download_mbps": avg_down,
            "average_upload_mbps": avg_up,
            "maximum_download_mbps": max_down,
            "maximum_upload_mbps": max_up,
        },
        "memory_details": {
            "in_use_gb": in_use_ram_gb,
            "available_gb": available_ram_gb,
            "total_gb": total_ram_gb,
            "in_use_percent": current_ram_pct,
        },
        "disk_partitions": partitions,
        "network_details": {
            "download_mbps": curr_down,
            "upload_mbps": curr_up,
            "total_sent_bytes": sent_bytes,
            "total_received_bytes": recv_bytes,
            "total_sent_gb": sent_gb,
            "total_received_gb": recv_gb,
        },
        "time_series": time_series,
    }


def purge_expired_metrics(
    db: Session,
    retention_days: int | None = None,
) -> int:
    """
    Purge telemetry metric records older than the configured data retention days.
    Returns the count of purged records.
    """
    from datetime import timedelta
    from sqlalchemy import delete
    from app.services.setting_service import get_setting_value

    if retention_days is None:
        retention_days = int(get_setting_value(db, "data_retention_days", 30))

    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, retention_days))

    result = db.execute(
        delete(SystemMetric)
        .where(SystemMetric.recorded_at < cutoff)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount or 0