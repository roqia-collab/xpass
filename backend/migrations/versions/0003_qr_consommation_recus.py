"""QR éphémères, consommations, reçus et dettes partenaires (lot 3)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-31 20:21:44.737456
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Références de reçu lisibles (XP-10001, ...). Une séquence peut laisser des trous (transactions annulées).
    op.execute("CREATE SEQUENCE receipt_reference_seq START 10001")
    op.create_table('partner_payables',
    sa.Column('merchant_id', sa.UUID(), nullable=False),
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('booking_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Enum('redemption', 'late_cancellation', name='payable_kind', native_enum=False, create_constraint=True, length=24), nullable=False),
    sa.Column('credits', sa.Integer(), nullable=False),
    sa.Column('amount_minor', sa.BigInteger(), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('status', sa.Enum('pending_valuation', 'valued', 'paid', 'adjusted', name='payable_status', native_enum=False, create_constraint=True, length=24), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('(amount_minor IS NULL) = (currency IS NULL)', name=op.f('ck_partner_payables_money_complete')),
    sa.CheckConstraint('credits > 0', name=op.f('ck_partner_payables_credits_positive')),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_partner_payables_booking_id_bookings')),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_partner_payables_location_id_locations')),
    sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], name=op.f('fk_partner_payables_merchant_id_merchants')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_partner_payables'))
    )
    op.create_index(op.f('ix_partner_payables_merchant_id'), 'partner_payables', ['merchant_id'], unique=False)
    op.create_index('uq_partner_payables_booking', 'partner_payables', ['booking_id'], unique=True)
    op.create_table('qr_tokens',
    sa.Column('booking_id', sa.UUID(), nullable=False),
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('scanned_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('scanned_by', sa.UUID(), nullable=True),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_qr_tokens_booking_id_bookings')),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_qr_tokens_location_id_locations')),
    sa.ForeignKeyConstraint(['scanned_by'], ['users.id'], name=op.f('fk_qr_tokens_scanned_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_qr_tokens'))
    )
    op.create_index('ix_qr_tokens_booking', 'qr_tokens', ['booking_id'], unique=False)
    op.create_index('uq_qr_tokens_active_code', 'qr_tokens', ['location_id', 'code_hash'], unique=True, postgresql_where=sa.text('used_at IS NULL AND revoked_at IS NULL'))
    op.create_index('uq_qr_tokens_token_hash', 'qr_tokens', ['token_hash'], unique=True)
    op.create_table('receipts',
    sa.Column('booking_id', sa.UUID(), nullable=False),
    sa.Column('reference', sa.String(length=20), nullable=False),
    sa.Column('credits_total', sa.Integer(), nullable=False),
    sa.Column('funding', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_receipts_booking_id_bookings')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_receipts'))
    )
    op.create_index('uq_receipts_booking', 'receipts', ['booking_id'], unique=True)
    op.create_index('uq_receipts_reference', 'receipts', ['reference'], unique=True)
    op.create_table('redemptions',
    sa.Column('booking_id', sa.UUID(), nullable=False),
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('qr_token_id', sa.UUID(), nullable=False),
    sa.Column('method', sa.Enum('qr', 'code', name='redemption_method', native_enum=False, create_constraint=True, length=8), nullable=False),
    sa.Column('validated_by', sa.UUID(), nullable=False),
    sa.Column('credits', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_redemptions_booking_id_bookings')),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_redemptions_location_id_locations')),
    sa.ForeignKeyConstraint(['qr_token_id'], ['qr_tokens.id'], name=op.f('fk_redemptions_qr_token_id_qr_tokens')),
    sa.ForeignKeyConstraint(['validated_by'], ['users.id'], name=op.f('fk_redemptions_validated_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_redemptions'))
    )
    op.create_index(op.f('ix_redemptions_created_at'), 'redemptions', ['created_at'], unique=False)
    op.create_index(op.f('ix_redemptions_location_id'), 'redemptions', ['location_id'], unique=False)
    op.create_index('uq_redemptions_booking', 'redemptions', ['booking_id'], unique=True)
    op.add_column('bookings', sa.Column('redeemed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS receipt_reference_seq")
    op.drop_column('bookings', 'redeemed_at')
    op.drop_index('uq_redemptions_booking', table_name='redemptions')
    op.drop_index(op.f('ix_redemptions_location_id'), table_name='redemptions')
    op.drop_index(op.f('ix_redemptions_created_at'), table_name='redemptions')
    op.drop_table('redemptions')
    op.drop_index('uq_receipts_reference', table_name='receipts')
    op.drop_index('uq_receipts_booking', table_name='receipts')
    op.drop_table('receipts')
    op.drop_index('uq_qr_tokens_token_hash', table_name='qr_tokens')
    op.drop_index('uq_qr_tokens_active_code', table_name='qr_tokens', postgresql_where=sa.text('used_at IS NULL AND revoked_at IS NULL'))
    op.drop_index('ix_qr_tokens_booking', table_name='qr_tokens')
    op.drop_table('qr_tokens')
    op.drop_index('uq_partner_payables_booking', table_name='partner_payables')
    op.drop_index(op.f('ix_partner_payables_merchant_id'), table_name='partner_payables')
    op.drop_table('partner_payables')
