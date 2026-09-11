from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.remote_command import CommandType, CommandStatus



class CommandCreate(BaseModel):
    command_type: CommandType
    payload: str | None = Field(default=None, max_length=255)


class CommandResponse(BaseModel):
    id: int
    computer_id: int
    command_type: CommandType
    payload: str | None
    status: CommandStatus
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class CommandResultSubmit(BaseModel):
    success: bool
    message: str | None = Field(default=None, max_length=255)


class CommandResultResponse(BaseModel):
    id: int
    command_id: int
    success: bool
    message: str | None
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)