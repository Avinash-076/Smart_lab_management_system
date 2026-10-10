"""add user fields and role description

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add full_name, email, is_active, created_at to users, and description to roles."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("full_name", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("email", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True)
        )

    with op.batch_alter_table("roles") as batch_op:
        batch_op.add_column(
            sa.Column("description", sa.String(length=255), nullable=True)
        )


def downgrade() -> None:
    """Remove user fields and role description."""
    with op.batch_alter_table("roles") as batch_op:
        batch_op.drop_column("description")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("created_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("email")
        batch_op.drop_column("full_name")
