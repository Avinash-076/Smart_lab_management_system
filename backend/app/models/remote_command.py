from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.command_result import CommandResult
    from app.models.computer import Computer
    from app.models.user import User


class CommandType(str, enum.Enum):
    message = "message"
    lock = "lock"
    restart = "restart"
    shutdown = "shutdown"


class CommandStatus(str, enum.Enum):
    pending = "pending"
    delivered = "delivered"
    executed = "executed"
    failed = "failed"
    cancelled = "cancelled"


class RemoteCommand(Base):
    __tablename__ = "remote_commands"

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

    command_type: Mapped[CommandType] = mapped_column(
        SqlEnum(
            CommandType,
            native_enum=False,
        ),
        nullable=False,
    )

    payload: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[CommandStatus] = mapped_column(
        SqlEnum(
            CommandStatus,
            native_enum=False,
        ),
        default=CommandStatus.pending,
        nullable=False,
    )

    issued_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    computer: Mapped["Computer"] = relationship()

    issuer: Mapped["User"] = relationship()

    result: Mapped["CommandResult | None"] = relationship(
        back_populates="command",
        cascade="all, delete-orphan",
    )