from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.remote_command import CommandType, CommandStatus


class CommandCreate(BaseModel):
    command_type: CommandType
    payload: str | None = Field(default=None, max_length=255)


class CommandResultSubmit(BaseModel):
    success: bool
    message: str | None = Field(default=None, max_length=255)
    duration_seconds: float | None = None


class CommandResultResponse(BaseModel):
    id: int
    command_id: int
    success: bool
    message: str | None
    duration_seconds: float | None = None
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommandResponse(BaseModel):
    id: int
    computer_id: int
    computer_hostname: str | None = None
    computer_ip: str | None = None
    command_type: CommandType
    payload: str | None
    status: CommandStatus
    issued_by: int | None = None
    issued_by_username: str | None = None
    duration_seconds: float | None = None
    created_at: datetime
    result: CommandResultResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class CommandSummaryResponse(BaseModel):
    total_commands: int
    successful_commands: int
    failed_commands: int
    pending_commands: int
    delivered_commands: int
    cancelled_commands: int
    success_rate_percent: float
    failure_rate_percent: float
    last_execution_at: datetime | None = None
    recent_activities: list[CommandResponse] = Field(default_factory=list)


class BatchCommandCreate(BaseModel):
    computer_ids: list[int] = Field(min_length=1, max_length=500)
    command_type: CommandType
    payload: str | None = Field(default=None, max_length=255)


class BatchCommandResultItem(BaseModel):
    computer_id: int
    computer_hostname: str | None = None
    command_id: int | None = None
    command_type: CommandType
    status: CommandStatus | None = None
    success: bool
    error: str | None = None


class BatchCommandResponse(BaseModel):
    total_targets: int
    dispatched_count: int
    failed_count: int
    results: list[BatchCommandResultItem] = Field(default_factory=list)


class FleetOverviewResponse(BaseModel):
    total_computers: int
    online_computers: int
    offline_computers: int
    online_percentage: float
    offline_percentage: float
    commands_24h: int
    commands_24h_success: int
    commands_24h_failed: int
    commands_24h_pending: int