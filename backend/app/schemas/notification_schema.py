from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.notification import NotificationSeverity


class NotificationResponse(BaseModel):
    id: int
    computer_id: int
    computer_hostname: str | None = None
    category: str
    severity: NotificationSeverity
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationStatsResponse(BaseModel):
    total: int = 0
    unread: int = 0
    critical: int = 0
    warning: int = 0
    info: int = 0

    model_config = ConfigDict(from_attributes=True)


class NotificationCreate(BaseModel):
    computer_id: int
    category: str
    severity: NotificationSeverity = NotificationSeverity.info
    message: str


class NotificationBulkReadResponse(BaseModel):
    updated_count: int


class NotificationBulkDeleteResponse(BaseModel):
    deleted_count: int