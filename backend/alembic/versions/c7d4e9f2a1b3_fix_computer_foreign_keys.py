"""fix computer foreign keys

Revision ID: c7d4e9f2a1b3
Revises: 8f3c2a1b4d6
Create Date: 2026-09-23

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "c7d4e9f2a1b3"
down_revision = "8f3c2a1b4d6"
branch_labels = None
depends_on = None


FK_NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
}


def upgrade() -> None:
    """
    Replace the existing computer_id foreign keys with
    ON DELETE CASCADE foreign keys.

    Existing rows are preserved by Alembic's batch table
    recreation mechanism.
    """

    # ---------------------------------------------------------
    # system_metrics
    # ---------------------------------------------------------
    with op.batch_alter_table(
        "system_metrics",
        recreate="always",
        naming_convention=FK_NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_system_metrics_computer_id_computers",
            type_="foreignkey",
        )

        batch_op.create_foreign_key(
            "fk_system_metrics_computer_id_computers",
            "computers",
            ["computer_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # ---------------------------------------------------------
    # notifications
    # ---------------------------------------------------------
    with op.batch_alter_table(
        "notifications",
        recreate="always",
        naming_convention=FK_NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_notifications_computer_id_computers",
            type_="foreignkey",
        )

        batch_op.create_foreign_key(
            "fk_notifications_computer_id_computers",
            "computers",
            ["computer_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # ---------------------------------------------------------
    # remote_commands
    # ---------------------------------------------------------
    with op.batch_alter_table(
        "remote_commands",
        recreate="always",
        naming_convention=FK_NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_remote_commands_computer_id_computers",
            type_="foreignkey",
        )

        batch_op.create_foreign_key(
            "fk_remote_commands_computer_id_computers",
            "computers",
            ["computer_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """
    Restore the original NO ACTION behavior for the
    computer foreign keys.
    """

    # ---------------------------------------------------------
    # remote_commands
    # ---------------------------------------------------------
    with op.batch_alter_table(
        "remote_commands",
        recreate="always",
        naming_convention=FK_NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_remote_commands_computer_id_computers",
            type_="foreignkey",
        )

        batch_op.create_foreign_key(
            "fk_remote_commands_computer_id_computers",
            "computers",
            ["computer_id"],
            ["id"],
        )

    # ---------------------------------------------------------
    # notifications
    # ---------------------------------------------------------
    with op.batch_alter_table(
        "notifications",
        recreate="always",
        naming_convention=FK_NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_notifications_computer_id_computers",
            type_="foreignkey",
        )

        batch_op.create_foreign_key(
            "fk_notifications_computer_id_computers",
            "computers",
            ["computer_id"],
            ["id"],
        )

    # ---------------------------------------------------------
    # system_metrics
    # ---------------------------------------------------------
    with op.batch_alter_table(
        "system_metrics",
        recreate="always",
        naming_convention=FK_NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_system_metrics_computer_id_computers",
            type_="foreignkey",
        )

        batch_op.create_foreign_key(
            "fk_system_metrics_computer_id_computers",
            "computers",
            ["computer_id"],
            ["id"],
        )