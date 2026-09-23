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


class IssueSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IssueStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class IssueSource(str, enum.Enum):
    agent = "agent"
    admin = "admin"
    system = "system"


class Issue(Base):
    __tablename__ = "issues"

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

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    severity: Mapped[IssueSeverity] = mapped_column(
        SqlEnum(
            IssueSeverity,
            native_enum=False,
        ),
        nullable=False,
        default=IssueSeverity.medium,
    )

    status: Mapped[IssueStatus] = mapped_column(
        SqlEnum(
            IssueStatus,
            native_enum=False,
        ),
        nullable=False,
        default=IssueStatus.open,
    )

    source: Mapped[IssueSource] = mapped_column(
        SqlEnum(
            IssueSource,
            native_enum=False,
        ),
        nullable=False,
        default=IssueSource.admin,
    )

    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    resolved_by: Mapped[int | None] = mapped_column(
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

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    computer: Mapped["Computer"] = relationship()

    creator: Mapped["User | None"] = relationship(
        foreign_keys=[created_by],
    )

    resolver: Mapped["User | None"] = relationship(
        foreign_keys=[resolved_by],
    )

    __table_args__ = (
        Index(
            "ix_issues_computer_status",
            "computer_id",
            "status",
        ),
    )