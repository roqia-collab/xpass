"""Abonnements, factures, webhooks PSP, journal monétaire, barème et versements partenaires (lot 4)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-31 21:24:34.074620
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


MONEY_SQL = """
-- Équilibre par devise : chaque écriture monétaire doit sommer à zéro dans chaque devise.
CREATE FUNCTION money_journal_assert_balanced() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE bad text;
BEGIN
  SELECT currency INTO bad FROM money_journal_lines WHERE journal_id = NEW.journal_id
    GROUP BY currency HAVING sum(amount_minor) <> 0 LIMIT 1;
  IF bad IS NOT NULL THEN
    RAISE EXCEPTION 'Écriture monétaire % déséquilibrée en %', NEW.journal_id, bad USING ERRCODE = '23514';
  END IF;
  RETURN NULL;
END $$;

CREATE CONSTRAINT TRIGGER money_journal_lines_balanced
  AFTER INSERT ON money_journal_lines
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION money_journal_assert_balanced();

CREATE TRIGGER money_journals_append_only BEFORE UPDATE OR DELETE ON money_journals
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER money_journal_lines_append_only BEFORE UPDATE OR DELETE ON money_journal_lines
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
-- Un webhook reçu ne peut pas être supprimé (preuve de ce que le prestataire a envoyé).
CREATE TRIGGER payment_webhook_events_no_delete BEFORE DELETE ON payment_webhook_events
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
"""


def upgrade() -> None:
    op.create_table('money_journals',
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('memo', sa.String(length=200), nullable=False),
    sa.Column('ref_type', sa.String(length=32), nullable=False),
    sa.Column('ref_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_money_journals'))
    )
    op.create_table('payment_webhook_events',
    sa.Column('provider', sa.String(length=16), nullable=False),
    sa.Column('event_id', sa.String(length=120), nullable=False),
    sa.Column('event_type', sa.String(length=80), nullable=False),
    sa.Column('livemode', sa.Boolean(), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('outcome', sa.String(length=16), nullable=True),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_payment_webhook_events'))
    )
    op.create_index('ix_payment_webhook_events_pending', 'payment_webhook_events', ['received_at'], unique=False, postgresql_where=sa.text('processed_at IS NULL'))
    op.create_index('uq_payment_webhook_events', 'payment_webhook_events', ['provider', 'event_id'], unique=True)
    op.create_table('settlement_terms',
    sa.Column('market_id', sa.UUID(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('gross_minor_per_credit', sa.Integer(), nullable=False),
    sa.Column('commission_bps', sa.Integer(), nullable=False),
    sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('commission_bps BETWEEN 0 AND 10000', name=op.f('ck_settlement_terms_commission_range')),
    sa.CheckConstraint('gross_minor_per_credit > 0', name=op.f('ck_settlement_terms_rate_positive')),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], name=op.f('fk_settlement_terms_market_id_markets')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_settlement_terms'))
    )
    op.create_index('uq_settlement_terms_market_from', 'settlement_terms', ['market_id', 'effective_from'], unique=True)
    op.create_table('subscription_plans',
    sa.Column('market_id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('price_minor', sa.BigInteger(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('credits_per_period', sa.Integer(), nullable=False),
    sa.Column('credit_validity_days', sa.Integer(), nullable=True),
    sa.Column('psp_price_id', sa.String(length=120), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('price_minor > 0 AND credits_per_period > 0', name=op.f('ck_subscription_plans_positive')),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], name=op.f('fk_subscription_plans_market_id_markets')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_subscription_plans'))
    )
    op.create_index('uq_subscription_plans_market_code', 'subscription_plans', ['market_id', 'code'], unique=True)
    op.create_table('money_journal_lines',
    sa.Column('journal_id', sa.UUID(), nullable=False),
    sa.Column('account', sa.Enum('psp_cash', 'customer_deferred', 'partner_expense', 'partner_payable', 'commission_revenue', name='money_account', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('merchant_id', sa.UUID(), nullable=True),
    sa.Column('amount_minor', sa.BigInteger(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('amount_minor <> 0', name=op.f('ck_money_journal_lines_non_zero')),
    sa.ForeignKeyConstraint(['journal_id'], ['money_journals.id'], name=op.f('fk_money_journal_lines_journal_id_money_journals')),
    sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], name=op.f('fk_money_journal_lines_merchant_id_merchants')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_money_journal_lines'))
    )
    op.create_index(op.f('ix_money_journal_lines_journal_id'), 'money_journal_lines', ['journal_id'], unique=False)
    op.create_index(op.f('ix_money_journal_lines_merchant_id'), 'money_journal_lines', ['merchant_id'], unique=False)
    op.create_table('partner_payouts',
    sa.Column('merchant_id', sa.UUID(), nullable=False),
    sa.Column('period_start', sa.Date(), nullable=False),
    sa.Column('period_end', sa.Date(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('gross_minor', sa.BigInteger(), nullable=False),
    sa.Column('commission_minor', sa.BigInteger(), nullable=False),
    sa.Column('adjustments_minor', sa.BigInteger(), nullable=False),
    sa.Column('net_minor', sa.BigInteger(), nullable=False),
    sa.Column('visits', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'in_transit', 'paid', 'to_reconcile', 'failed', name='payout_status', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('provider', sa.String(length=16), nullable=True),
    sa.Column('psp_transfer_id', sa.String(length=120), nullable=True),
    sa.Column('confirmed_minor', sa.BigInteger(), nullable=True),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('net_minor = gross_minor - commission_minor + adjustments_minor', name=op.f('ck_partner_payouts_net_formula')),
    sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], name=op.f('fk_partner_payouts_merchant_id_merchants')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_partner_payouts')),
    sa.UniqueConstraint('psp_transfer_id', name=op.f('uq_partner_payouts_psp_transfer_id'))
    )
    op.create_index(op.f('ix_partner_payouts_merchant_id'), 'partner_payouts', ['merchant_id'], unique=False)
    op.create_index('uq_partner_payouts_period', 'partner_payouts', ['merchant_id', 'period_start', 'currency'], unique=True)
    op.create_table('subscriptions',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('market_id', sa.UUID(), nullable=False),
    sa.Column('plan_id', sa.UUID(), nullable=False),
    sa.Column('provider', sa.String(length=16), nullable=False),
    sa.Column('status', sa.Enum('incomplete', 'active', 'past_due', 'canceled', 'expired', name='subscription_status', native_enum=False, create_constraint=True, length=24), nullable=False),
    sa.Column('psp_checkout_id', sa.String(length=120), nullable=True),
    sa.Column('psp_customer_id', sa.String(length=120), nullable=True),
    sa.Column('psp_subscription_id', sa.String(length=120), nullable=True),
    sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
    sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False),
    sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], name=op.f('fk_subscriptions_market_id_markets')),
    sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], name=op.f('fk_subscriptions_plan_id_subscription_plans')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_subscriptions_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_subscriptions'))
    )
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    op.create_index('uq_subscriptions_checkout', 'subscriptions', ['provider', 'psp_checkout_id'], unique=True)
    op.create_index('uq_subscriptions_live', 'subscriptions', ['user_id', 'market_id'], unique=True, postgresql_where=sa.text("status IN ('incomplete','active','past_due')"))
    op.create_index('uq_subscriptions_psp', 'subscriptions', ['provider', 'psp_subscription_id'], unique=True)
    op.create_table('invoices',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('subscription_id', sa.UUID(), nullable=True),
    sa.Column('provider', sa.String(length=16), nullable=False),
    sa.Column('psp_invoice_id', sa.String(length=120), nullable=False),
    sa.Column('amount_minor', sa.BigInteger(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('credits', sa.Integer(), nullable=False),
    sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
    sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.Enum('paid', 'refunded', 'void', name='invoice_status', native_enum=False, create_constraint=True, length=24), nullable=False),
    sa.Column('livemode', sa.Boolean(), nullable=False),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('amount_minor >= 0', name=op.f('ck_invoices_amount_non_negative')),
    sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], name=op.f('fk_invoices_subscription_id_subscriptions')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_invoices_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_invoices'))
    )
    op.create_index(op.f('ix_invoices_subscription_id'), 'invoices', ['subscription_id'], unique=False)
    op.create_index(op.f('ix_invoices_user_id'), 'invoices', ['user_id'], unique=False)
    op.create_index('uq_invoices_psp', 'invoices', ['provider', 'psp_invoice_id'], unique=True)
    op.create_table('partner_adjustments',
    sa.Column('merchant_id', sa.UUID(), nullable=False),
    sa.Column('reference', sa.String(length=20), nullable=False),
    sa.Column('label', sa.String(length=160), nullable=False),
    sa.Column('amount_minor', sa.BigInteger(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('payout_id', sa.UUID(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('amount_minor <> 0', name=op.f('ck_partner_adjustments_non_zero')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_partner_adjustments_created_by_users')),
    sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], name=op.f('fk_partner_adjustments_merchant_id_merchants')),
    sa.ForeignKeyConstraint(['payout_id'], ['partner_payouts.id'], name=op.f('fk_partner_adjustments_payout_id_partner_payouts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_partner_adjustments'))
    )
    op.create_index(op.f('ix_partner_adjustments_merchant_id'), 'partner_adjustments', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_partner_adjustments_payout_id'), 'partner_adjustments', ['payout_id'], unique=False)
    op.create_index('uq_partner_adjustments_reference', 'partner_adjustments', ['reference'], unique=True)
    op.create_index('uq_credit_lots_invoice', 'credit_lots', ['origin_ref'], unique=True, postgresql_where=sa.text("origin_type = 'subscription_invoice'"))
    op.add_column('merchants', sa.Column('psp_account_id', sa.String(length=120), nullable=True))
    op.add_column('partner_payables', sa.Column('commission_minor', sa.BigInteger(), nullable=True))
    op.add_column('partner_payables', sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('partner_payables', sa.Column('valued_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('partner_payables', sa.Column('payout_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_partner_payables_payout_id'), 'partner_payables', ['payout_id'], unique=False)
    op.create_index('ix_partner_payables_unpaid', 'partner_payables', ['merchant_id', 'occurred_at'], unique=False, postgresql_where=sa.text('payout_id IS NULL'))
    op.create_foreign_key(op.f('fk_partner_payables_payout_id_partner_payouts'), 'partner_payables', 'partner_payouts', ['payout_id'], ['id'])
    # Contraintes modifiées (non détectées par l'autogénération).
    op.drop_constraint(op.f('ck_partner_payables_money_complete'), 'partner_payables', type_='check')
    op.create_check_constraint(
        op.f('ck_partner_payables_money_complete'), 'partner_payables',
        '(amount_minor IS NULL) = (currency IS NULL) AND (amount_minor IS NULL) = (commission_minor IS NULL)',
    )
    op.create_check_constraint(
        op.f('ck_partner_payables_commission_range'), 'partner_payables',
        'commission_minor IS NULL OR commission_minor BETWEEN 0 AND amount_minor',
    )
    op.execute("UPDATE partner_payables SET status = 'pending_valuation' WHERE status = 'adjusted'")
    op.drop_constraint(op.f('ck_partner_payables_payable_status'), 'partner_payables', type_='check')
    op.create_check_constraint(
        op.f('ck_partner_payables_payable_status'), 'partner_payables',
        "status IN ('pending_valuation','valued','in_payout','paid')",
    )
    op.execute(MONEY_SQL)
    op.execute("CREATE SEQUENCE adjustment_reference_seq START 1001")


def downgrade() -> None:
    for trg, table in [
        ('payment_webhook_events_no_delete', 'payment_webhook_events'),
        ('money_journal_lines_append_only', 'money_journal_lines'),
        ('money_journals_append_only', 'money_journals'),
        ('money_journal_lines_balanced', 'money_journal_lines'),
    ]:
        op.execute(f"DROP TRIGGER IF EXISTS {trg} ON {table}")
    op.execute("DROP FUNCTION IF EXISTS money_journal_assert_balanced()")
    op.execute("DROP SEQUENCE IF EXISTS adjustment_reference_seq")
    op.drop_constraint(op.f('ck_partner_payables_payable_status'), 'partner_payables', type_='check')
    op.execute("UPDATE partner_payables SET status = 'valued' WHERE status = 'in_payout'")
    op.create_check_constraint(
        op.f('ck_partner_payables_payable_status'), 'partner_payables',
        "status IN ('pending_valuation','valued','paid','adjusted')",
    )
    op.drop_constraint(op.f('ck_partner_payables_commission_range'), 'partner_payables', type_='check')
    op.drop_constraint(op.f('ck_partner_payables_money_complete'), 'partner_payables', type_='check')
    op.create_check_constraint(
        op.f('ck_partner_payables_money_complete'), 'partner_payables', '(amount_minor IS NULL) = (currency IS NULL)'
    )
    op.drop_constraint(op.f('fk_partner_payables_payout_id_partner_payouts'), 'partner_payables', type_='foreignkey')
    op.drop_index('ix_partner_payables_unpaid', table_name='partner_payables', postgresql_where=sa.text('payout_id IS NULL'))
    op.drop_index(op.f('ix_partner_payables_payout_id'), table_name='partner_payables')
    op.drop_column('partner_payables', 'payout_id')
    op.drop_column('partner_payables', 'valued_at')
    op.drop_column('partner_payables', 'occurred_at')
    op.drop_column('partner_payables', 'commission_minor')
    op.drop_column('merchants', 'psp_account_id')
    op.drop_index('uq_credit_lots_invoice', table_name='credit_lots', postgresql_where=sa.text("origin_type = 'subscription_invoice'"))
    op.drop_index('uq_partner_adjustments_reference', table_name='partner_adjustments')
    op.drop_index(op.f('ix_partner_adjustments_payout_id'), table_name='partner_adjustments')
    op.drop_index(op.f('ix_partner_adjustments_merchant_id'), table_name='partner_adjustments')
    op.drop_table('partner_adjustments')
    op.drop_index('uq_invoices_psp', table_name='invoices')
    op.drop_index(op.f('ix_invoices_user_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_subscription_id'), table_name='invoices')
    op.drop_table('invoices')
    op.drop_index('uq_subscriptions_psp', table_name='subscriptions')
    op.drop_index('uq_subscriptions_live', table_name='subscriptions', postgresql_where=sa.text("status IN ('incomplete','active','past_due')"))
    op.drop_index('uq_subscriptions_checkout', table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    op.drop_index('uq_partner_payouts_period', table_name='partner_payouts')
    op.drop_index(op.f('ix_partner_payouts_merchant_id'), table_name='partner_payouts')
    op.drop_table('partner_payouts')
    op.drop_index(op.f('ix_money_journal_lines_merchant_id'), table_name='money_journal_lines')
    op.drop_index(op.f('ix_money_journal_lines_journal_id'), table_name='money_journal_lines')
    op.drop_table('money_journal_lines')
    op.drop_index('uq_subscription_plans_market_code', table_name='subscription_plans')
    op.drop_table('subscription_plans')
    op.drop_index('uq_settlement_terms_market_from', table_name='settlement_terms')
    op.drop_table('settlement_terms')
    op.drop_index('uq_payment_webhook_events', table_name='payment_webhook_events')
    op.drop_index('ix_payment_webhook_events_pending', table_name='payment_webhook_events', postgresql_where=sa.text('processed_at IS NULL'))
    op.drop_table('payment_webhook_events')
    op.drop_table('money_journals')
