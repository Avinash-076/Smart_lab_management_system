"""add management tables

Revision ID: 8f3c2a1b4d6
Revises: d5e244477ef6
Create Date: 2026-09-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f3c2a1b4d6"
down_revision: Union[str, Sequence[str], None] = "d5e244477ef6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ---------------------------------------------------------
    # SOFTWARE
    # ---------------------------------------------------------

    op.create_table(
        "software",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("computer_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("install_date", sa.String(length=20), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_software_computer_id"),
        "software",
        ["computer_id"],
        unique=False,
    )

    op.create_index(
        "ix_software_computer_name_version",
        "software",
        ["computer_id", "name", "version"],
        unique=False,
    )

    # ---------------------------------------------------------
    # USAGE SESSIONS
    # ---------------------------------------------------------

    op.create_table(
        "usage_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("computer_id", sa.Integer(), nullable=False),
        sa.Column("application_name", sa.String(length=255), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "ended_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "duration_seconds",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["computer_id"],
            ["computers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_usage_sessions_computer_id"),
        "usage_sessions",
        ["computer_id"],
        unique=False,
    )

    op.create_index(
        "ix_usage_sessions_computer_started",
        "usage_sessions",
        ["computer_id", "started_at"],
        unique=False,
    )

    # ---------------------------------------------------------
    # ISSUES
    # ---------------------------------------------------------

    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("computer_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),

        sa.Column(
            "severity",
            sa.Enum(
                "low",
                "medium",
                "high",
                "critical",
                name="issueseverity",
                native_enum=False,
            ),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.Enum(
                "open",
                "in_progress",
                "resolved",
                name="issuestatus",
                native_enum=False,
            ),
            nullable=False,
        ),

        sa.Column(
            "source",
            sa.Enum(
                "agent",
                "admin",
                "system",
                name="issuesource",
                native_enum=False,
            ),
            nullable=False,
        ),

        sa.Column(
            "resolution_notes",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "created_by",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "resolved_by",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.ForeignKeyConstraint(
            ["computer_id"],
            ["computers.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),

        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["users.id"],
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_issues_computer_id"),
        "issues",
        ["computer_id"],
        unique=False,
    )

    op.create_index(
        "ix_issues_computer_status",
        "issues",
        ["computer_id", "status"],
        unique=False,
    )

    # ---------------------------------------------------------
    # MAINTENANCE RECORDS
    # ---------------------------------------------------------

    op.create_table(
        "maintenance_records",
        sa.Column("id", sa.Integer(), nullable=False),

        sa.Column(
            "computer_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "maintenance_type",
            sa.Enum(
                "preventive",
                "corrective",
                "emergency",
                "software",
                "hardware",
                name="maintenancetype",
                native_enum=False,
            ),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.Enum(
                "scheduled",
                "in_progress",
                "completed",
                "cancelled",
                name="maintenancestatus",
                native_enum=False,
            ),
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "work_performed",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "technician_name",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "created_by",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["computer_id"],
            ["computers.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_maintenance_records_computer_id"),
        "maintenance_records",
        ["computer_id"],
        unique=False,
    )

    op.create_index(
        "ix_maintenance_computer_status",
        "maintenance_records",
        ["computer_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "ix_maintenance_computer_status",
        table_name="maintenance_records",
    )

    op.drop_index(
        op.f("ix_maintenance_records_computer_id"),
        table_name="maintenance_records",
    )

    op.drop_table("maintenance_records")

    op.drop_index(
        "ix_issues_computer_status",
        table_name="issues",
    )

    op.drop_index(
        op.f("ix_issues_computer_id"),
        table_name="issues",
    )

    op.drop_table("issues")

    op.drop_index(
        "ix_usage_sessions_computer_started",
        table_name="usage_sessions",
    )

    op.drop_index(
        op.f("ix_usage_sessions_computer_id"),
        table_name="usage_sessions",
    )

    op.drop_table("usage_sessions")

    op.drop_index(
        "ix_software_computer_name_version",
        table_name="software",
    )

    op.drop_index(
        op.f("ix_software_computer_id"),
        table_name="software",
    )

    op.drop_table("software")