"""add memory_mb and executable_path to processes

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-10-14
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "g7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("processes") as batch_op:
        batch_op.add_column(
            sa.Column("memory_mb", sa.Float(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("executable_path", sa.String(length=500), nullable=True)
        )
        batch_op.create_index(
            "ix_processes_computer_status",
            ["computer_id", "status"],
        )


def downgrade() -> None:
    with op.batch_alter_table("processes") as batch_op:
        batch_op.drop_index("ix_processes_computer_status")
        batch_op.drop_column("executable_path")
        batch_op.drop_column("memory_mb")
