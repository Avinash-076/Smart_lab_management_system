"""add duration and expand command fields

Revision ID: i9d0e1f2a3b4
Revises: h8c9d0e1f2a3
Create Date: 2026-10-14
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "i9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "h8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("remote_commands") as batch_op:
        batch_op.alter_column(
            "payload",
            existing_type=sa.String(length=255),
            type_=sa.String(length=1000),
            existing_nullable=True,
        )
        batch_op.create_index(
            "ix_remote_commands_computer_created",
            ["computer_id", "created_at"],
        )

    with op.batch_alter_table("command_results") as batch_op:
        batch_op.alter_column(
            "message",
            existing_type=sa.String(length=255),
            type_=sa.String(length=1000),
            existing_nullable=True,
        )
        batch_op.add_column(
            sa.Column("duration_seconds", sa.Float(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("command_results") as batch_op:
        batch_op.drop_column("duration_seconds")
        batch_op.alter_column(
            "message",
            existing_type=sa.String(length=1000),
            type_=sa.String(length=255),
            existing_nullable=True,
        )

    with op.batch_alter_table("remote_commands") as batch_op:
        batch_op.drop_index("ix_remote_commands_computer_created")
        batch_op.alter_column(
            "payload",
            existing_type=sa.String(length=1000),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
