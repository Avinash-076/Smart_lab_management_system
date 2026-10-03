"""add idempotency constraints and keys

Revision ID: a1b2c3d4e5f6
Revises: e7a91c42b5d3, fc9488c243e2
Create Date: 2026-09-27
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = ("e7a91c42b5d3", "fc9488c243e2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add idempotency key columns and uniqueness constraints."""
    with op.batch_alter_table("system_metrics") as batch_op:
        batch_op.add_column(
            sa.Column("idempotency_key", sa.String(length=128), nullable=True)
        )
        batch_op.create_index(
            "ix_system_metrics_idempotency_key",
            ["idempotency_key"],
            unique=True,
        )

    with op.batch_alter_table("usage_sessions") as batch_op:
        batch_op.create_unique_constraint(
            "uq_usage_sessions_computer_app_started",
            ["computer_id", "application_name", "started_at"],
        )

    with op.batch_alter_table("issues") as batch_op:
        batch_op.add_column(
            sa.Column("idempotency_key", sa.String(length=128), nullable=True)
        )
        batch_op.create_index(
            "ix_issues_idempotency_key",
            ["idempotency_key"],
            unique=True,
        )


def downgrade() -> None:
    """Remove idempotency constraints and columns."""
    with op.batch_alter_table("issues") as batch_op:
        batch_op.drop_index("ix_issues_idempotency_key")
        batch_op.drop_column("idempotency_key")

    with op.batch_alter_table("usage_sessions") as batch_op:
        batch_op.drop_constraint(
            "uq_usage_sessions_computer_app_started",
            type_="unique",
        )

    with op.batch_alter_table("system_metrics") as batch_op:
        batch_op.drop_index("ix_system_metrics_idempotency_key")
        batch_op.drop_column("idempotency_key")
