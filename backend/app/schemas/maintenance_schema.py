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

    computer_hostname: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


class MaintenanceComplete(BaseModel):
    work_performed: str | None = Field(
        default=None,
        max_length=5000,
    )
    notes: str | None = Field(
        default=None,
        max_length=5000,
    )


class MaintenanceStatsResponse(BaseModel):
    total: int = 0
    scheduled: int = 0
    in_progress: int = 0
    completed: int = 0
    cancelled: int = 0
    preventive: int = 0
    corrective: int = 0
    emergency: int = 0
    software: int = 0
    hardware: int = 0
