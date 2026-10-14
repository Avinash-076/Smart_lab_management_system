from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.remote_command import RemoteCommand

class CommandResult(Base):
    __tablename__ = "command_results"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    command_id: Mapped[int] = mapped_column(
        ForeignKey("remote_commands.id"),
        unique=True,
        nullable=False,
    )

    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    message: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    command: Mapped["RemoteCommand"] = relationship(back_populates="result")