"""add install_location and architecture to software

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-10-14
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("software") as batch_op:
        batch_op.add_column(
            sa.Column("install_location", sa.String(length=500), nullable=True)
        )
        batch_op.add_column(
            sa.Column("architecture", sa.String(length=20), nullable=True)
        )
        batch_op.create_index(
            "ix_software_computer_publisher",
            ["computer_id", "publisher"],
        )


def downgrade() -> None:
    with op.batch_alter_table("software") as batch_op:
        batch_op.drop_index("ix_software_computer_publisher")
        batch_op.drop_column("architecture")
        batch_op.drop_column("install_location")
