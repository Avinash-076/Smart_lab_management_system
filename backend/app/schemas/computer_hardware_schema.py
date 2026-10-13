from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ComputerHardwareBase(BaseModel):
    # System & Chassis
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    system_type: str | None = None
    bios_version: str | None = None
    bios_date: str | None = None

    # Processor
    processor_name: str | None = None
    processor_cores: int | None = None
    processor_threads: int | None = None
    processor_base_speed: str | None = None
    processor_max_speed: str | None = None

    # Memory (RAM)
    ram_total_gb: float | None = None
    ram_usable_gb: float | None = None
    ram_type: str | None = None
    ram_speed: str | None = None
    ram_slots_used: int | None = None
    ram_slots_total: int | None = None

    # Storage
    storage_drives_count: int | None = None
    storage_total_gb: float | None = None
    storage_type: str | None = None
    storage_health: str | None = None

    # Graphics
    gpu_name: str | None = None
    gpu_memory_mb: float | None = None
    gpu_driver_version: str | None = None

    # Network Adapter Information
    subnet_mask: str | None = None
    default_gateway: str | None = None
    dns_servers: str | None = None
    connection_type: str | None = None

    # Motherboard
    motherboard_manufacturer: str | None = None
    motherboard_model: str | None = None
    motherboard_chipset: str | None = None
    motherboard_serial: str | None = None

    # OS & Power / Agent metadata
    os_install_date: str | None = None
    last_boot_time: str | None = None
    power_plan: str | None = None
    agent_version: str | None = None


class ComputerHardwareUpload(ComputerHardwareBase):
    pass


class ComputerHardwareResponse(ComputerHardwareBase):
    id: int
    computer_id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
