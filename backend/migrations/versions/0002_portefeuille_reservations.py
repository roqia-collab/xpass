"""Portefeuille, réservations, idempotence et outbox (lot 2)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31 19:52:49.391475
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


LEDGER_SQL = """
-- Équilibre : la somme des lignes d'une écriture doit être nulle. Vérifié à la fin de la
-- transaction (trigger de contrainte DIFFÉRÉ) : un CHECK de ligne ne peut pas vérifier une somme.
CREATE FUNCTION credit_journal_assert_balanced() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE total bigint; n int;
BEGIN
  SELECT coalesce(sum(amount), 0), count(*) INTO total, n
    FROM credit_journal_lines WHERE journal_id = NEW.journal_id;
  IF total <> 0 THEN
    RAISE EXCEPTION 'Écriture % déséquilibrée (somme %)', NEW.journal_id, total USING ERRCODE = '23514';
  END IF;
  IF n < 2 THEN
    RAISE EXCEPTION 'Écriture % : au moins deux lignes requises', NEW.journal_id USING ERRCODE = '23514';
  END IF;
  RETURN NULL;
END $$;

CREATE CONSTRAINT TRIGGER credit_journal_lines_balanced
  AFTER INSERT ON credit_journal_lines
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION credit_journal_assert_balanced();

-- Journal append-only : ni modification ni suppression ; les corrections passent par contre-écriture.
CREATE FUNCTION forbid_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'Table % en ajout seul : % interdit', TG_TABLE_NAME, TG_OP USING ERRCODE = '42501';
END $$;

