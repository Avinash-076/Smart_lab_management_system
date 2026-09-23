from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import enum

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.computer import Computer
    from app.models.user import User


class MaintenanceType(str, enum.Enum):
    preventive = "preventive"
    corrective = "corrective"
    emergency = "emergency"
    software = "software"
    hardware = "hardware"


class MaintenanceStatus(str, enum.Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    computer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "computers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    maintenance_type: Mapped[MaintenanceType] = mapped_column(
        SqlEnum(
            MaintenanceType,
            native_enum=False,
        ),
        nullable=False,
    )

    status: Mapped[MaintenanceStatus] = mapped_column(
        SqlEnum(
            MaintenanceStatus,
            native_enum=False,
        ),
        nullable=False,
        default=MaintenanceStatus.scheduled,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    work_performed: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    technician_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    computer: Mapped["Computer"] = relationship()

    creator: Mapped["User | None"] = relationship(
        foreign_keys=[created_by],
    )

    __table_args__ = (
        Index(
            "ix_maintenance_computer_status",
            "computer_id",
            "status",
        ),
    )