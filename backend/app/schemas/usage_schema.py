from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class UsageSessionCreate(BaseModel):
    application_name: str = Field(
        min_length=1,
        max_length=255,
    )
    process_name: str | None = Field(
        default=None,
        max_length=255,
    )
    user: str | None = Field(
        default=None,
        max_length=255,
    )
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int = Field(
        default=0,
        ge=0,
    )


class UsageSessionResponse(BaseModel):
    id: int
    computer_id: int
    application_name: str
    process_name: str | None = None
    user: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class UsageUpload(BaseModel):
    sessions: list[UsageSessionCreate] = Field(
        default_factory=list,
        max_length=2000,
    )


class TopAppUsageItem(BaseModel):
    application_name: str
    process_name: str
    duration_seconds: int
    formatted_duration: str
    percentage: float


class UsageTrendInterval(BaseModel):
    label: str
    start_time: datetime
    end_time: datetime
    duration_minutes: float


class UsageSummaryResponse(BaseModel):
    computer_id: int
    time_range: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    total_active_seconds: int = 0
    formatted_total_active: str = "0m"
    total_sessions: int = 0
    top_applications: list[TopAppUsageItem] = Field(default_factory=list)
    trend_intervals: list[UsageTrendInterval] = Field(default_factory=list)
    available_users: list[str] = Field(default_factory=list)
    available_applications: list[str] = Field(default_factory=list)