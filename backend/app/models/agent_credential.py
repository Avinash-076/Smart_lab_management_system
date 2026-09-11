from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING: 
    from app.models.computer import Computer




class AgentCredential(Base):
    __tablename__ = "agent_credentials"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    agent_id: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False
    )

    # credential: Mapped[str] = mapped_column(
    #     String(64),
    #     unique=True,
    #     nullable=False,
    #     index=True,
    # )

    secret_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    computer_id: Mapped[int] = mapped_column(
        ForeignKey("computers.id"),
        unique=True,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    last_used_at: Mapped[datetime | None ] =  mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    computer: Mapped["Computer"] = relationship(back_populates="credential")