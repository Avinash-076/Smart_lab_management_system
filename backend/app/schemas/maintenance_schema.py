from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.maintenance import (
    MaintenanceStatus,
    MaintenanceType,
)


class MaintenanceCreate(BaseModel):
    computer_id: int = Field(
        gt=0,
    )

    maintenance_type: MaintenanceType

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    technician_name: str | None = Field(
        default=None,
        max_length=255,
    )

    scheduled_at: datetime | None = None

    notes: str | None = Field(
        default=None,
        max_length=5000,
    )


class MaintenanceUpdate(BaseModel):
    maintenance_type: MaintenanceType | None = None

    status: MaintenanceStatus | None = None

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    work_performed: str | None = Field(
        default=None,
        max_length=5000,
    )

    technician_name: str | None = Field(
        default=None,
        max_length=255,
    )

    scheduled_at: datetime | None = None

    started_at: datetime | None = None

    completed_at: datetime | None = None

    notes: str | None = Field(
        default=None,
        max_length=5000,
    )


class MaintenanceResponse(BaseModel):
    id: int
    computer_id: int

    maintenance_type: MaintenanceType
    status: MaintenanceStatus

    title: str
    description: str | None
    work_performed: str | None

    technician_name: str | None
    notes: str | None

    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None

    created_by: int | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )