import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSTZRANGE, ExcludeConstraint, Range
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin

BOOKING_STATUS = ("held", "confirmed", "cancelled", "expired", "redeemed", "no_show")
ACTIVE_STATUSES = ("held", "confirmed")
HOLD_MINUTES = 5


class Booking(IdMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("party_size >= 1", name="party_positive"),
        CheckConstraint("total_credits = price_credits_per_person * party_size", name="total_matches"),
        CheckConstraint("ends_at > starts_at", name="ends_after_start"),
        CheckConstraint("status <> 'held' OR hold_expires_at IS NOT NULL", name="held_has_expiry"),
        # Même effet métier impossible deux fois (même avec une autre clé d'idempotence).
        Index(
            "uq_bookings_active_user_offer_start",
            "user_id",
            "offer_id",
            "starts_at",
            unique=True,
            postgresql_where=text("status IN ('held', 'confirmed')"),
        ),
        Index("ix_bookings_held_expiry", "hold_expires_at", postgresql_where=text("status = 'held'")),
        Index("ix_bookings_location_start", "location_id", "starts_at"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"))
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"))
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id"))
    # Version de prix et de politique conservée telle qu'au moment de la réservation.
    offer_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offer_versions.id"))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resources.id"))
    inventory_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("session_inventories.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    party_size: Mapped[int] = mapped_column(SmallInteger)
    price_credits_per_person: Mapped[int] = mapped_column(Integer)
    # Ajustements appliqués au prix de base au moment de la réserve : peak, demand, last_minute.
    price_adjustments: Mapped[list[str] | None] = mapped_column(ARRAY(String(16)))
    total_credits: Mapped[int] = mapped_column(Integer)
    # Crédits rendus au client à l'annulation (tous si gratuite, la moitié si tardive).
    refunded_credits: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(
        Enum(*BOOKING_STATUS, name="booking_status", native_enum=False, create_constraint=True, length=16)
    )
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    free_cancellation_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    late_cancellation: Mapped[bool] = mapped_column(Boolean, default=False)
    cancel_reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Rappel « la veille » envoyé (notification ou e-mail) : jamais deux fois.
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    location = relationship("Location")
    offer_version = relationship("OfferVersion")
    resource = relationship("Resource")
    user = relationship("User")


class SessionInventory(IdMixin, Base):
    """Inventaire collectif d'une séance (capacité partagée), verrouillé par mise à jour conditionnelle."""

    __tablename__ = "session_inventories"
    __table_args__ = (
        UniqueConstraint("offer_id", "starts_at"),
        CheckConstraint("capacity > 0", name="capacity_positive"),
        CheckConstraint("reserved >= 0 AND reserved <= capacity", name="reserved_within_capacity"),
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    capacity: Mapped[int] = mapped_column(Integer)
    reserved: Mapped[int] = mapped_column(Integer, default=0)


class ExternalBlock(IdMixin, Base):
    """Plage indisponible déclarée par le partenaire (réservation hors XPASS, pause, absence)."""

    __tablename__ = "external_blocks"
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), index=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id"))
    during: Mapped[Range[datetime]] = mapped_column(TSTZRANGE)
    reason: Mapped[str] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResourceOccupancy(IdMixin, Base):
    """Occupation d'une ressource exclusive : une réservation OU un blocage externe, jamais les deux.

    La contrainte d'exclusion GiST interdit deux occupations actives qui se chevauchent
    sur la même ressource, y compris sous concurrence.
    """

    __tablename__ = "resource_occupancies"
    __table_args__ = (
        CheckConstraint("num_nonnulls(booking_id, external_block_id) = 1", name="one_owner"),
        ExcludeConstraint(
            ("resource_id", "="),
            ("during", "&&"),
            where=text("is_active"),
            using="gist",
            name="ex_resource_occupancies_no_overlap",
        ),
        UniqueConstraint("booking_id"),
        UniqueConstraint("external_block_id"),
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id"))
    booking_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bookings.id"))
    external_block_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("external_blocks.id"))
    during: Mapped[Range[datetime]] = mapped_column(TSTZRANGE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