CREATE TRIGGER credit_journals_append_only BEFORE UPDATE OR DELETE ON credit_journals
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER credit_journal_lines_append_only BEFORE UPDATE OR DELETE ON credit_journal_lines
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
"""


def upgrade() -> None:
    op.create_table('outbox_events',
    sa.Column('aggregate_type', sa.String(length=40), nullable=False),
    sa.Column('aggregate_id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sa.String(length=60), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('last_error', sa.String(length=500), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_outbox_events'))
    )
    op.create_index('ix_outbox_pending', 'outbox_events', ['created_at'], unique=False, postgresql_where=sa.text('published_at IS NULL'))
    op.create_table('idempotency_keys',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('scope', sa.String(length=80), nullable=False),
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('request_hash', sa.String(length=64), nullable=False),
    sa.Column('response_status', sa.SmallInteger(), nullable=False),
    sa.Column('response_body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_idempotency_keys_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_idempotency_keys')),
    sa.UniqueConstraint('user_id', 'scope', 'key', name=op.f('uq_idempotency_keys_user_id'))
    )
    op.create_table('wallets',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('market_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], name=op.f('fk_wallets_market_id_markets')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_wallets_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_wallets')),
    sa.UniqueConstraint('user_id', 'market_id', name=op.f('uq_wallets_user_id'))
    )
    op.create_index(op.f('ix_wallets_user_id'), 'wallets', ['user_id'], unique=False)
    op.create_table('credit_lots',
    sa.Column('wallet_id', sa.UUID(), nullable=False),
    sa.Column('source', sa.Enum('personal', 'employer', 'promotional', name='credit_source', native_enum=False, create_constraint=True, length=24), nullable=False),
    sa.Column('origin_type', sa.String(length=40), nullable=False),
    sa.Column('origin_ref', sa.String(length=120), nullable=True),
    sa.Column('label', sa.String(length=120), nullable=False),
    sa.Column('granted_credits', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('eligible_categories', postgresql.ARRAY(sa.String(length=32)), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('granted_credits > 0', name=op.f('ck_credit_lots_granted_positive')),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], name=op.f('fk_credit_lots_wallet_id_wallets')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_credit_lots'))
    )
    op.create_index(op.f('ix_credit_lots_wallet_id'), 'credit_lots', ['wallet_id'], unique=False)
    op.create_table('credit_lot_balances',
    sa.Column('lot_id', sa.UUID(), nullable=False),
    sa.Column('available', sa.Integer(), nullable=False),
    sa.Column('reserved', sa.Integer(), nullable=False),
    sa.Column('consumed', sa.Integer(), nullable=False),
    sa.Column('expired', sa.Integer(), nullable=False),
    sa.CheckConstraint('available >= 0', name=op.f('ck_credit_lot_balances_available_nonneg')),
    sa.CheckConstraint('consumed >= 0', name=op.f('ck_credit_lot_balances_consumed_nonneg')),
    sa.CheckConstraint('expired >= 0', name=op.f('ck_credit_lot_balances_expired_nonneg')),
    sa.CheckConstraint('reserved >= 0', name=op.f('ck_credit_lot_balances_reserved_nonneg')),
    sa.ForeignKeyConstraint(['lot_id'], ['credit_lots.id'], name=op.f('fk_credit_lot_balances_lot_id_credit_lots'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('lot_id', name=op.f('pk_credit_lot_balances'))
    )
    op.create_table('external_blocks',
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('resource_id', sa.UUID(), nullable=False),
    sa.Column('during', postgresql.TSTZRANGE(), nullable=False),
    sa.Column('reason', sa.String(length=160), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_external_blocks_created_by_users')),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_external_blocks_location_id_locations')),
    sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], name=op.f('fk_external_blocks_resource_id_resources')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_external_blocks'))
    )
    op.create_index(op.f('ix_external_blocks_location_id'), 'external_blocks', ['location_id'], unique=False)
    op.create_table('session_inventories',
    sa.Column('offer_id', sa.UUID(), nullable=False),
    sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('capacity', sa.Integer(), nullable=False),
    sa.Column('reserved', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('capacity > 0', name=op.f('ck_session_inventories_capacity_positive')),
    sa.CheckConstraint('reserved >= 0 AND reserved <= capacity', name=op.f('ck_session_inventories_reserved_within_capacity')),
    sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], name=op.f('fk_session_inventories_offer_id_offers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_session_inventories')),
    sa.UniqueConstraint('offer_id', 'starts_at', name=op.f('uq_session_inventories_offer_id'))
    )
    op.create_table('bookings',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('wallet_id', sa.UUID(), nullable=False),
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('offer_id', sa.UUID(), nullable=False),
    sa.Column('offer_version_id', sa.UUID(), nullable=False),
    sa.Column('resource_id', sa.UUID(), nullable=True),
    sa.Column('inventory_id', sa.UUID(), nullable=True),
    sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('party_size', sa.SmallInteger(), nullable=False),
    sa.Column('price_credits_per_person', sa.Integer(), nullable=False),
    sa.Column('total_credits', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('held', 'confirmed', 'cancelled', 'expired', 'redeemed', 'no_show', name='booking_status', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('hold_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('free_cancellation_until', sa.DateTime(timezone=True), nullable=False),
    sa.Column('late_cancellation', sa.Boolean(), nullable=False),
    sa.Column('cancel_reason', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expired_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint("status <> 'held' OR hold_expires_at IS NOT NULL", name=op.f('ck_bookings_held_has_expiry')),
    sa.CheckConstraint('ends_at > starts_at', name=op.f('ck_bookings_ends_after_start')),
    sa.CheckConstraint('party_size >= 1', name=op.f('ck_bookings_party_positive')),
    sa.CheckConstraint('total_credits = price_credits_per_person * party_size', name=op.f('ck_bookings_total_matches')),
    sa.ForeignKeyConstraint(['inventory_id'], ['session_inventories.id'], name=op.f('fk_bookings_inventory_id_session_inventories')),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_bookings_location_id_locations')),
    sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], name=op.f('fk_bookings_offer_id_offers')),
    sa.ForeignKeyConstraint(['offer_version_id'], ['offer_versions.id'], name=op.f('fk_bookings_offer_version_id_offer_versions')),
    sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], name=op.f('fk_bookings_resource_id_resources')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_bookings_user_id_users')),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], name=op.f('fk_bookings_wallet_id_wallets')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bookings'))
    )
    op.create_index('ix_bookings_held_expiry', 'bookings', ['hold_expires_at'], unique=False, postgresql_where=sa.text("status = 'held'"))
    op.create_index('ix_bookings_location_start', 'bookings', ['location_id', 'starts_at'], unique=False)
    op.create_index(op.f('ix_bookings_user_id'), 'bookings', ['user_id'], unique=False)
    op.create_index('uq_bookings_active_user_offer_start', 'bookings', ['user_id', 'offer_id', 'starts_at'], unique=True, postgresql_where=sa.text("status IN ('held', 'confirmed')"))
    op.create_table('credit_journals',
    sa.Column('wallet_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Enum('grant', 'reserve', 'release', 'capture', 'expire', 'adjustment', name='journal_kind', native_enum=False, create_constraint=True, length=24), nullable=False),
    sa.Column('booking_id', sa.UUID(), nullable=True),
    sa.Column('reverses_journal_id', sa.UUID(), nullable=True),
    sa.Column('memo', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_credit_journals_booking_id_bookings')),
    sa.ForeignKeyConstraint(['reverses_journal_id'], ['credit_journals.id'], name=op.f('fk_credit_journals_reverses_journal_id_credit_journals')),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], name=op.f('fk_credit_journals_wallet_id_wallets')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_credit_journals'))
    )
    op.create_index(op.f('ix_credit_journals_booking_id'), 'credit_journals', ['booking_id'], unique=False)
    op.create_index(op.f('ix_credit_journals_created_at'), 'credit_journals', ['created_at'], unique=False)
    op.create_index(op.f('ix_credit_journals_wallet_id'), 'credit_journals', ['wallet_id'], unique=False)
    op.create_table('resource_occupancies',
    sa.Column('resource_id', sa.UUID(), nullable=False),
    sa.Column('booking_id', sa.UUID(), nullable=True),
    sa.Column('external_block_id', sa.UUID(), nullable=True),
    sa.Column('during', postgresql.TSTZRANGE(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    postgresql.ExcludeConstraint((sa.column('resource_id'), '='), (sa.column('during'), '&&'), where=sa.text('is_active'), using='gist', name='ex_resource_occupancies_no_overlap'),
    sa.CheckConstraint('num_nonnulls(booking_id, external_block_id) = 1', name=op.f('ck_resource_occupancies_one_owner')),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_resource_occupancies_booking_id_bookings')),
    sa.ForeignKeyConstraint(['external_block_id'], ['external_blocks.id'], name=op.f('fk_resource_occupancies_external_block_id_external_blocks')),
    sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], name=op.f('fk_resource_occupancies_resource_id_resources')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resource_occupancies')),
    sa.UniqueConstraint('booking_id', name=op.f('uq_resource_occupancies_booking_id')),
    sa.UniqueConstraint('external_block_id', name=op.f('uq_resource_occupancies_external_block_id'))
    )
    op.create_table('credit_journal_lines',
    sa.Column('journal_id', sa.UUID(), nullable=False),
    sa.Column('lot_id', sa.UUID(), nullable=False),
    sa.Column('account', sa.Enum('issuance', 'available', 'reserved', 'consumed', 'expired', name='credit_account', native_enum=False, create_constraint=True, length=24), nullable=False),
    sa.Column('amount', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('amount <> 0', name=op.f('ck_credit_journal_lines_amount_nonzero')),
    sa.ForeignKeyConstraint(['journal_id'], ['credit_journals.id'], name=op.f('fk_credit_journal_lines_journal_id_credit_journals')),
    sa.ForeignKeyConstraint(['lot_id'], ['credit_lots.id'], name=op.f('fk_credit_journal_lines_lot_id_credit_lots')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_credit_journal_lines'))
    )
    op.create_index(op.f('ix_credit_journal_lines_journal_id'), 'credit_journal_lines', ['journal_id'], unique=False)
    op.create_index(op.f('ix_credit_journal_lines_lot_id'), 'credit_journal_lines', ['lot_id'], unique=False)
    op.execute(LEDGER_SQL)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS credit_journal_lines_append_only ON credit_journal_lines")
    op.execute("DROP TRIGGER IF EXISTS credit_journals_append_only ON credit_journals")
    op.execute("DROP TRIGGER IF EXISTS credit_journal_lines_balanced ON credit_journal_lines")
    op.execute("DROP FUNCTION IF EXISTS forbid_mutation()")
    op.execute("DROP FUNCTION IF EXISTS credit_journal_assert_balanced()")
    op.drop_index(op.f('ix_credit_journal_lines_lot_id'), table_name='credit_journal_lines')
    op.drop_index(op.f('ix_credit_journal_lines_journal_id'), table_name='credit_journal_lines')
    op.drop_table('credit_journal_lines')
    op.drop_table('resource_occupancies')
    op.drop_index(op.f('ix_credit_journals_wallet_id'), table_name='credit_journals')
    op.drop_index(op.f('ix_credit_journals_created_at'), table_name='credit_journals')
    op.drop_index(op.f('ix_credit_journals_booking_id'), table_name='credit_journals')
    op.drop_table('credit_journals')
    op.drop_index('uq_bookings_active_user_offer_start', table_name='bookings', postgresql_where=sa.text("status IN ('held', 'confirmed')"))
    op.drop_index(op.f('ix_bookings_user_id'), table_name='bookings')
    op.drop_index('ix_bookings_location_start', table_name='bookings')
    op.drop_index('ix_bookings_held_expiry', table_name='bookings', postgresql_where=sa.text("status = 'held'"))
    op.drop_table('bookings')
    op.drop_table('session_inventories')
    op.drop_index(op.f('ix_external_blocks_location_id'), table_name='external_blocks')
    op.drop_table('external_blocks')
    op.drop_table('credit_lot_balances')
    op.drop_index(op.f('ix_credit_lots_wallet_id'), table_name='credit_lots')
    op.drop_table('credit_lots')
    op.drop_index(op.f('ix_wallets_user_id'), table_name='wallets')
    op.drop_table('wallets')
    op.drop_table('idempotency_keys')
    op.drop_index('ix_outbox_pending', table_name='outbox_events', postgresql_where=sa.text('published_at IS NULL'))
    op.drop_table('outbox_events')
