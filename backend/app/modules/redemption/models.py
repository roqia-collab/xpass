"""QR éphémères, consommations, reçus et dettes partenaires."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin


class QrToken(IdMixin, Base):
    """Jeton opaque : seules les empreintes SHA-256 sont stockées, jamais le jeton ni le code."""

    __tablename__ = "qr_tokens"
    __table_args__ = (
        Index("uq_qr_tokens_token_hash", "token_hash", unique=True),
        # Le code manuel est court : unique parmi les jetons encore actifs d'un même site.
        Index(
            "uq_qr_tokens_active_code",
            "location_id",
            "code_hash",
            unique=True,
            postgresql_where=text("used_at IS NULL AND revoked_at IS NULL"),
        ),
        Index("ix_qr_tokens_booking", "booking_id"),
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id"))
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"))
    token_hash: Mapped[str] = mapped_column(String(64))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Un aperçu prolonge la validité pour la confirmation par le même opérateur (quelques minutes).
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scanned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Redemption(IdMixin, Base):
    """Consommation d'une réservation. L'unicité sur booking_id interdit toute double consommation."""

    __tablename__ = "redemptions"
    __table_args__ = (Index("uq_redemptions_booking", "booking_id", unique=True),)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id"))
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), index=True)
    qr_token_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("qr_tokens.id"))
    method: Mapped[str] = mapped_column(
        Enum("qr", "code", name="redemption_method", native_enum=False, create_constraint=True, length=8)
    )
    validated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    credits: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Receipt(IdMixin, Base):
    __tablename__ = "receipts"
    __table_args__ = (
        Index("uq_receipts_booking", "booking_id", unique=True),
        Index("uq_receipts_reference", "reference", unique=True),
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id"))
    reference: Mapped[str] = mapped_column(String(20))
    credits_total: Mapped[int] = mapped_column(Integer)
    funding: Mapped[dict] = mapped_column(JSONB)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


PAYABLE_KIND = ("redemption", "late_cancellation", "no_show")
PAYABLE_STATUS = ("pending_valuation", "valued", "in_payout", "paid")


class PartnerPayable(IdMixin, Base):
    """Dette d'XPASS envers le partenaire, créée dans la même transaction que la consommation.

    Le montant monétaire (unités mineures + devise) est calculé avec le barème du marché en vigueur à
    `occurred_at` ; sans barème, la dette reste en crédits avec le statut `pending_valuation`.
    """

    __tablename__ = "partner_payables"
    __table_args__ = (
        Index("uq_partner_payables_booking", "booking_id", unique=True),
        CheckConstraint("credits > 0", name="credits_positive"),
        CheckConstraint(
            "(amount_minor IS NULL) = (currency IS NULL) AND (amount_minor IS NULL) = (commission_minor IS NULL)",
            name="money_complete",
        ),
        CheckConstraint("commission_minor IS NULL OR commission_minor BETWEEN 0 AND amount_minor", name="commission_range"),
        Index("ix_partner_payables_unpaid", "merchant_id", "occurred_at", postgresql_where=text("payout_id IS NULL")),
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"))
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id"))
    kind: Mapped[str] = mapped_column(
        Enum(*PAYABLE_KIND, name="payable_kind", native_enum=False, create_constraint=True, length=24)
    )
    credits: Mapped[int] = mapped_column(Integer)
    # Montant brut (avant commission) et commission, en unités mineures ; NULL tant que non valorisé.
    amount_minor: Mapped[int | None] = mapped_column(BigInteger)
    commission_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str | None] = mapped_column(String(3))
    # Date de la prestation (ou de l'annulation tardive) : fixe le barème et la période de versement.
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payout_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("partner_payouts.id"), index=True)
    status: Mapped[str] = mapped_column(
        Enum(*PAYABLE_STATUS, name="payable_status", native_enum=False, create_constraint=True, length=24)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
