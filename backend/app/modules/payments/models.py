"""Abonnements, factures, webhooks du prestataire de paiement et journal monétaire.

Règles :
- l'argent est en unités mineures entières (centimes) avec sa devise ; jamais mélangé aux crédits ;
- les crédits d'un abonnement ne sont attribués que sur un webhook signé « facture payée »,
  jamais sur un retour navigateur ;
- chaque webhook est persisté avant traitement et dédupliqué par (prestataire, identifiant d'événement).
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin


def _enum(*values: str, name: str, length: int = 24) -> Enum:
    return Enum(*values, name=name, native_enum=False, create_constraint=True, length=length)


class SubscriptionPlan(IdMixin, Base):
    __tablename__ = "subscription_plans"
    __table_args__ = (
        Index("uq_subscription_plans_market_code", "market_id", "code", unique=True),
        CheckConstraint("price_minor > 0 AND credits_per_period > 0", name="positive"),
    )
    market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("markets.id"))
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(80))
    price_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    credits_per_period: Mapped[int] = mapped_column(Integer)
    # NULL = crédits sans expiration ; sinon validité en jours à partir de l'attribution.
    credit_validity_days: Mapped[int | None] = mapped_column(Integer)
    # Identifiant du tarif chez le prestataire (ex. price_... chez Stripe).
    psp_price_id: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


SUBSCRIPTION_STATUS = ("incomplete", "active", "past_due", "canceled", "expired")
LIVE_SUBSCRIPTION = ("incomplete", "active", "past_due")


class Subscription(IdMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        # Un seul abonnement vivant par client et par marché.
        Index(
            "uq_subscriptions_live",
            "user_id",
            "market_id",
            unique=True,
            postgresql_where=text("status IN ('incomplete','active','past_due')"),
        ),
        Index("uq_subscriptions_psp", "provider", "psp_subscription_id", unique=True),
        Index("uq_subscriptions_checkout", "provider", "psp_checkout_id", unique=True),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("markets.id"))
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subscription_plans.id"))
    # Formule choisie pour le prochain renouvellement (appliquée quand la facture correspondante est payée).
    pending_plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subscription_plans.id"))
    provider: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(_enum(*SUBSCRIPTION_STATUS, name="subscription_status"))
    psp_checkout_id: Mapped[str | None] = mapped_column(String(120))
    psp_customer_id: Mapped[str | None] = mapped_column(String(120))
    psp_subscription_id: Mapped[str | None] = mapped_column(String(120))
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    plan: Mapped[SubscriptionPlan] = relationship(foreign_keys=[plan_id])
    pending_plan: Mapped[SubscriptionPlan | None] = relationship(foreign_keys=[pending_plan_id])


INVOICE_STATUS = ("paid", "refunded", "void")


class Invoice(IdMixin, Base):
    """Facture payée côté prestataire (seule une facture payée crée des crédits)."""

    __tablename__ = "invoices"
    __table_args__ = (
        Index("uq_invoices_psp", "provider", "psp_invoice_id", unique=True),
        CheckConstraint("amount_minor >= 0", name="amount_non_negative"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subscriptions.id"), index=True)
    provider: Mapped[str] = mapped_column(String(16))
    psp_invoice_id: Mapped[str] = mapped_column(String(120))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    credits: Mapped[int] = mapped_column(Integer)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(_enum(*INVOICE_STATUS, name="invoice_status"))
    # Faux en bac à sable / mode test du prestataire : aucun argent réel.
    livemode: Mapped[bool] = mapped_column(Boolean)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaymentWebhookEvent(IdMixin, Base):
    """Journal durable des webhooks reçus (signature vérifiée AVANT insertion)."""

    __tablename__ = "payment_webhook_events"
    __table_args__ = (
        Index("uq_payment_webhook_events", "provider", "event_id", unique=True),
        Index("ix_payment_webhook_events_pending", "received_at", postgresql_where=text("processed_at IS NULL")),
    )
    provider: Mapped[str] = mapped_column(String(16))
    event_id: Mapped[str] = mapped_column(String(120))
    event_type: Mapped[str] = mapped_column(String(80))
    livemode: Mapped[bool] = mapped_column(Boolean)
    payload: Mapped[dict] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # applied | ignored
    outcome: Mapped[str | None] = mapped_column(String(16))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)


MONEY_ACCOUNTS = (
    "psp_cash",  # trésorerie détenue chez le prestataire
    "customer_deferred",  # encaissements clients en contrepartie de crédits
    "partner_expense",  # coût des prestations dues aux partenaires
    "partner_payable",  # dettes envers les partenaires
    "commission_revenue",  # commission XPASS
    "bank_cash",  # virements reçus sur le compte bancaire XPASS (factures entreprises)
    "employer_prepaid",  # financements entreprises non encore alloués aux salariés
)


class MoneyJournal(IdMixin, Base):
    """Écriture monétaire en ajout seul ; équilibre par devise vérifié en fin de transaction."""

    __tablename__ = "money_journals"
    kind: Mapped[str] = mapped_column(String(32))
    memo: Mapped[str] = mapped_column(String(200))
    ref_type: Mapped[str] = mapped_column(String(32))
    ref_id: Mapped[uuid.UUID] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    lines: Mapped[list["MoneyJournalLine"]] = relationship()


class MoneyJournalLine(IdMixin, Base):
    __tablename__ = "money_journal_lines"
    __table_args__ = (CheckConstraint("amount_minor <> 0", name="non_zero"),)
    journal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("money_journals.id"), index=True)
    account: Mapped[str] = mapped_column(_enum(*MONEY_ACCOUNTS, name="money_account", length=32))
    # Compte de tiers éventuel (marchand pour partner_payable).
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("merchants.id"), index=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
