"""Administration : journal d'audit (ajout seul) et litiges."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin


class AuditEvent(IdMixin, Base):
    """Trace d'une décision ou d'un événement sensible. Jamais modifiée ni supprimée (trigger)."""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_object", "object_type", "object_id"),
        Index("ix_audit_events_created", "created_at"),
    )
    # operator (équipe XPASS), system, partner, customer, hr
    actor_kind: Mapped[str] = mapped_column(String(16))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(48))
    object_type: Mapped[str] = mapped_column(String(32))
    object_id: Mapped[uuid.UUID] = mapped_column()
    object_label: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


DISPUTE_STATUS = ("open", "in_review", "waiting_customer", "resolved_refund", "resolved_rejected")
OPEN_DISPUTES = ("open", "in_review", "waiting_customer")


class Dispute(IdMixin, Base):
    __tablename__ = "disputes"
    __table_args__ = (
        Index("uq_disputes_reference", "reference", unique=True),
        # Un seul litige ouvert à la fois par réservation.
        Index("uq_disputes_open_booking", "booking_id", unique=True,
              postgresql_where=text("status IN ('open','in_review','waiting_customer')")),
        CheckConstraint("credits_restored IS NULL OR credits_restored > 0", name="credits_positive"),
    )
    reference: Mapped[str] = mapped_column(String(16))
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id"), index=True)
    opened_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Enum(*DISPUTE_STATUS, name="dispute_status", native_enum=False,
                                             create_constraint=True, length=24))
    operator_notes: Mapped[str | None] = mapped_column(Text)
    credits_restored: Mapped[int | None] = mapped_column(Integer)
    partner_adjustment_minor: Mapped[int | None] = mapped_column(BigInteger)
    resolution_reason: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


SUPPORT_CATEGORY = ("booking", "credits", "account", "partner", "other")
SUPPORT_STATUS = ("open", "answered", "closed")


class SupportRequest(IdMixin, Base):
    """Demande d'assistance d'un client (écran 16), traitée par l'équipe XPASS."""

    __tablename__ = "support_requests"
    __table_args__ = (Index("uq_support_requests_reference", "reference", unique=True),)
    reference: Mapped[str] = mapped_column(String(16))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(Enum(*SUPPORT_CATEGORY, name="support_category", native_enum=False,
                                               create_constraint=True, length=16))
    subject: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bookings.id"))
    status: Mapped[str] = mapped_column(Enum(*SUPPORT_STATUS, name="support_status", native_enum=False,
                                             create_constraint=True, length=16))
    reply: Mapped[str | None] = mapped_column(Text)
    replied_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
