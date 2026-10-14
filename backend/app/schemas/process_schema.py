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
    user: str | None
    cpu_percent: float
    memory_percent: float
    status: str | None
    start_time: str | None
    collected_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


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