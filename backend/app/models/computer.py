from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.client_status import ClientStatus
    from app.models.agent_credential import AgentCredential

class Computer(Base):
    __tablename__ = "computers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    hostname: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
    )

    mac_address: Mapped[str] = mapped_column(
        String(17),
        nullable=False,
        unique=True
    )

    os_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    os_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    registered_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,    
    )

    status_info: Mapped["ClientStatus"] = relationship(
        back_populates="computer",
        cascade="all, delete-orphan",
        uselist=False,
    )

    credential: Mapped["AgentCredential"] = relationship(
        back_populates="computer",
        cascade="all, delete-orphan",
        uselist=False
    )

