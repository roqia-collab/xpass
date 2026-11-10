"""Profil, préférences et demandes d'assistance (lot 8a)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-02 01:46:33.199577
"""
from alembic import op
import sqlalchemy as sa


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('support_requests',
    sa.Column('reference', sa.String(length=16), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('category', sa.Enum('booking', 'credits', 'account', 'partner', 'other', name='support_category', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('subject', sa.String(length=160), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('booking_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.Enum('open', 'answered', 'closed', name='support_status', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('reply', sa.Text(), nullable=True),
    sa.Column('replied_by', sa.UUID(), nullable=True),
    sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_support_requests_booking_id_bookings')),
    sa.ForeignKeyConstraint(['replied_by'], ['users.id'], name=op.f('fk_support_requests_replied_by_users')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_support_requests_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_support_requests'))
    )
    op.create_index(op.f('ix_support_requests_user_id'), 'support_requests', ['user_id'], unique=False)
    op.create_index('uq_support_requests_reference', 'support_requests', ['reference'], unique=True)
    op.add_column('users', sa.Column('locale', sa.String(length=5), server_default='fr', nullable=False))
    op.add_column('users', sa.Column('notify_email', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("CREATE SEQUENCE support_reference_seq START 1001")
    op.create_check_constraint(op.f("ck_users_locale"), "users", "locale IN ('fr','en','ar')")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_users_locale"), "users", type_="check")
    op.execute("DROP SEQUENCE IF EXISTS support_reference_seq")
    op.drop_column('users', 'deleted_at')
    op.drop_column('users', 'notify_email')
    op.drop_column('users', 'locale')
    op.drop_index('uq_support_requests_reference', table_name='support_requests')
    op.drop_index(op.f('ix_support_requests_user_id'), table_name='support_requests')
    op.drop_table('support_requests')
