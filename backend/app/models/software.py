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


class Software(Base):
    __tablename__ = "software"

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

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    publisher: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    install_date: Mapped[str | None] = mapped_column(
        String(20),
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
            "ix_software_computer_name_version",
            "computer_id",
            "name",
            "version",
        ),
    )