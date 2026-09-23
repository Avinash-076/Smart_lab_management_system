from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.computer import Computer


class UsageSession(Base):
    __tablename__ = "usage_sessions"

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

    application_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    computer: Mapped["Computer"] = relationship()

    __table_args__ = (
        Index(
            "ix_usage_sessions_computer_started",
            "computer_id",
            "started_at",
        ),
    )