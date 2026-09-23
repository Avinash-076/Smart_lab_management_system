from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.computer import Computer


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    computer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "computers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    cpu_usage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    ram_usage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    disk_usage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    network_sent: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    network_received: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    computer: Mapped["Computer"] = relationship()

    __table_args__ = (
        Index(
            "ix_system_metrics_computer_id_recorded_at",
            "computer_id",
            "recorded_at",
        ),
    )