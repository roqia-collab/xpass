"""Rattache un commerçant au service RH qui l'a créé.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-10 21:40:00
"""
from alembic import op
import sqlalchemy as sa


revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("merchants", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.create_index("ix_merchants_organization_id", "merchants", ["organization_id"])
    op.create_foreign_key(
        "fk_merchants_organization_id", "merchants", "organizations", ["organization_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_merchants_organization_id", "merchants", type_="foreignkey")
    op.drop_index("ix_merchants_organization_id", "merchants")
    op.drop_column("merchants", "organization_id")
