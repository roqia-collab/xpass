"""Message automatique d'accusé de réception (expéditeur système).

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-04 22:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_messages_sender_kind"), "messages", type_="check")
    op.create_check_constraint(
        op.f("ck_messages_sender_kind"),
        "messages",
        "sender_kind IN ('customer', 'partner', 'system')",
    )
    op.alter_column("messages", "sender_user_id", existing_type=sa.UUID(), nullable=True)
    op.create_check_constraint(
        op.f("ck_messages_system_no_user"),
        "messages",
        "(sender_kind = 'system') = (sender_user_id IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_messages_system_no_user"), "messages", type_="check")
    op.execute("DELETE FROM messages WHERE sender_kind = 'system'")
    op.alter_column("messages", "sender_user_id", existing_type=sa.UUID(), nullable=False)
    op.drop_constraint(op.f("ck_messages_sender_kind"), "messages", type_="check")
    op.create_check_constraint(
        op.f("ck_messages_sender_kind"),
        "messages",
        "sender_kind IN ('customer', 'partner')",
    )
