"""add unique constraint to role permissions

Revision ID: fc9488c243e2
Revises: c7d4e9f2a1b3
Create Date: 2026-09-24
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "fc9488c243e2"
down_revision: Union[str, Sequence[str], None] = "c7d4e9f2a1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint to role permissions."""

    with op.batch_alter_table(
        "role_permissions",
        recreate="always",
    ) as batch_op:
        batch_op.create_unique_constraint(
            "uq_role_permission_action",
            ["role_id", "action_code"],
        )


def downgrade() -> None:
    """Remove unique constraint from role permissions."""

    with op.batch_alter_table(
        "role_permissions",
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_role_permission_action",
            type_="unique",
        )