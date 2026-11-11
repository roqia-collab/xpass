"""Événements publiés par un service RH sur l'établissement d'un commerçant.

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-11 17:10:00
"""
from alembic import op
import sqlalchemy as sa


revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "venue_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_credits", sa.Integer(), nullable=False),
        sa.Column("cover_image_key", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="published"),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("ends_at > starts_at", name=op.f("ck_venue_events_event_span")),
        sa.CheckConstraint("price_credits > 0", name=op.f("ck_venue_events_event_price_positive")),
        sa.CheckConstraint("status IN ('published', 'hidden')", name=op.f("ck_venue_events_status")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_venue_events_organization_id")),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], name=op.f("fk_venue_events_location_id")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_venue_events_created_by")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_venue_events")),
    )
    op.create_index("ix_venue_events_organization_id", "venue_events", ["organization_id"])
    op.create_index("ix_venue_events_location_id", "venue_events", ["location_id"])
    op.create_index("ix_venue_events_starts_at", "venue_events", ["starts_at"])


def downgrade() -> None:
    op.drop_index("ix_venue_events_starts_at", table_name="venue_events")
    op.drop_index("ix_venue_events_location_id", table_name="venue_events")
    op.drop_index("ix_venue_events_organization_id", table_name="venue_events")
    op.drop_table("venue_events")
