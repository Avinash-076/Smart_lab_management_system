from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

class MetricUpload(BaseModel):
    cpu_usage: float = Field(ge=0, le=100)
    ram_usage: float = Field(ge=0, le=100)
    disk_usage: float = Field(ge=0, le=100)
    network_sent: float | None = Field(default=None, ge=0)
    network_received: float | None = Field(default=None, ge=0)
    idempotency_key: str | None = Field(default=None, max_length=128)

class MetricRespond(BaseModel):
    id: int
    computer_id: int
    cpu_usage: float
    ram_usage: float
    disk_usage: float
    network_sent: float | None 
    network_received: float | None
    idempotency_key: str | None = None
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetricBatchUpload(BaseModel):
    metrics: list[MetricUpload] = Field(min_length=1, max_length=500)


class MetricStatSet(BaseModel):
    current: float | None = None
    average: float | None = None
    maximum: float | None = None
    minimum: float | None = None


class MemoryDetails(BaseModel):
    in_use_gb: float | None = None
    available_gb: float | None = None
    total_gb: float | None = None
    in_use_percent: float | None = None


class DiskPartition(BaseModel):
    device: str | None = None
    mountpoint: str | None = None
    name: str | None = None
    total_gb: float | None = None
    used_gb: float | None = None
    free_gb: float | None = None
    percent: float | None = None


class NetworkDetails(BaseModel):
    download_mbps: float | None = None
    upload_mbps: float | None = None
    total_sent_bytes: float | None = None
    total_received_bytes: float | None = None
    total_sent_gb: float | None = None
    total_received_gb: float | None = None


class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    cpu_usage: float
    ram_usage: float
    disk_usage: float
    download_mbps: float | None = None
    upload_mbps: float | None = None
    network_sent: float | None = None
    network_received: float | None = None


class MetricSummaryResponse(BaseModel):
    computer_id: int
    time_range: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    sample_count: int = 0
    cpu: MetricStatSet
    memory: MetricStatSet
    disk: MetricStatSet
    network: MetricStatSet
    memory_details: MemoryDetails
    disk_partitions: list[DiskPartition]
    network_details: NetworkDetails
    time_series: list[TimeSeriesPoint]