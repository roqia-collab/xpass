"""Ville ouverte et conditions écrites du contrat employeur.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-11 09:40:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cities", sa.Column("opened", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.execute("UPDATE cities SET opened = true WHERE slug = 'paris'")
    op.add_column("employer_contracts", sa.Column("term_months", sa.Integer(), server_default="12", nullable=False))
    op.add_column(
        "employer_contracts",
        sa.Column(
            "covered_cities",
            postgresql.ARRAY(sa.String(80)),
            server_default=sa.text("ARRAY['Paris']::varchar[]"),
            nullable=False,
        ),
    )
    op.add_column("employer_contracts", sa.Column("commission_bps", sa.Integer(), server_default="1000", nullable=False))
    op.add_column(
        "employer_contracts",
        sa.Column("free_cancellation_hours", sa.Integer(), server_default="24", nullable=False),
    )
    op.create_check_constraint(op.f("ck_employer_contracts_term_range"), "employer_contracts", "term_months BETWEEN 1 AND 36")
    op.create_check_constraint(
        op.f("ck_employer_contracts_commission_range"), "employer_contracts", "commission_bps BETWEEN 0 AND 10000"
    )
    op.create_check_constraint(
        op.f("ck_employer_contracts_cancellation_range"),
        "employer_contracts",
        "free_cancellation_hours BETWEEN 0 AND 168",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_employer_contracts_cancellation_range"), "employer_contracts", type_="check")
    op.drop_constraint(op.f("ck_employer_contracts_commission_range"), "employer_contracts", type_="check")
    op.drop_constraint(op.f("ck_employer_contracts_term_range"), "employer_contracts", type_="check")
    op.drop_column("employer_contracts", "free_cancellation_hours")
    op.drop_column("employer_contracts", "commission_bps")
    op.drop_column("employer_contracts", "covered_cities")
    op.drop_column("employer_contracts", "term_months")
    op.drop_column("cities", "opened")
