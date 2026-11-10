import uuid
from datetime import date, datetime, time

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin


def _enum(*values: str, name: str) -> Enum:
    # Stocké en texte + CHECK : plus simple à faire évoluer qu'un type ENUM natif.
    return Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


COMMERCIAL_STATUS = ("draft", "pending_review", "documents_missing", "approved", "suspended")
PSP_STATUS = ("not_started", "pending", "verified", "rejected")
LOCATION_STATUS = ("draft", "published", "hidden")
BOOKING_MODE = ("resource_slot", "capacity_session", "open_access", "external_ticket")
RESOURCE_KIND = ("staff", "equipment", "room")


class Market(IdMixin, Base):
    __tablename__ = "markets"
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    country_code: Mapped[str] = mapped_column(String(2))
    currency: Mapped[str] = mapped_column(String(3))
    timezone: Mapped[str] = mapped_column(String(64))
    default_locale: Mapped[str] = mapped_column(String(10), default="fr-FR")


class City(IdMixin, Base):
    __tablename__ = "cities"
    __table_args__ = (UniqueConstraint("market_id", "slug"),)
    market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("markets.id"))
    slug: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(80))
    center = mapped_column(Geography("POINT", srid=4326), nullable=False)

    market: Mapped[Market] = relationship()


class Category(IdMixin, Base):
    __tablename__ = "categories"
    slug: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    eyebrow: Mapped[str] = mapped_column(String(80))
    headline: Mapped[str] = mapped_column(String(80))
    tagline: Mapped[str] = mapped_column(String(200))
    cta_label: Mapped[str] = mapped_column(String(60))
    tile_image_key: Mapped[str | None] = mapped_column(String(255))
    hero_image_key: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)

    subcategories: Mapped[list["Subcategory"]] = relationship(
        back_populates="category", order_by="Subcategory.sort_order"
    )


class Subcategory(IdMixin, Base):
    __tablename__ = "subcategories"
    __table_args__ = (UniqueConstraint("category_id", "slug"),)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"))
    slug: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(64))
    icon: Mapped[str] = mapped_column(String(32))
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)

    category: Mapped[Category] = relationship(back_populates="subcategories")


class Merchant(IdMixin, TimestampMixin, Base):
    __tablename__ = "merchants"
    market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("markets.id"))
    # Service RH qui a créé ce commerçant. Vide pour une candidature directe, validée par l'admin.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    legal_name: Mapped[str] = mapped_column(String(160))
    display_name: Mapped[str] = mapped_column(String(120))
    # Validation commerciale et statut du prestataire de paiement sont indépendants.
    commercial_status: Mapped[str] = mapped_column(_enum(*COMMERCIAL_STATUS, name="commercial_status"))
    psp_status: Mapped[str] = mapped_column(_enum(*PSP_STATUS, name="psp_status"))
    # Compte connecté chez le prestataire (destinataire des versements), créé à l'intégration PSP.
    psp_account_id: Mapped[str | None] = mapped_column(String(120))
    city_label: Mapped[str] = mapped_column(String(80))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    # Inscription (lot réseau) : SIRET vérifié dans l'annuaire public, résultat conservé pour l'équipe XPASS.
    siret: Mapped[str | None] = mapped_column(String(14))
    siren: Mapped[str | None] = mapped_column(String(9))
    contact_phone: Mapped[str | None] = mapped_column(String(30))
    company_check: Mapped[dict | None] = mapped_column(JSONB)
    company_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    market: Mapped[Market] = relationship()
    locations: Mapped[list["Location"]] = relationship(back_populates="merchant")


class Location(IdMixin, TimestampMixin, Base):
    __tablename__ = "locations"
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    city_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cities.id"), index=True)
    subcategory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subcategories.id"), index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    kind_label: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    address_line: Mapped[str] = mapped_column(String(200))
    postal_code: Mapped[str] = mapped_column(String(12))
    district_label: Mapped[str] = mapped_column(String(40))
    geo = mapped_column(Geography("POINT", srid=4326), nullable=False)
    access_info: Mapped[str | None] = mapped_column(String(240))
    meeting_point: Mapped[str | None] = mapped_column(String(240))
    wheelchair_accessible: Mapped[bool] = mapped_column(Boolean, default=False)
    review_url: Mapped[str | None] = mapped_column(String(500))
    cover_image_key: Mapped[str | None] = mapped_column(String(255))
    # Adresse retenue par la Base Adresse Nationale et score de confiance (0 à 1).
    geocode_label: Mapped[str | None] = mapped_column(String(200))
    geocode_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(_enum(*LOCATION_STATUS, name="location_status"))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    merchant: Mapped[Merchant] = relationship(back_populates="locations")
    city: Mapped[City] = relationship()
    subcategory: Mapped[Subcategory] = relationship()
    offers: Mapped[list["Offer"]] = relationship(back_populates="location", order_by="Offer.sort_order")
    opening_hours: Mapped[list["OpeningHours"]] = relationship(
        order_by="(OpeningHours.weekday, OpeningHours.opens_at)"
    )
    exceptions: Mapped[list["ScheduleException"]] = relationship()
    resources: Mapped[list["Resource"]] = relationship(order_by="Resource.sort_order")


