import uuid
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from app.modules.booking.models import Booking
from app.modules.booking.pricing import late_cancellation_refund


class HoldIn(BaseModel):
    offer_id: uuid.UUID
    starts_at: datetime
    party_size: int = Field(1, ge=1, le=20)
    resource_id: uuid.UUID | None = None
    # Prix par personne affiché au client : s'il a changé entre-temps, la réserve est refusée (409 price_changed).
    expected_price_credits: int | None = Field(None, ge=1)


class FundingOut(BaseModel):
    source: str
    credits: int


class BookingLocationOut(BaseModel):
    slug: str
    name: str
    kind_label: str
    district_label: str
    address: str
    category_slug: str
    category_name: str
    cover_image_key: str | None


class BookingOut(BaseModel):
    id: uuid.UUID
    status: str
    location: BookingLocationOut
    offer_id: uuid.UUID
    offer_title: str
    duration_min: int
    resource_name: str | None
    starts_at: datetime
    # Heures murales dans le fuseau du marché, à afficher sans conversion.
    local_start: str
    timezone: str
    party_size: int
    price_credits_per_person: int
    # peak (heure de pointe), demand (forte demande), last_minute (dernière minute)
    price_adjustments: list[str] = []
    total_credits: int
    funding: list[FundingOut]
    hold_expires_at: datetime | None
    hold_seconds_remaining: int | None
    free_cancellation_until: datetime
    local_free_cancellation_until: str
    late_cancellation: bool
    # Crédits rendus si l'annulation intervient après le délai gratuit (la moitié), et crédits effectivement rendus.
    late_cancellation_refund_credits: int = 0
    refunded_credits: int = 0
    created_at: datetime
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    redeemed_at: datetime | None = None
    receipt_reference: str | None = None


class BookingListOut(BaseModel):
    items: list[BookingOut]
    counts: dict[str, int]


class SlotSchema(BaseModel):
    starts_at: datetime
    local_time: str
    available: bool
    remaining: int | None
    free_resource_ids: list[uuid.UUID]
    price_credits: int
    price_adjustments: list[str]


class DaySchema(BaseModel):
    date: date
    open: bool


class AvailabilityOut(BaseModel):
    offer_id: uuid.UUID
    offer_title: str
    booking_mode: str
    duration_min: int
    price_credits: int
    participants_min: int
    participants_max: int
    location_slug: str
    location_name: str
    city_name: str
    timezone: str
    date: date
    days: list[DaySchema]
    resources: list[dict]
    slots: list[SlotSchema]


def _local(dt: datetime, tz: str) -> str:
    return dt.astimezone(ZoneInfo(tz)).replace(tzinfo=None).isoformat(timespec="seconds")


def booking_out(
    b: Booking, funding: dict[str, int], now: datetime | None = None, receipt_reference: str | None = None
) -> BookingOut:
    now = now or datetime.now(UTC)
    loc = b.location
    tz = loc.merchant.market.timezone
    remaining = None
    if b.status == "held" and b.hold_expires_at is not None:
        remaining = max(0, int((b.hold_expires_at - now).total_seconds()))
    order = ["employer", "promotional", "personal"]
    return BookingOut(
        id=b.id,
        status=b.status,
        location=BookingLocationOut(
            slug=loc.slug,
            name=loc.name,
            kind_label=loc.kind_label,
            district_label=loc.district_label,
            address=f"{loc.address_line}, {loc.postal_code} {loc.city.name}",
            category_slug=loc.subcategory.category.slug,
            category_name=loc.subcategory.category.name,
            cover_image_key=loc.cover_image_key,
        ),
        offer_id=b.offer_id,
        offer_title=b.offer_version.title,
        duration_min=b.offer_version.duration_min,
        resource_name=b.resource.name if b.resource else None,
        starts_at=b.starts_at,
        local_start=_local(b.starts_at, tz),
        timezone=tz,
        party_size=b.party_size,
        price_credits_per_person=b.price_credits_per_person,
        price_adjustments=list(b.price_adjustments or []),
        total_credits=b.total_credits,
        funding=[FundingOut(source=s, credits=funding[s]) for s in order if funding.get(s)],
        hold_expires_at=b.hold_expires_at,
        hold_seconds_remaining=remaining,
        free_cancellation_until=b.free_cancellation_until,
        local_free_cancellation_until=_local(b.free_cancellation_until, tz),
        late_cancellation=b.late_cancellation,
        late_cancellation_refund_credits=late_cancellation_refund(b.total_credits),
        refunded_credits=b.refunded_credits or 0,
        created_at=b.created_at,
        confirmed_at=b.confirmed_at,
        cancelled_at=b.cancelled_at,
        redeemed_at=b.redeemed_at,
        receipt_reference=receipt_reference,
    )


class PassOut(BaseModel):
    """QR et code à présenter. Valables `expires_in` secondes ; à redemander ensuite."""

    qr_payload: str
    manual_code: str
    expires_at: datetime
    expires_in: int


class ReceiptOut(BaseModel):
    reference: str
    booking_id: uuid.UUID
    location_name: str
    offer_title: str
    city_name: str
    cover_image_key: str | None
    redeemed_at: datetime
    local_redeemed_at: str
    credits_total: int
    funding: list[FundingOut]
    # Lien neutre vers la fiche d'avis de l'établissement (aucune récompense, aucune publication automatique).
    review_url: str | None
