"""Paiement en ligne des factures (aucune table) et clés d'API de synchronisation RH

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-03 10:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('organization_api_keys',
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('label', sa.String(length=80), nullable=False),
    sa.Column('prefix', sa.String(length=12), nullable=False),
    sa.Column('key_hash', sa.String(length=64), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_organization_api_keys_organization_id_organizations')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_organization_api_keys_created_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_organization_api_keys')),
    sa.UniqueConstraint('key_hash', name=op.f('uq_organization_api_keys_key_hash')))
    op.create_index(op.f('ix_organization_api_keys_organization_id'), 'organization_api_keys', ['organization_id'])


def downgrade() -> None:
    op.drop_table('organization_api_keys')
