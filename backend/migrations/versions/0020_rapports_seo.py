"""Rapports SEO externes, recommandations, balises par page et historique.

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-17 10:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seo_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("report_id", sa.String(length=100), nullable=False),
        sa.Column("site_url", sa.String(length=300), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("report_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("markdown_report", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="new"),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('new', 'in_review', 'validated', 'applied', 'rejected')",
                           name="ck_seo_reports_seo_report_status"),
        sa.CheckConstraint("overall_score IS NULL OR overall_score BETWEEN 0 AND 100", name="ck_seo_reports_score"),
        sa.PrimaryKeyConstraint("id", name="pk_seo_reports"),
        sa.UniqueConstraint("report_id", name="uq_seo_reports_report_id"),
    )
    op.create_index("ix_seo_reports_report_created", "seo_reports", ["report_created_at"])
    op.create_index("ix_seo_reports_status", "seo_reports", ["status"])

    op.create_table(
        "seo_recommendations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("report_pk", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("page_url", sa.String(length=500), nullable=False),
        sa.Column("page_path", sa.String(length=300), nullable=True),
        sa.Column("issue", sa.Text(), nullable=False),
        sa.Column("current_value", sa.Text(), nullable=True),
        sa.Column("suggested_value", sa.Text(), nullable=True),
        sa.Column("edited_value", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("sender_status", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="new"),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.UUID(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_by", sa.UUID(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('new', 'validated', 'rejected', 'applied', 'reverted')",
                           name="ck_seo_recommendations_seo_reco_status"),
        sa.ForeignKeyConstraint(["report_pk"], ["seo_reports.id"], ondelete="CASCADE",
                                name="fk_seo_recommendations_report_pk_seo_reports"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], name="fk_seo_recommendations_decided_by_users"),
        sa.ForeignKeyConstraint(["applied_by"], ["users.id"], name="fk_seo_recommendations_applied_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_seo_recommendations"),
        sa.UniqueConstraint("report_pk", "external_id", name="uq_seo_recommendations_report_external"),
    )
    op.create_index("ix_seo_recommendations_report_pk", "seo_recommendations", ["report_pk"])
    op.create_index("ix_seo_recommendations_status", "seo_recommendations", ["status"])

    op.create_table(
        "seo_page_overrides",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("page_path", sa.String(length=300), nullable=False),
        sa.Column("field", sa.String(length=40), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name="fk_seo_page_overrides_updated_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_seo_page_overrides"),
        sa.UniqueConstraint("page_path", "field", name="uq_seo_page_overrides_page_field"),
    )
    op.create_index("ix_seo_page_overrides_page_path", "seo_page_overrides", ["page_path"])

    op.create_table(
        "seo_changes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("recommendation_id", sa.UUID(), nullable=True),
        sa.Column("page_path", sa.String(length=300), nullable=False),
        sa.Column("field", sa.String(length=40), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=False),
        sa.Column("applied_by", sa.UUID(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reverted_by", sa.UUID(), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["seo_recommendations.id"],
                                name="fk_seo_changes_recommendation_id_seo_recommendations"),
        sa.ForeignKeyConstraint(["applied_by"], ["users.id"], name="fk_seo_changes_applied_by_users"),
        sa.ForeignKeyConstraint(["reverted_by"], ["users.id"], name="fk_seo_changes_reverted_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_seo_changes"),
    )
    op.create_index("ix_seo_changes_recommendation_id", "seo_changes", ["recommendation_id"])
    op.create_index("ix_seo_changes_page_field", "seo_changes", ["page_path", "field"])


def downgrade() -> None:
    op.drop_table("seo_changes")
    op.drop_table("seo_page_overrides")
    op.drop_table("seo_recommendations")
    op.drop_table("seo_reports")
