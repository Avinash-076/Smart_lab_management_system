from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String 
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
if TYPE_CHECKING:
    from app.models.computer import Computer

class ClientStatus(Base):
    __tablename__ = "client_status"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    computer_id: Mapped[int] = mapped_column(
        ForeignKey("computers.id"),
        unique=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="offline",
        nullable=False
    )

    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    computer: Mapped["Computer"] = relationship(
        back_populates="status_info"
    )