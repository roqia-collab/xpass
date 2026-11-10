"""Assemblage des réponses du catalogue (cartes, fiches) à partir des modèles."""
from datetime import UTC, datetime

from app.modules.catalog import availability
from app.modules.catalog.models import Location, Offer
from app.modules.catalog.schemas import (
    LocationCardOut,
    LocationDetailOut,
    NextSlotOut,
    OfferOut,
    OpeningHoursOut,
    TeamMemberOut,
)

SLOT_MODES = ("resource_slot", "capacity_session", "open_access")


def _active_offers(location: Location) -> list[Offer]:
    return [o for o in location.offers if o.is_active and o.current_version is not None]


def offer_out(location: Location, offer: Offer, now: datetime) -> OfferOut:
    v = offer.current_version
    assert v is not None
    next_slot = None
    if offer.booking_mode in SLOT_MODES:
        starts_at = availability.next_indicative_slot(
            weekly=location.opening_hours,
            exceptions=location.exceptions,
            duration_min=v.duration_min,
            timezone=location.merchant.market.timezone,
            now=now,
        )
        if starts_at is not None:
            staff = next((r for r in offer.resources if r.is_active and r.kind == "staff"), None)
            next_slot = NextSlotOut(
                starts_at=starts_at,
                local_start=starts_at.replace(tzinfo=None).isoformat(timespec="seconds"),
                resource_name=staff.name if staff else None,
            )
    return OfferOut(
        id=offer.id,
        version_id=v.id,
        title=v.title,
        summary=v.summary,
        includes=v.includes,
        language=v.language,
        duration_min=v.duration_min,
        price_credits=v.price_credits,
        booking_mode=offer.booking_mode,
        participants_min=v.participants_min,
        participants_max=v.participants_max,
        capacity=v.capacity,
        free_cancellation_hours=v.free_cancellation_hours,
        external_ticket_note=v.external_ticket_note,
        image_key=offer.image_key,
        next_slot=next_slot,
    )


def _card_fields(location: Location, distance_m: float | None, featured: OfferOut | None) -> dict:
    sub = location.subcategory
    return dict(
        id=location.id,
        slug=location.slug,
        name=location.name,
        kind_label=location.kind_label,
        category_slug=sub.category.slug,
        category_name=sub.category.name,
        subcategory_slug=sub.slug,
        subcategory_name=sub.name,
        city_slug=location.city.slug,
        district_label=location.district_label,
        cover_image_key=location.cover_image_key,
        distance_m=round(distance_m) if distance_m is not None else None,
        wheelchair_accessible=location.wheelchair_accessible,
        meeting_point=location.meeting_point,
        featured_offer=featured,
        is_demo=location.is_demo,
    )


def location_card(location: Location, distance_m: float | None, now: datetime | None = None, *,
                  lat: float | None = None, lng: float | None = None) -> LocationCardOut:
    now = now or datetime.now(UTC)
    offers = _active_offers(location)
    featured = offer_out(location, offers[0], now) if offers else None
    return LocationCardOut(**_card_fields(location, distance_m, featured), latitude=lat, longitude=lng)


def location_detail(
    location: Location, lat: float, lng: float, now: datetime | None = None, *, include_inactive: bool = False
) -> LocationDetailOut:
    now = now or datetime.now(UTC)
    offers = [o for o in location.offers if o.current_version is not None] if include_inactive else _active_offers(
        location
    )
    offer_list = [offer_out(location, o, now) for o in offers]
    return LocationDetailOut(
        **_card_fields(location, None, offer_list[0] if offer_list else None),
        merchant_name=location.merchant.display_name,
        description=location.description,
        address_line=location.address_line,
        postal_code=location.postal_code,
        city_name=location.city.name,
        latitude=lat,
        longitude=lng,
        access_info=location.access_info,
        review_url=location.review_url,
        hours_summary=availability.hours_summary(location.opening_hours),
        opening_hours=[OpeningHoursOut.model_validate(h) for h in location.opening_hours],
        offers=offer_list,
        team=[
            TeamMemberOut(name=r.name, role_label=r.role_label, kind=r.kind)
            for r in location.resources
            if r.is_active
        ],
        status=location.status,
        merchant_status=location.merchant.commercial_status,
    )
