"""Relation client ↔ établissement : messagerie par réservation, favoris, avis notés, appareils pour les notifications."""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin

SENDER_KIND = ("customer", "partner", "system")
REVIEW_STATUS = ("published", "hidden")
PLATFORM = ("android", "ios", "web")


def _enum(*values: str, name: str) -> Enum:
    return Enum(*values, name=name, native_enum=False, create_constraint=True, length=16)


class Conversation(IdMixin, Base):
    """Une conversation par réservation : le client et l'équipe de l'établissement, rien d'autre."""

    __tablename__ = "conversations"
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id"), unique=True)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    customer_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    partner_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Message(IdMixin, Base):
    """Message en ajout seul (jamais modifié ni supprimé par l'application)."""

    __tablename__ = "messages"
    __table_args__ = (CheckConstraint("char_length(body) BETWEEN 1 AND 2000", name="body_length"),)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender_kind: Mapped[str] = mapped_column(_enum(*SENDER_KIND, name="sender_kind"))
    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Favorite(Base):
    __tablename__ = "favorites"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Review(IdMixin, Base):
    """Avis noté, un par réservation consommée ; l'établissement peut répondre, XPASS peut masquer (motif tracé)."""

    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id"), unique=True)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(SmallInteger)
    comment: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(_enum(*REVIEW_STATUS, name="review_status"), default="published")
    partner_reply: Mapped[str | None] = mapped_column(String(1000))
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PushDevice(IdMixin, Base):
    """Jeton de notification d'un téléphone (Firebase Cloud Messaging). Supprimé à la déconnexion."""

    __tablename__ = "push_devices"
    __table_args__ = (UniqueConstraint("token", name="uq_push_devices_token"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(512))
    platform: Mapped[str] = mapped_column(_enum(*PLATFORM, name="push_platform"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
