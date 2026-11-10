"""Administration : journal d'audit en ajout seul, litiges (lot 7)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-02 01:24:48.671196
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('audit_events',
    sa.Column('actor_kind', sa.String(length=16), nullable=False),
    sa.Column('actor_user_id', sa.UUID(), nullable=True),
    sa.Column('action', sa.String(length=48), nullable=False),
    sa.Column('object_type', sa.String(length=32), nullable=False),
    sa.Column('object_id', sa.Uuid(), nullable=False),
    sa.Column('object_label', sa.String(length=200), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], name=op.f('fk_audit_events_actor_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_events'))
    )
    op.create_index('ix_audit_events_created', 'audit_events', ['created_at'], unique=False)
    op.create_index('ix_audit_events_object', 'audit_events', ['object_type', 'object_id'], unique=False)
    op.create_table('disputes',
    sa.Column('reference', sa.String(length=16), nullable=False),
    sa.Column('booking_id', sa.UUID(), nullable=False),
    sa.Column('opened_by', sa.UUID(), nullable=True),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('open', 'in_review', 'waiting_customer', 'resolved_refund', 'resolved_rejected', name='dispute_status', native_enum=False, create_constraint=True, length=24), nullable=False),
    sa.Column('operator_notes', sa.Text(), nullable=True),
    sa.Column('credits_restored', sa.Integer(), nullable=True),
    sa.Column('partner_adjustment_minor', sa.BigInteger(), nullable=True),
    sa.Column('resolution_reason', sa.Text(), nullable=True),
    sa.Column('resolved_by', sa.UUID(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('credits_restored IS NULL OR credits_restored > 0', name=op.f('ck_disputes_credits_positive')),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_disputes_booking_id_bookings')),
    sa.ForeignKeyConstraint(['opened_by'], ['users.id'], name=op.f('fk_disputes_opened_by_users')),
    sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], name=op.f('fk_disputes_resolved_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_disputes'))
    )
    op.create_index(op.f('ix_disputes_booking_id'), 'disputes', ['booking_id'], unique=False)
    op.create_index('uq_disputes_open_booking', 'disputes', ['booking_id'], unique=True, postgresql_where=sa.text("status IN ('open','in_review','waiting_customer')"))
    op.create_index('uq_disputes_reference', 'disputes', ['reference'], unique=True)
    op.create_index('uq_credit_lots_dispute_refund', 'credit_lots', ['origin_ref'], unique=True, postgresql_where=sa.text("origin_type = 'dispute_refund'"))
    op.execute("CREATE SEQUENCE dispute_reference_seq START 1001")
    op.execute("CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events "
               "FOR EACH ROW EXECUTE FUNCTION forbid_mutation()")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events")
    op.execute("DROP SEQUENCE IF EXISTS dispute_reference_seq")
    op.drop_index('uq_credit_lots_dispute_refund', table_name='credit_lots', postgresql_where=sa.text("origin_type = 'dispute_refund'"))
    op.drop_index('uq_disputes_reference', table_name='disputes')
    op.drop_index('uq_disputes_open_booking', table_name='disputes', postgresql_where=sa.text("status IN ('open','in_review','waiting_customer')"))
    op.drop_index(op.f('ix_disputes_booking_id'), table_name='disputes')
    op.drop_table('disputes')
    op.drop_index('ix_audit_events_object', table_name='audit_events')
    op.drop_index('ix_audit_events_created', table_name='audit_events')
    op.drop_table('audit_events')
