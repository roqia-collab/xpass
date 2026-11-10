"""Changement de formule d'abonnement au prochain renouvellement

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-04 16:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('subscriptions', sa.Column('pending_plan_id', sa.UUID(), nullable=True))
    op.create_foreign_key(op.f('fk_subscriptions_pending_plan_id_subscription_plans'), 'subscriptions',
                          'subscription_plans', ['pending_plan_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint(op.f('fk_subscriptions_pending_plan_id_subscription_plans'), 'subscriptions', type_='foreignkey')
    op.drop_column('subscriptions', 'pending_plan_id')
