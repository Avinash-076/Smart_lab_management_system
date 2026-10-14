from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProcessItem(BaseModel):
    pid: int = Field(
        ge=0,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    user: str | None = Field(
        default=None,
        max_length=255,
    )

    cpu_percent: float = Field(
        default=0,
        ge=0,
    )

    memory_percent: float = Field(
        default=0,
        ge=0,
    )

    memory_mb: float | None = Field(
        default=None,
        ge=0,
    )

    executable_path: str | None = Field(
        default=None,
        max_length=500,
    )

    status: str | None = Field(
        default=None,
        max_length=50,
    )

    start_time: str | None = Field(
        default=None,
        max_length=64,
    )


class ProcessUpload(BaseModel):
    processes: list[ProcessItem] = Field(
        default_factory=list,
        max_length=5000,
    )


class ProcessResponse(BaseModel):
    id: int
    computer_id: int
    pid: int
    name: str
    user: str | None = None
    cpu_percent: float
    memory_percent: float
    memory_mb: float | None = None
    executable_path: str | None = None
    status: str | None = None
    start_time: str | None = None
    collected_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class ProcessStatusDistributionItem(BaseModel):
    status: str
    count: int
    percentage: float


class TopCpuProcessItem(BaseModel):
    pid: int
    name: str
    cpu_percent: float
    user: str | None = None


class ProcessSummaryResponse(BaseModel):
    total_running: int
    total_cpu_percent: float
    total_memory_mb: float
    total_memory_percent: float
    system_ram_gb: float | None = None
    last_scan: datetime | None = None
    status_distribution: list[ProcessStatusDistributionItem] = Field(default_factory=list)
    top_cpu_processes: list[TopCpuProcessItem] = Field(default_factory=list)
    users: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)


class ProcessRankingItem(BaseModel):
    rank: int
    pid: int
    name: str
    user: str | None = None
    cpu_percent: float
    memory_percent: float
    memory_mb: float | None = None
    download_mb: float | None = None
    upload_mb: float | None = None
    total_mb: float | None = None


class NetworkAttributionInfo(BaseModel):
    supported: bool = False
    status: str = "unavailable"
    reason: str = "Platform attribution unavailable: user-space process socket I/O is not reliably attributable without kernel-mode drivers on Windows."
    items: list[ProcessRankingItem] = Field(default_factory=list)


class ProcessRankingsResponse(BaseModel):
    computer_id: int
    top_cpu: list[ProcessRankingItem]
    top_memory: list[ProcessRankingItem]
    network: NetworkAttributionInfo
