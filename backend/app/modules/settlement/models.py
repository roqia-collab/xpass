"""Valorisation des dettes partenaires, ajustements et versements hebdomadaires."""
import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin


class SettlementTerms(IdMixin, Base):
    """Barème d'un marché : valeur d'un crédit reversée au partenaire et commission XPASS.

    Les dettes sont valorisées avec le barème en vigueur à la date de la prestation (jamais rétroactif).
    """

    __tablename__ = "settlement_terms"
    __table_args__ = (
        Index("uq_settlement_terms_market_from", "market_id", "effective_from", unique=True),
        CheckConstraint("gross_minor_per_credit > 0", name="rate_positive"),
        CheckConstraint("commission_bps BETWEEN 0 AND 10000", name="commission_range"),
    )
    market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("markets.id"))
    currency: Mapped[str] = mapped_column(String(3))
    gross_minor_per_credit: Mapped[int] = mapped_column(Integer)
    # Points de base : 1000 = 10 %.
    commission_bps: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


PAYOUT_STATUS = ("pending", "in_transit", "paid", "to_reconcile", "failed")


class PartnerPayout(IdMixin, Base):
    """Versement d'une période fermée (semaine du lundi au dimanche, fuseau du marché)."""

    __tablename__ = "partner_payouts"
    __table_args__ = (
        Index("uq_partner_payouts_period", "merchant_id", "period_start", "currency", unique=True),
        CheckConstraint("net_minor = gross_minor - commission_minor + adjustments_minor", name="net_formula"),
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    gross_minor: Mapped[int] = mapped_column(BigInteger)
    commission_minor: Mapped[int] = mapped_column(BigInteger)
    adjustments_minor: Mapped[int] = mapped_column(BigInteger)
    net_minor: Mapped[int] = mapped_column(BigInteger)
    visits: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Enum(*PAYOUT_STATUS, name="payout_status", native_enum=False, create_constraint=True, length=16))
    provider: Mapped[str | None] = mapped_column(String(16))
    psp_transfer_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    # Montant effectivement confirmé par le prestataire (rapprochement).
    confirmed_minor: Mapped[int | None] = mapped_column(BigInteger)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PartnerAdjustment(IdMixin, Base):
    """Avoir ou correction (montant signé). Création par l'administration au lot 7."""

    __tablename__ = "partner_adjustments"
    __table_args__ = (
        Index("uq_partner_adjustments_reference", "reference", unique=True),
        CheckConstraint("amount_minor <> 0", name="non_zero"),
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    reference: Mapped[str] = mapped_column(String(20))
    label: Mapped[str] = mapped_column(String(160))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    payout_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("partner_payouts.id"), index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
