"""add computer_hardware table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "computer_hardware",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("computer_id", sa.Integer(), sa.ForeignKey("computers.id", ondelete="CASCADE"), nullable=False),
        # System & Chassis
        sa.Column("manufacturer", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("serial_number", sa.String(length=100), nullable=True),
        sa.Column("system_type", sa.String(length=100), nullable=True),
        sa.Column("bios_version", sa.String(length=100), nullable=True),
        sa.Column("bios_date", sa.String(length=100), nullable=True),
        # Processor
        sa.Column("processor_name", sa.String(length=150), nullable=True),
        sa.Column("processor_cores", sa.Integer(), nullable=True),
        sa.Column("processor_threads", sa.Integer(), nullable=True),
        sa.Column("processor_base_speed", sa.String(length=50), nullable=True),
        sa.Column("processor_max_speed", sa.String(length=50), nullable=True),
        # Memory (RAM)
        sa.Column("ram_total_gb", sa.Float(), nullable=True),
        sa.Column("ram_usable_gb", sa.Float(), nullable=True),
        sa.Column("ram_type", sa.String(length=50), nullable=True),
        sa.Column("ram_speed", sa.String(length=50), nullable=True),
        sa.Column("ram_slots_used", sa.Integer(), nullable=True),
        sa.Column("ram_slots_total", sa.Integer(), nullable=True),
        # Storage
        sa.Column("storage_drives_count", sa.Integer(), nullable=True),
        sa.Column("storage_total_gb", sa.Float(), nullable=True),
        sa.Column("storage_type", sa.String(length=50), nullable=True),
        sa.Column("storage_health", sa.String(length=50), nullable=True),
        # Graphics
        sa.Column("gpu_name", sa.String(length=150), nullable=True),
        sa.Column("gpu_memory_mb", sa.Float(), nullable=True),
        sa.Column("gpu_driver_version", sa.String(length=100), nullable=True),
        # Network Adapter Information
        sa.Column("subnet_mask", sa.String(length=50), nullable=True),
        sa.Column("default_gateway", sa.String(length=50), nullable=True),
        sa.Column("dns_servers", sa.String(length=150), nullable=True),
        sa.Column("connection_type", sa.String(length=50), nullable=True),
        # Motherboard
        sa.Column("motherboard_manufacturer", sa.String(length=100), nullable=True),
        sa.Column("motherboard_model", sa.String(length=100), nullable=True),
        sa.Column("motherboard_chipset", sa.String(length=100), nullable=True),
        sa.Column("motherboard_serial", sa.String(length=100), nullable=True),
        # OS & Power / Agent metadata
        sa.Column("os_install_date", sa.String(length=100), nullable=True),
        sa.Column("last_boot_time", sa.String(length=100), nullable=True),
        sa.Column("power_plan", sa.String(length=100), nullable=True),
        sa.Column("agent_version", sa.String(length=50), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_computer_hardware_id", "computer_hardware", ["id"], unique=False)
    op.create_index("ix_computer_hardware_computer_id", "computer_hardware", ["computer_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_computer_hardware_computer_id", table_name="computer_hardware")
    op.drop_index("ix_computer_hardware_id", table_name="computer_hardware")
    op.drop_table("computer_hardware")
