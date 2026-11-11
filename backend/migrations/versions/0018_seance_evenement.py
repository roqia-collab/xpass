"""Séance réservable pour chaque événement.

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-11 18:40:00
"""
from alembic import op
import sqlalchemy as sa


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("venue_events", sa.Column("capacity", sa.Integer(), server_default="20", nullable=False))
    op.add_column("venue_events", sa.Column("offer_id", sa.UUID(), nullable=True))
    op.create_check_constraint("ck_venue_events_capacity_positive", "venue_events", "capacity > 0")
    op.create_foreign_key(
        op.f("fk_venue_events_offer_id"), "venue_events", "offers", ["offer_id"], ["id"], use_alter=True
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_venue_events_offer_id"), "venue_events", type_="foreignkey")
    op.drop_constraint("ck_venue_events_capacity_positive", "venue_events", type_="check")
    op.drop_column("venue_events", "offer_id")
    op.drop_column("venue_events", "capacity")
