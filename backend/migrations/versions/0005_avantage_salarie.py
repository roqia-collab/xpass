"""Avantage salarié : contrats employeur, salariés, politiques, factures de financement, allocations (lot 6)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-02 00:57:06.624389
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


ACCOUNTS_OLD = "'psp_cash','customer_deferred','partner_expense','partner_payable','commission_revenue'"
ACCOUNTS_NEW = ACCOUNTS_OLD + ",'bank_cash','employer_prepaid'"


def _accounts(values: str, *, validate: bool = True) -> None:
    op.drop_constraint(op.f('ck_money_journal_lines_money_account'), 'money_journal_lines', type_='check')
    # Au retour arrière, le journal (ajout seul) peut déjà contenir les nouveaux comptes : la contrainte
    # restaurée ne s'applique alors qu'aux nouvelles lignes (NOT VALID).
    op.execute(f"ALTER TABLE money_journal_lines ADD CONSTRAINT ck_money_journal_lines_money_account "
               f"CHECK (account IN ({values})){'' if validate else ' NOT VALID'}")


def upgrade() -> None:
    op.execute("CREATE SEQUENCE employer_invoice_seq START 1")
    op.create_table('budget_policies',
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('credits_per_month', sa.Integer(), nullable=False),
    sa.Column('eligible_categories', postgresql.ARRAY(sa.String(length=32)), nullable=True),
    sa.Column('credit_validity_days', sa.Integer(), nullable=False),
    sa.Column('effective_from', sa.Date(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('credit_validity_days BETWEEN 7 AND 366', name=op.f('ck_budget_policies_validity_range')),
    sa.CheckConstraint('credits_per_month > 0', name=op.f('ck_budget_policies_credits_positive')),
    sa.CheckConstraint('extract(day from effective_from) = 1', name=op.f('ck_budget_policies_first_of_month')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_budget_policies_created_by_users')),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_budget_policies_organization_id_organizations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_budget_policies'))
    )
    op.create_index(op.f('ix_budget_policies_organization_id'), 'budget_policies', ['organization_id'], unique=False)
    op.create_index('uq_budget_policies_org_from', 'budget_policies', ['organization_id', 'effective_from'], unique=True)
    op.create_table('employees',
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('first_name', sa.String(length=80), nullable=False),
    sa.Column('last_name', sa.String(length=80), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.Enum('invited', 'active', 'suspended', 'removed', name='employee_status', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('invited_by', sa.UUID(), nullable=True),
    sa.Column('invited_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('email = lower(email)', name=op.f('ck_employees_email_lower')),
    sa.ForeignKeyConstraint(['invited_by'], ['users.id'], name=op.f('fk_employees_invited_by_users')),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_employees_organization_id_organizations')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_employees_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_employees'))
    )
    op.create_index(op.f('ix_employees_email'), 'employees', ['email'], unique=False)
    op.create_index(op.f('ix_employees_organization_id'), 'employees', ['organization_id'], unique=False)
    op.create_index('uq_employees_org_email', 'employees', ['organization_id', 'email'], unique=True)
    op.create_index('uq_employees_org_user', 'employees', ['organization_id', 'user_id'], unique=True, postgresql_where=sa.text('user_id IS NOT NULL'))
    op.create_table('employer_contracts',
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.Enum('draft', 'active', 'suspended', 'ended', name='contract_status', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('credit_price_minor', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('payment_terms_days', sa.Integer(), nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=False),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('credit_price_minor > 0', name=op.f('ck_employer_contracts_price_positive')),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_employer_contracts_organization_id_organizations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_employer_contracts'))
    )
    op.create_index('uq_employer_contracts_org', 'employer_contracts', ['organization_id'], unique=True)
    op.create_table('employer_invoices',
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('reference', sa.String(length=24), nullable=False),
    sa.Column('label', sa.String(length=120), nullable=False),
    sa.Column('amount_minor', sa.BigInteger(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('issued_on', sa.Date(), nullable=False),
    sa.Column('due_on', sa.Date(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'paid', 'void', name='employer_invoice_status', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('confirmed_by', sa.UUID(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('amount_minor > 0', name=op.f('ck_employer_invoices_amount_positive')),
    sa.ForeignKeyConstraint(['confirmed_by'], ['users.id'], name=op.f('fk_employer_invoices_confirmed_by_users')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_employer_invoices_created_by_users')),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_employer_invoices_organization_id_organizations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_employer_invoices'))
    )
    op.create_index(op.f('ix_employer_invoices_organization_id'), 'employer_invoices', ['organization_id'], unique=False)
    op.create_index('uq_employer_invoices_reference', 'employer_invoices', ['reference'], unique=True)
    op.create_table('employer_allocations',
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('employee_id', sa.UUID(), nullable=False),
    sa.Column('policy_id', sa.UUID(), nullable=False),
    sa.Column('period', sa.Date(), nullable=False),
    sa.Column('credits', sa.Integer(), nullable=False),
    sa.Column('cost_minor', sa.BigInteger(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('credit_lot_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('credits > 0 AND cost_minor > 0', name=op.f('ck_employer_allocations_positive')),
    sa.CheckConstraint('extract(day from period) = 1', name=op.f('ck_employer_allocations_first_of_month')),
    sa.ForeignKeyConstraint(['credit_lot_id'], ['credit_lots.id'], name=op.f('fk_employer_allocations_credit_lot_id_credit_lots')),
    sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], name=op.f('fk_employer_allocations_employee_id_employees')),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_employer_allocations_organization_id_organizations')),
    sa.ForeignKeyConstraint(['policy_id'], ['budget_policies.id'], name=op.f('fk_employer_allocations_policy_id_budget_policies')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_employer_allocations')),
    sa.UniqueConstraint('credit_lot_id', name=op.f('uq_employer_allocations_credit_lot_id'))
    )
    op.create_index(op.f('ix_employer_allocations_organization_id'), 'employer_allocations', ['organization_id'], unique=False)
    op.create_index('uq_employer_allocations_period', 'employer_allocations', ['employee_id', 'period'], unique=True)
    _accounts(ACCOUNTS_NEW)


def downgrade() -> None:
    _accounts(ACCOUNTS_OLD, validate=False)
    op.execute("DROP SEQUENCE IF EXISTS employer_invoice_seq")
    op.drop_index('uq_employer_allocations_period', table_name='employer_allocations')
    op.drop_index(op.f('ix_employer_allocations_organization_id'), table_name='employer_allocations')
    op.drop_table('employer_allocations')
    op.drop_index('uq_employer_invoices_reference', table_name='employer_invoices')
    op.drop_index(op.f('ix_employer_invoices_organization_id'), table_name='employer_invoices')
    op.drop_table('employer_invoices')
    op.drop_index('uq_employer_contracts_org', table_name='employer_contracts')
    op.drop_table('employer_contracts')
    op.drop_index('uq_employees_org_user', table_name='employees', postgresql_where=sa.text('user_id IS NOT NULL'))
    op.drop_index('uq_employees_org_email', table_name='employees')
    op.drop_index(op.f('ix_employees_organization_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_email'), table_name='employees')
    op.drop_table('employees')
    op.drop_index('uq_budget_policies_org_from', table_name='budget_policies')
    op.drop_index(op.f('ix_budget_policies_organization_id'), table_name='budget_policies')
    op.drop_table('budget_policies')
