"""Inscription des partenaires : SIRET vérifié dans l'annuaire, adresse géocodée (Base Adresse Nationale)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-02 05:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('merchants', sa.Column('siret', sa.String(length=14), nullable=True))
    op.add_column('merchants', sa.Column('siren', sa.String(length=9), nullable=True))
    op.add_column('merchants', sa.Column('contact_phone', sa.String(length=30), nullable=True))
    # Résultat de l'annuaire au moment de l'inscription ; {"status": "unavailable"} si le service n'a pas répondu.
    op.add_column('merchants', sa.Column('company_check', postgresql.JSONB(), nullable=True))
    op.add_column('merchants', sa.Column('company_checked_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('uq_merchants_siret', 'merchants', ['siret'], unique=True,
                    postgresql_where=sa.text('siret IS NOT NULL'))
    op.add_column('locations', sa.Column('geocode_label', sa.String(length=200), nullable=True))
    op.add_column('locations', sa.Column('geocode_score', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('locations', 'geocode_score')
    op.drop_column('locations', 'geocode_label')
    op.drop_index('uq_merchants_siret', table_name='merchants')
    op.drop_column('merchants', 'company_checked_at')
    op.drop_column('merchants', 'company_check')
    op.drop_column('merchants', 'contact_phone')
    op.drop_column('merchants', 'siren')
    op.drop_column('merchants', 'siret')
