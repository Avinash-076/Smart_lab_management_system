from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.computer import Computer


class ComputerHardware(Base):
    __tablename__ = "computer_hardware"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    computer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("computers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # System & Chassis
    manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    system_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bios_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bios_date: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Processor
    processor_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    processor_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processor_threads: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processor_base_speed: Mapped[str | None] = mapped_column(String(50), nullable=True)
    processor_max_speed: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Memory (RAM)
    ram_total_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    ram_usable_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    ram_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ram_speed: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ram_slots_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ram_slots_total: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Storage
    storage_drives_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_total_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    storage_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    storage_health: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Graphics
    gpu_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    gpu_memory_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    gpu_driver_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Network Adapter Information
    subnet_mask: Mapped[str | None] = mapped_column(String(50), nullable=True)
    default_gateway: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dns_servers: Mapped[str | None] = mapped_column(String(150), nullable=True)
    connection_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Motherboard
    motherboard_manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    motherboard_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    motherboard_chipset: Mapped[str | None] = mapped_column(String(100), nullable=True)
    motherboard_serial: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # OS & Power / Agent metadata
    os_install_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_boot_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    power_plan: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    computer: Mapped["Computer"] = relationship(
        "Computer",
        back_populates="hardware",
    )
