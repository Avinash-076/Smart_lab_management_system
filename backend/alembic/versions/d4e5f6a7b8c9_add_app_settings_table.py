"""add app_settings table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create app_settings table for persistent runtime configuration."""
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), primary_key=True, nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("value_type", sa.String(length=20), nullable=False, server_default="string"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("requires_restart", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_app_settings_key", "app_settings", ["key"], unique=True)
    op.create_index("ix_app_settings_category", "app_settings", ["category"], unique=False)


def downgrade() -> None:
    """Drop app_settings table."""
    op.drop_index("ix_app_settings_category", table_name="app_settings")
    op.drop_index("ix_app_settings_key", table_name="app_settings")
    op.drop_table("app_settings")
