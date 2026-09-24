from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


if TYPE_CHECKING:
    from app.models.computer import Computer


class Process(Base):
    __tablename__ = "processes"

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

    pid: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    user: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    cpu_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )

    memory_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )

    status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    start_time: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    computer: Mapped["Computer"] = relationship()

    __table_args__ = (
        Index(
            "ix_processes_computer_pid",
            "computer_id",
            "pid",
        ),
        Index(
            "ix_processes_computer_name",
            "computer_id",
            "name",
        ),
        Index(
            "ix_processes_computer_collected_at",
            "computer_id",
            "collected_at",
        ),
    )