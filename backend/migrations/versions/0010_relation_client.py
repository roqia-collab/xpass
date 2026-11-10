"""Relation client : messagerie par réservation, favoris, avis notés, appareils de notification, rappel de la veille

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-02 09:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def _enum(*values, name):
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=16)


def upgrade() -> None:
    op.create_table('conversations',
    sa.Column('booking_id', sa.UUID(), nullable=False),
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('customer_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('customer_read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('partner_read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_conversations_booking_id_bookings')),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_conversations_location_id_locations')),
    sa.ForeignKeyConstraint(['customer_id'], ['users.id'], name=op.f('fk_conversations_customer_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_conversations')),
    sa.UniqueConstraint('booking_id', name=op.f('uq_conversations_booking_id')))
    op.create_index(op.f('ix_conversations_location_id'), 'conversations', ['location_id'])
    op.create_index(op.f('ix_conversations_customer_id'), 'conversations', ['customer_id'])

    op.create_table('messages',
    sa.Column('conversation_id', sa.UUID(), nullable=False),
    sa.Column('sender_kind', _enum('customer', 'partner', name='sender_kind'), nullable=False),
    sa.Column('sender_user_id', sa.UUID(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('char_length(body) BETWEEN 1 AND 2000', name=op.f('ck_messages_body_length')),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], name=op.f('fk_messages_conversation_id_conversations'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sender_user_id'], ['users.id'], name=op.f('fk_messages_sender_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_messages')))
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'])

    op.create_table('favorites',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_favorites_user_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_favorites_location_id_locations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'location_id', name=op.f('pk_favorites')))

    op.create_table('reviews',
    sa.Column('booking_id', sa.UUID(), nullable=False),
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('rating', sa.SmallInteger(), nullable=False),
    sa.Column('comment', sa.String(length=1000), nullable=True),
    sa.Column('status', _enum('published', 'hidden', name='review_status'), nullable=False),
    sa.Column('partner_reply', sa.String(length=1000), nullable=True),
    sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('rating BETWEEN 1 AND 5', name=op.f('ck_reviews_rating_range')),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_reviews_booking_id_bookings')),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_reviews_location_id_locations')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_reviews_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reviews')),
    sa.UniqueConstraint('booking_id', name=op.f('uq_reviews_booking_id')))
    op.create_index(op.f('ix_reviews_location_id'), 'reviews', ['location_id'])
    op.create_index(op.f('ix_reviews_user_id'), 'reviews', ['user_id'])

    op.create_table('push_devices',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token', sa.String(length=512), nullable=False),
    sa.Column('platform', _enum('android', 'ios', 'web', name='push_platform'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_push_devices_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_push_devices')),
    sa.UniqueConstraint('token', name='uq_push_devices_token'))
    op.create_index(op.f('ix_push_devices_user_id'), 'push_devices', ['user_id'])

    op.add_column('bookings', sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('bookings', 'reminder_sent_at')
    op.drop_table('push_devices')
    op.drop_table('reviews')
    op.drop_table('favorites')
    op.drop_table('messages')
    op.drop_table('conversations')
