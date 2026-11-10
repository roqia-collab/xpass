"""Plusieurs établissements par commerçant : demandes de modification (nom, activité, adresse) validées par XPASS

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-02 08:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('location_change_requests',
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('requested_by', sa.UUID(), nullable=False),
    sa.Column('changes', postgresql.JSONB(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='change_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('decision_reason', sa.Text(), nullable=True),
    sa.Column('decided_by', sa.UUID(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_location_change_requests_location_id_locations'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], name=op.f('fk_location_change_requests_requested_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_location_change_requests'))
    )
    op.create_index(op.f('ix_location_change_requests_location_id'), 'location_change_requests', ['location_id'], unique=False)
    # Une seule demande en attente par établissement.
    op.create_index('uq_location_change_pending', 'location_change_requests', ['location_id'], unique=True,
                    postgresql_where=sa.text("status = 'pending'"))


def downgrade() -> None:
    op.drop_index('uq_location_change_pending', table_name='location_change_requests')
    op.drop_index(op.f('ix_location_change_requests_location_id'), table_name='location_change_requests')
    op.drop_table('location_change_requests')
