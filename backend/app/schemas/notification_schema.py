from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.notification import NotificationSeverity


class NotificationResponse(BaseModel):
    id: int
    computer_id: int
    category: str
    severity: NotificationSeverity
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    