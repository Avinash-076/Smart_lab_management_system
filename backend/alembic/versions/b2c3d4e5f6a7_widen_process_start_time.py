"""widen process start_time column
Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-02
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Widen processes.start_time from String(30) to String(64)."""
    with op.batch_alter_table("processes") as batch_op:
        batch_op.alter_column(
            "start_time",
            existing_type=sa.String(length=30),
            type_=sa.String(length=64),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Revert processes.start_time to String(30)."""
    with op.batch_alter_table("processes") as batch_op:
        batch_op.alter_column(
            "start_time",
            existing_type=sa.String(length=64),
            type_=sa.String(length=30),
            existing_nullable=True,
        )
