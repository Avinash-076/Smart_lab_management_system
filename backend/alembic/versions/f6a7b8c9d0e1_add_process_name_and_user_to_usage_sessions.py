"""add process_name and user to usage_sessions

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-14
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("usage_sessions") as batch_op:
        batch_op.add_column(
            sa.Column("process_name", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("user", sa.String(length=255), nullable=True)
        )
        batch_op.create_index(
            "ix_usage_sessions_computer_app",
            ["computer_id", "application_name"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("usage_sessions") as batch_op:
        batch_op.drop_index("ix_usage_sessions_computer_app")
        batch_op.drop_column("user")
        batch_op.drop_column("process_name")
