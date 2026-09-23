from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UsageSessionCreate(BaseModel):
    application_name: str = Field(
        min_length=1,
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
    started_at: datetime
    ended_at: datetime | None
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