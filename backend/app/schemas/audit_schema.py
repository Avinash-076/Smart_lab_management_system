from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.audit_log import AuditResult


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None = None
    username: str | None = None
    action: str
    target_type: str | None = None
    target_id: int | None = None
    result: AuditResult
    ip_address: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    limit: int
    total_pages: int
