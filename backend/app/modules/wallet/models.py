"""Portefeuille de crédits : lots, journal append-only équilibré et projections.

Comptes du journal (par lot) :
    issuance     contrepartie d'une émission (attribution de crédits)
    available    crédits utilisables
    reserved     crédits bloqués par une réservation
    consumed     crédits consommés (prestation, annulation tardive)
    expired      crédits périmés

Chaque écriture (journal) a des lignes dont la somme vaut 0 (vérifié par un trigger
différé). Les projections `credit_lot_balances` sont mises à jour dans la même
transaction et peuvent être reconstruites à partir des lignes.
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin


def _enum(*values: str, name: str) -> Enum:
    return Enum(*values, name=name, native_enum=False, create_constraint=True, length=24)


CREDIT_SOURCE = ("personal", "employer", "promotional")
JOURNAL_KIND = ("grant", "reserve", "release", "capture", "expire", "adjustment")
ACCOUNT = ("issuance", "available", "reserved", "consumed", "expired")

# Ordre de consommation : promotionnel, puis employeur, puis personnel ; à source égale, expiration la plus proche.
SOURCE_PRIORITY = {"promotional": 0, "employer": 1, "personal": 2}


class Wallet(IdMixin, Base):
    __tablename__ = "wallets"
    __table_args__ = (UniqueConstraint("user_id", "market_id"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("markets.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lots: Mapped[list["CreditLot"]] = relationship(back_populates="wallet", order_by="CreditLot.created_at")


class CreditLot(IdMixin, Base):
    __tablename__ = "credit_lots"
    __table_args__ = (
        CheckConstraint("granted_credits > 0", name="granted_positive"),
        # Une seule allocation de crédits par facture payée, quel que soit le nombre de webhooks reçus.
        Index(
            "uq_credit_lots_invoice",
            "origin_ref",
            unique=True,
            postgresql_where=text("origin_type = 'subscription_invoice'"),
        ),
        # Restitution de litige : une seule par (litige, lot d'origine).
        Index(
            "uq_credit_lots_dispute_refund",
            "origin_ref",
            unique=True,
            postgresql_where=text("origin_type = 'dispute_refund'"),
        ),
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    source: Mapped[str] = mapped_column(_enum(*CREDIT_SOURCE, name="credit_source"))
    # Origine métier : demo_grant, employer_allocation (lot 6), purchase (lot 4), refund, ...
    origin_type: Mapped[str] = mapped_column(String(40))
    origin_ref: Mapped[str | None] = mapped_column(String(120))
    label: Mapped[str] = mapped_column(String(120))
    granted_credits: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # NULL = tous les univers ; sinon slugs de catégories éligibles.
    eligible_categories: Mapped[list[str] | None] = mapped_column(ARRAY(String(32)))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    wallet: Mapped[Wallet] = relationship(back_populates="lots")
    balance: Mapped["CreditLotBalance"] = relationship(uselist=False, lazy="joined")


class CreditLotBalance(Base):
    """Projection transactionnelle du solde d'un lot (reconstructible depuis le journal)."""

    __tablename__ = "credit_lot_balances"
    __table_args__ = (
        CheckConstraint("available >= 0", name="available_nonneg"),
        CheckConstraint("reserved >= 0", name="reserved_nonneg"),
        CheckConstraint("consumed >= 0", name="consumed_nonneg"),
        CheckConstraint("expired >= 0", name="expired_nonneg"),
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credit_lots.id", ondelete="RESTRICT"), primary_key=True
    )
    available: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    consumed: Mapped[int] = mapped_column(Integer, default=0)
    expired: Mapped[int] = mapped_column(Integer, default=0)


class CreditJournal(IdMixin, Base):
    __tablename__ = "credit_journals"
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    kind: Mapped[str] = mapped_column(_enum(*JOURNAL_KIND, name="journal_kind"))
    booking_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bookings.id"), index=True)
    # Contre-écriture : pointe vers l'écriture corrigée (jamais de modification).
    reverses_journal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("credit_journals.id"))
    memo: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    lines: Mapped[list["CreditJournalLine"]] = relationship(back_populates="journal")


class CreditJournalLine(IdMixin, Base):
    __tablename__ = "credit_journal_lines"
    __table_args__ = (CheckConstraint("amount <> 0", name="amount_nonzero"),)
    journal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("credit_journals.id"), index=True)
    lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("credit_lots.id"), index=True)
    account: Mapped[str] = mapped_column(_enum(*ACCOUNT, name="credit_account"))
    amount: Mapped[int] = mapped_column(Integer)

    journal: Mapped[CreditJournal] = relationship(back_populates="lines")