CHANGE_STATUS = ("pending", "approved", "rejected")


class LocationChangeRequest(IdMixin, TimestampMixin, Base):
    """Demande de modification (nom, activité, adresse) par le commerçant, appliquée après validation XPASS."""

    __tablename__ = "location_change_requests"
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), index=True)
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    # Valeurs proposées ; pour une adresse : lignes géocodées (Base Adresse Nationale) prêtes à appliquer.
    changes: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(_enum(*CHANGE_STATUS, name="change_status"), default="pending")
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OpeningHours(IdMixin, Base):
    __tablename__ = "opening_hours"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint("closes_at > opens_at", name="hours_order"),
    )
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[int] = mapped_column(SmallInteger)  # 0 = lundi
    opens_at: Mapped[time] = mapped_column(Time)
    closes_at: Mapped[time] = mapped_column(Time)


class ScheduleException(IdMixin, Base):
    __tablename__ = "schedule_exceptions"
    __table_args__ = (
        CheckConstraint(
            "(is_closed AND opens_at IS NULL AND closes_at IS NULL) OR "
            "(NOT is_closed AND opens_at IS NOT NULL AND closes_at > opens_at)",
            name="exception_shape",
        ),
    )
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date)
    is_closed: Mapped[bool] = mapped_column(Boolean)
    opens_at: Mapped[time | None] = mapped_column(Time)
    closes_at: Mapped[time | None] = mapped_column(Time)
    reason: Mapped[str | None] = mapped_column(String(160))


class Resource(IdMixin, Base):
    __tablename__ = "resources"
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(_enum(*RESOURCE_KIND, name="resource_kind"))
    name: Mapped[str] = mapped_column(String(80))
    role_label: Mapped[str] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)


class Offer(IdMixin, TimestampMixin, Base):
    __tablename__ = "offers"
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), index=True)
    booking_mode: Mapped[str] = mapped_column(_enum(*BOOKING_MODE, name="booking_mode"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)
    image_key: Mapped[str | None] = mapped_column(String(255))
    # Version publiée courante. Les réservations référenceront la version, jamais l'offre seule.
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("offer_versions.id", use_alter=True, name="fk_offers_current_version")
    )

    location: Mapped[Location] = relationship(back_populates="offers")
    current_version: Mapped["OfferVersion | None"] = relationship(foreign_keys=[current_version_id])
    resources: Mapped[list[Resource]] = relationship(secondary="offer_resources", order_by="Resource.sort_order")


class OfferVersion(IdMixin, TimestampMixin, Base):
    __tablename__ = "offer_versions"
    __table_args__ = (
        UniqueConstraint("offer_id", "version"),
        CheckConstraint("price_credits > 0", name="price_positive"),
        CheckConstraint("duration_min > 0", name="duration_positive"),
        CheckConstraint("participants_max >= participants_min AND participants_min >= 1", name="participants"),
        CheckConstraint("capacity IS NULL OR capacity > 0", name="capacity_positive"),
        CheckConstraint("free_cancellation_hours >= 0", name="cancellation_nonneg"),
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(String(240), default="")
    includes: Mapped[str | None] = mapped_column(String(240))
    language: Mapped[str | None] = mapped_column(String(40))
    duration_min: Mapped[int] = mapped_column(Integer)
    # Prix en CRÉDITS (entier), par participant. Aucune notion monétaire ici.
    price_credits: Mapped[int] = mapped_column(Integer)
    participants_min: Mapped[int] = mapped_column(SmallInteger, default=1)
    participants_max: Mapped[int] = mapped_column(SmallInteger, default=1)
    capacity: Mapped[int | None] = mapped_column(Integer)
    free_cancellation_hours: Mapped[int] = mapped_column(Integer, default=24)
    external_ticket_note: Mapped[str | None] = mapped_column(String(160))


class OfferResource(Base):
    __tablename__ = "offer_resources"
    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), primary_key=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True
    )
