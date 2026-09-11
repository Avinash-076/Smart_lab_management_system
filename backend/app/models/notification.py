from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime, timezone
import enum

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.computer import Computer


class NotificationSeverity(str, enum.Enum):
    warning = "warning"
    critical = "critical"

    

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    computer_id: Mapped[int] = mapped_column(
        ForeignKey("computers.id"),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    severity: Mapped[NotificationSeverity] = mapped_column(
        SqlEnum(NotificationSeverity, native_enum=False),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    computer: Mapped["Computer"] =  relationship()