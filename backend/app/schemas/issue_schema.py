from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.issue import (
    IssueSeverity,
    IssueStatus,
    IssueSource,
)


class IssueCreate(BaseModel):
    computer_id: int = Field(
        gt=0,
    )

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str = Field(
        min_length=1,
        max_length=5000,
    )

    severity: IssueSeverity = IssueSeverity.medium

    source: IssueSource = IssueSource.admin

    idempotency_key: str | None = Field(
        default=None,
        max_length=128,
    )


class IssueUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
        min_length=1,
        max_length=5000,
    )

    severity: IssueSeverity | None = None

    status: IssueStatus | None = None

    resolution_notes: str | None = Field(
        default=None,
        max_length=5000,
    )


class IssueResponse(BaseModel):
    id: int
    computer_id: int
    title: str
    description: str
    severity: IssueSeverity
    status: IssueStatus
    source: IssueSource

    resolution_notes: str | None
    idempotency_key: str | None = None

    created_by: int | None
    resolved_by: int | None

    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None

    computer_hostname: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


class IssueAgentCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str = Field(
        min_length=1,
        max_length=5000,
    )

    severity: IssueSeverity = IssueSeverity.medium

    idempotency_key: str | None = Field(
        default=None,
        max_length=128,
    )


class IssueResolve(BaseModel):
    resolution_notes: str | None = Field(
        default=None,
        max_length=5000,
    )


class IssueStatsResponse(BaseModel):
    total: int = 0
    open: int = 0
    in_progress: int = 0
    resolved: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0