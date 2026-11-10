"""Prix variable par créneau, annulation tardive à moitié rendue, absences (no-show)

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-04 15:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('bookings', sa.Column('price_adjustments', postgresql.ARRAY(sa.String(length=16)), nullable=True))
    op.add_column('bookings', sa.Column('refunded_credits', sa.Integer(), server_default='0', nullable=False))
    # Annulations déjà enregistrées : gratuites = tout rendu, tardives = rien (ancienne règle).
    op.execute("UPDATE bookings SET refunded_credits = total_credits WHERE status = 'cancelled' AND NOT late_cancellation")
    op.drop_constraint(op.f('ck_partner_payables_payable_kind'), 'partner_payables', type_='check')
    op.create_check_constraint(op.f('ck_partner_payables_payable_kind'), 'partner_payables',
                               "kind IN ('redemption', 'late_cancellation', 'no_show')")


def downgrade() -> None:
    op.drop_constraint(op.f('ck_partner_payables_payable_kind'), 'partner_payables', type_='check')
    # L'ancien schéma ne connaît pas les absences : elles redeviennent des dédommagements (montants inchangés).
    op.execute("UPDATE partner_payables SET kind = 'late_cancellation' WHERE kind = 'no_show'")
    op.create_check_constraint(op.f('ck_partner_payables_payable_kind'), 'partner_payables',
                               "kind IN ('redemption', 'late_cancellation')")
    op.drop_column('bookings', 'refunded_credits')
    op.drop_column('bookings', 'price_adjustments')
