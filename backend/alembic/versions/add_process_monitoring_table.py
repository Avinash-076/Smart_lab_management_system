"""add process monitoring table

Revision ID: e7a91c42b5d3
Revises: 8f3c2a1b4d6
Create Date: 2026-09-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ============================================================
# REVISION IDENTIFIERS
# ============================================================

revision: str = "e7a91c42b5d3"

down_revision: Union[
    str,
    Sequence[str],
    None,
] = "8f3c2a1b4d6"

branch_labels = None

depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade() -> None:

    op.create_table(
        "processes",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "computer_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "pid",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "user",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "cpu_percent",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "memory_percent",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "start_time",
            sa.String(length=30),
            nullable=True,
        ),

        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["computer_id"],
            ["computers.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id",
        ),
    )

    op.create_index(
        op.f("ix_processes_computer_id"),
        "processes",
        ["computer_id"],
        unique=False,
    )

    op.create_index(
        "ix_processes_computer_pid",
        "processes",
        ["computer_id", "pid"],
        unique=False,
    )

    op.create_index(
        "ix_processes_computer_name",
        "processes",
        ["computer_id", "name"],
        unique=False,
    )

    op.create_index(
        "ix_processes_computer_collected_at",
        "processes",
        ["computer_id", "collected_at"],
        unique=False,
    )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade() -> None:

    op.drop_index(
        "ix_processes_computer_collected_at",
        table_name="processes",
    )

    op.drop_index(
        "ix_processes_computer_name",
        table_name="processes",
    )

    op.drop_index(
        "ix_processes_computer_pid",
        table_name="processes",
    )

    op.drop_index(
        op.f("ix_processes_computer_id"),
        table_name="processes",
    )

    op.drop_table(
        "processes",
    )