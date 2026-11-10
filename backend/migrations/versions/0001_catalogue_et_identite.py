"""Catalogue et identité (lot 1)

Revision ID: 0001
Revises: 
Create Date: 2026-10-31 19:07:07.426400
"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    for ext in ("postgis", "btree_gist", "unaccent", "pgcrypto"):
        op.execute(f"CREATE EXTENSION IF NOT EXISTS {ext}")
    op.create_table('categories',
    sa.Column('slug', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('eyebrow', sa.String(length=80), nullable=False),
    sa.Column('headline', sa.String(length=80), nullable=False),
    sa.Column('tagline', sa.String(length=200), nullable=False),
    sa.Column('cta_label', sa.String(length=60), nullable=False),
    sa.Column('tile_image_key', sa.String(length=255), nullable=True),
    sa.Column('hero_image_key', sa.String(length=255), nullable=True),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_categories')),
    sa.UniqueConstraint('slug', name=op.f('uq_categories_slug'))
    )
    op.create_table('markets',
    sa.Column('code', sa.String(length=16), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('country_code', sa.String(length=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('timezone', sa.String(length=64), nullable=False),
    sa.Column('default_locale', sa.String(length=10), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_markets')),
    sa.UniqueConstraint('code', name=op.f('uq_markets_code'))
    )
    op.create_table('users',
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('display_name', sa.String(length=120), nullable=False),
    sa.Column('oidc_subject', sa.String(length=255), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email')),
    sa.UniqueConstraint('oidc_subject', name=op.f('uq_users_oidc_subject'))
    )
    op.create_geospatial_table('cities',
    sa.Column('market_id', sa.UUID(), nullable=False),
    sa.Column('slug', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('center', Geography(geometry_type='POINT', srid=4326, spatial_index=False, from_text='ST_GeogFromText', name='geography', nullable=False), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], name=op.f('fk_cities_market_id_markets')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cities')),
    sa.UniqueConstraint('market_id', 'slug', name=op.f('uq_cities_market_id'))
    )
    op.create_geospatial_index('idx_cities_center', 'cities', ['center'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_table('memberships',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('scope_type', sa.Enum('platform', 'merchant', 'organization', name='scope_type', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('scope_id', sa.Uuid(), nullable=True),
    sa.Column('role', sa.Enum('platform_admin', 'platform_operator', 'merchant_owner', 'merchant_staff', 'hr_admin', 'hr_viewer', name='role', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(role IN ('platform_admin','platform_operator') AND scope_type = 'platform') OR (role IN ('merchant_owner','merchant_staff') AND scope_type = 'merchant') OR (role IN ('hr_admin','hr_viewer') AND scope_type = 'organization')", name=op.f('ck_memberships_role_matches_scope')),
    sa.CheckConstraint("(scope_type = 'platform' AND scope_id IS NULL) OR (scope_type <> 'platform' AND scope_id IS NOT NULL)", name=op.f('ck_memberships_scope_id_shape')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_memberships_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_memberships')),
    sa.UniqueConstraint('user_id', 'scope_type', 'scope_id', 'role', name='uq_memberships_scope_role')
    )
    op.create_index('ix_memberships_scope', 'memberships', ['scope_type', 'scope_id'], unique=False)
    op.create_index(op.f('ix_memberships_user_id'), 'memberships', ['user_id'], unique=False)
    op.create_table('merchants',
    sa.Column('market_id', sa.UUID(), nullable=False),
    sa.Column('legal_name', sa.String(length=160), nullable=False),
    sa.Column('display_name', sa.String(length=120), nullable=False),
    sa.Column('commercial_status', sa.Enum('draft', 'pending_review', 'documents_missing', 'approved', 'suspended', name='commercial_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('psp_status', sa.Enum('not_started', 'pending', 'verified', 'rejected', name='psp_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('city_label', sa.String(length=80), nullable=False),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], name=op.f('fk_merchants_market_id_markets')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_merchants'))
    )
    op.create_table('organizations',
    sa.Column('market_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('sector_label', sa.String(length=120), nullable=True),
    sa.Column('city_label', sa.String(length=80), nullable=True),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['market_id'], ['markets.id'], name=op.f('fk_organizations_market_id_markets')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_organizations'))
    )
    op.create_table('subcategories',
    sa.Column('category_id', sa.UUID(), nullable=False),
    sa.Column('slug', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('icon', sa.String(length=32), nullable=False),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_subcategories_category_id_categories')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_subcategories')),
    sa.UniqueConstraint('category_id', 'slug', name=op.f('uq_subcategories_category_id'))
    )
    op.create_geospatial_table('locations',
    sa.Column('merchant_id', sa.UUID(), nullable=False),
    sa.Column('city_id', sa.UUID(), nullable=False),
    sa.Column('subcategory_id', sa.UUID(), nullable=False),
    sa.Column('slug', sa.String(length=120), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('kind_label', sa.String(length=80), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('address_line', sa.String(length=200), nullable=False),
    sa.Column('postal_code', sa.String(length=12), nullable=False),
    sa.Column('district_label', sa.String(length=40), nullable=False),
    sa.Column('geo', Geography(geometry_type='POINT', srid=4326, spatial_index=False, from_text='ST_GeogFromText', name='geography', nullable=False), nullable=False),
    sa.Column('access_info', sa.String(length=240), nullable=True),
    sa.Column('meeting_point', sa.String(length=240), nullable=True),
    sa.Column('wheelchair_accessible', sa.Boolean(), nullable=False),
    sa.Column('review_url', sa.String(length=500), nullable=True),
    sa.Column('cover_image_key', sa.String(length=255), nullable=True),
    sa.Column('status', sa.Enum('draft', 'published', 'hidden', name='location_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('is_demo', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], name=op.f('fk_locations_city_id_cities')),
    sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], name=op.f('fk_locations_merchant_id_merchants')),
    sa.ForeignKeyConstraint(['subcategory_id'], ['subcategories.id'], name=op.f('fk_locations_subcategory_id_subcategories')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_locations')),
    sa.UniqueConstraint('slug', name=op.f('uq_locations_slug'))
    )
    op.create_geospatial_index('idx_locations_geo', 'locations', ['geo'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_index(op.f('ix_locations_city_id'), 'locations', ['city_id'], unique=False)
    op.create_index(op.f('ix_locations_merchant_id'), 'locations', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_locations_subcategory_id'), 'locations', ['subcategory_id'], unique=False)
    op.create_table('offers',
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('booking_mode', sa.Enum('resource_slot', 'capacity_session', 'open_access', 'external_ticket', name='booking_mode', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('image_key', sa.String(length=255), nullable=True),
    sa.Column('current_version_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_offers_location_id_locations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_offers'))
    )
    op.create_index(op.f('ix_offers_location_id'), 'offers', ['location_id'], unique=False)
    op.create_table('opening_hours',
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('weekday', sa.SmallInteger(), nullable=False),
    sa.Column('opens_at', sa.Time(), nullable=False),
    sa.Column('closes_at', sa.Time(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('closes_at > opens_at', name=op.f('ck_opening_hours_hours_order')),
    sa.CheckConstraint('weekday BETWEEN 0 AND 6', name=op.f('ck_opening_hours_weekday_range')),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_opening_hours_location_id_locations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_opening_hours'))
    )
    op.create_index(op.f('ix_opening_hours_location_id'), 'opening_hours', ['location_id'], unique=False)
    op.create_table('resources',
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Enum('staff', 'equipment', 'room', name='resource_kind', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('role_label', sa.String(length=80), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_resources_location_id_locations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resources'))
    )
    op.create_index(op.f('ix_resources_location_id'), 'resources', ['location_id'], unique=False)
    op.create_table('schedule_exceptions',
    sa.Column('location_id', sa.UUID(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('is_closed', sa.Boolean(), nullable=False),
    sa.Column('opens_at', sa.Time(), nullable=True),
    sa.Column('closes_at', sa.Time(), nullable=True),
    sa.Column('reason', sa.String(length=160), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint('(is_closed AND opens_at IS NULL AND closes_at IS NULL) OR (NOT is_closed AND opens_at IS NOT NULL AND closes_at > opens_at)', name=op.f('ck_schedule_exceptions_exception_shape')),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_schedule_exceptions_location_id_locations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_schedule_exceptions'))
    )
    op.create_index(op.f('ix_schedule_exceptions_location_id'), 'schedule_exceptions', ['location_id'], unique=False)
    op.create_table('offer_resources',
    sa.Column('offer_id', sa.UUID(), nullable=False),
    sa.Column('resource_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], name=op.f('fk_offer_resources_offer_id_offers'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], name=op.f('fk_offer_resources_resource_id_resources'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('offer_id', 'resource_id', name=op.f('pk_offer_resources'))
    )
    op.create_table('offer_versions',
    sa.Column('offer_id', sa.UUID(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=120), nullable=False),
    sa.Column('summary', sa.String(length=240), nullable=False),
    sa.Column('includes', sa.String(length=240), nullable=True),
    sa.Column('language', sa.String(length=40), nullable=True),
    sa.Column('duration_min', sa.Integer(), nullable=False),
    sa.Column('price_credits', sa.Integer(), nullable=False),
    sa.Column('participants_min', sa.SmallInteger(), nullable=False),
    sa.Column('participants_max', sa.SmallInteger(), nullable=False),
    sa.Column('capacity', sa.Integer(), nullable=True),
    sa.Column('free_cancellation_hours', sa.Integer(), nullable=False),
    sa.Column('external_ticket_note', sa.String(length=160), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('capacity IS NULL OR capacity > 0', name=op.f('ck_offer_versions_capacity_positive')),
    sa.CheckConstraint('duration_min > 0', name=op.f('ck_offer_versions_duration_positive')),
    sa.CheckConstraint('free_cancellation_hours >= 0', name=op.f('ck_offer_versions_cancellation_nonneg')),
    sa.CheckConstraint('participants_max >= participants_min AND participants_min >= 1', name=op.f('ck_offer_versions_participants')),
    sa.CheckConstraint('price_credits > 0', name=op.f('ck_offer_versions_price_positive')),
    sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], name=op.f('fk_offer_versions_offer_id_offers'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_offer_versions')),
    sa.UniqueConstraint('offer_id', 'version', name=op.f('uq_offer_versions_offer_id'))
    )
    op.create_index(op.f('ix_offer_versions_offer_id'), 'offer_versions', ['offer_id'], unique=False)
    # Référence circulaire offres <-> versions : ajoutée après la création des deux tables.
    op.create_foreign_key('fk_offers_current_version', 'offers', 'offer_versions', ['current_version_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_offers_current_version', 'offers', type_='foreignkey')
    op.drop_index(op.f('ix_offer_versions_offer_id'), table_name='offer_versions')
    op.drop_table('offer_versions')
    op.drop_table('offer_resources')
    op.drop_index(op.f('ix_schedule_exceptions_location_id'), table_name='schedule_exceptions')
    op.drop_table('schedule_exceptions')
    op.drop_index(op.f('ix_resources_location_id'), table_name='resources')
    op.drop_table('resources')
    op.drop_index(op.f('ix_opening_hours_location_id'), table_name='opening_hours')
    op.drop_table('opening_hours')
    op.drop_index(op.f('ix_offers_location_id'), table_name='offers')
    op.drop_table('offers')
    op.drop_index(op.f('ix_locations_subcategory_id'), table_name='locations')
    op.drop_index(op.f('ix_locations_merchant_id'), table_name='locations')
    op.drop_index(op.f('ix_locations_city_id'), table_name='locations')
    op.drop_geospatial_index('idx_locations_geo', table_name='locations', postgresql_using='gist', column_name='geo')
    op.drop_geospatial_table('locations')
    op.drop_table('subcategories')
    op.drop_table('organizations')
    op.drop_table('merchants')
    op.drop_index(op.f('ix_memberships_user_id'), table_name='memberships')
    op.drop_index('ix_memberships_scope', table_name='memberships')
    op.drop_table('memberships')
    op.drop_geospatial_index('idx_cities_center', table_name='cities', postgresql_using='gist', column_name='center')
    op.drop_geospatial_table('cities')
    op.drop_table('users')
    op.drop_table('markets')
    op.drop_table('categories')
