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