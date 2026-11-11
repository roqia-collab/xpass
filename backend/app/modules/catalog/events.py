"""Événements d'un établissement : créés par l'admin ou par le RH qui possède le commerçant."""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.catalog.models import Category, City, Location, Merchant, Offer, OfferVersion, Subcategory, VenueEvent
from app.modules.identity.models import Organization
from app.modules.ops.service import audit


class EventError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        self.code, self.message, self.status = code, message, status


EVENT_OFFER_SORT = 90


def ensure_offer(db: Session, event: VenueEvent, location: Location) -> Offer:
    """Une séance réservable, cachée de la liste des prestations du lieu."""
    minutes = max(15, int((event.ends_at - event.starts_at).total_seconds() // 60))
    if event.offer_id is None:
        offer = Offer(
            location_id=location.id, booking_mode="capacity_session", sort_order=EVENT_OFFER_SORT,
            image_key=event.cover_image_key, is_active=event.status == "published",
        )
        db.add(offer)
        db.flush()
        version = OfferVersion(
            offer_id=offer.id, version=1, title=event.title[:120], summary=(event.summary or "")[:240],
            duration_min=minutes, price_credits=event.price_credits, participants_min=1, participants_max=1,
            capacity=event.capacity or 20, free_cancellation_hours=24,
        )
        db.add(version)
        db.flush()
        offer.current_version_id = version.id
        event.offer_id = offer.id
        db.flush()
        return offer
    offer = db.get(Offer, event.offer_id)
    if offer is None or offer.current_version_id is None:
        event.offer_id = None
        return ensure_offer(db, event, location)
    offer.is_active = event.status == "published"
    offer.image_key = event.cover_image_key
    offer.sort_order = EVENT_OFFER_SORT
    version = db.get(OfferVersion, offer.current_version_id)
    if version is not None:
        version.title = event.title[:120]
        version.summary = (event.summary or "")[:240]
        version.duration_min = minutes
        version.price_credits = event.price_credits
        version.capacity = event.capacity or 20
    db.flush()
    return offer


def backfill_offers(db: Session) -> int:
    rows = db.scalars(select(VenueEvent).where(VenueEvent.offer_id.is_(None))).all()
    for event in rows:
        location = db.get(Location, event.location_id)
        if location is not None:
            ensure_offer(db, event, location)
    return len(rows)


def _check_times(starts_at: datetime, ends_at: datetime) -> tuple[datetime, datetime]:
    if starts_at.tzinfo is None or ends_at.tzinfo is None:
        raise EventError("timezone_required", "Indiquez une date avec son fuseau horaire.")
    start, end = starts_at.astimezone(UTC), ends_at.astimezone(UTC)
    if end <= start:
        raise EventError("invalid_span", "La fin doit être après le début.")
    if end - start > timedelta(hours=48):
        raise EventError("too_long", "Un événement dure au plus 48 heures.")
    return start, end


def _venue_for(db: Session, location_id: uuid.UUID, organization_id: uuid.UUID | None) -> tuple[Location, uuid.UUID]:
    location = db.scalar(
        select(Location)
        .join(Merchant, Merchant.id == Location.merchant_id)
        .where(Location.id == location_id)
        .options(selectinload(Location.merchant))
    )
    if location is None:
        raise EventError("location_not_found", "Établissement introuvable.", 404)
    org_id = location.merchant.organization_id
    if org_id is None:
        raise EventError("no_rh", "Ce commerçant n'est pas rattaché à un service RH.", 409)
    if organization_id is not None and org_id != organization_id:
        raise EventError("wrong_org", "Cet établissement n'appartient pas à votre service RH.", 403)
    return location, org_id


def create_event(
    db: Session, *, location_id: uuid.UUID, title: str, summary: str, starts_at: datetime, ends_at: datetime,
    price_credits: int, by: uuid.UUID, actor_kind: str, organization_id: uuid.UUID | None = None,
) -> VenueEvent:
    if not 1 <= price_credits <= 500:
        raise EventError("invalid_price", "Le prix doit être compris entre 1 et 500 crédits.")
    title = title.strip()
    if len(title) < 2:
        raise EventError("invalid_title", "Indiquez le titre de l'événement.")
    start, end = _check_times(starts_at, ends_at)
    location, org_id = _venue_for(db, location_id, organization_id)
    event = VenueEvent(
        organization_id=org_id, location_id=location.id, title=title[:120], summary=(summary or "").strip()[:500],
        starts_at=start, ends_at=end, price_credits=price_credits, status="published", created_by=by,
        cover_image_key=location.cover_image_key,
    )
    db.add(event)
    db.flush()
    ensure_offer(db, event, location)
    audit(
        db, actor_kind=actor_kind, actor_user_id=by, action="event.created", object_type="venue_event",
        object_id=event.id, object_label=event.title,
        details={"location": location.name, "organization_id": str(org_id)},
    )
    return event


def update_event(
    db: Session, event_id: uuid.UUID, *, title: str, summary: str, starts_at: datetime, ends_at: datetime,
    price_credits: int, by: uuid.UUID, actor_kind: str, organization_id: uuid.UUID | None = None,
) -> VenueEvent:
    event = _owned(db, event_id, organization_id)
    if not 1 <= price_credits <= 500:
        raise EventError("invalid_price", "Le prix doit être compris entre 1 et 500 crédits.")
    start, end = _check_times(starts_at, ends_at)
    event.title = title.strip()[:120]
    event.summary = (summary or "").strip()[:500]
    event.starts_at, event.ends_at, event.price_credits = start, end, price_credits
    ensure_offer(db, event, event.location)
    audit(
        db, actor_kind=actor_kind, actor_user_id=by, action="event.updated", object_type="venue_event",
        object_id=event.id, object_label=event.title,
    )
    return event


def set_event_visible(db: Session, event_id: uuid.UUID, *, published: bool, by: uuid.UUID, actor_kind: str,
                      organization_id: uuid.UUID | None = None) -> VenueEvent:
    event = _owned(db, event_id, organization_id)
    event.status = "published" if published else "hidden"
    ensure_offer(db, event, event.location)
    audit(
        db, actor_kind=actor_kind, actor_user_id=by,
        action="event.published" if published else "event.hidden",
        object_type="venue_event", object_id=event.id, object_label=event.title,
    )
    return event


def set_cover(db: Session, event_id: uuid.UUID, key: str, organization_id: uuid.UUID | None = None) -> VenueEvent:
    event = _owned(db, event_id, organization_id)
    event.cover_image_key = key
    return event


def _owned(db: Session, event_id: uuid.UUID, organization_id: uuid.UUID | None) -> VenueEvent:
    event = db.get(VenueEvent, event_id)
    if event is None or (organization_id is not None and event.organization_id != organization_id):
        raise EventError("event_not_found", "Événement introuvable.", 404)
    return event


def _row(event: VenueEvent, location: Location, org_name: str, category_slug: str) -> dict:
    return {
        "id": event.id,
        "title": event.title,
        "summary": event.summary,
        "starts_at": event.starts_at,
        "ends_at": event.ends_at,
        "price_credits": event.price_credits,
        "cover_image_key": event.cover_image_key or location.cover_image_key,
        "status": event.status,
        "location_id": location.id,
        "location_slug": location.slug,
        "location_name": location.name,
        "address_line": location.address_line,
        "district_label": location.district_label,
        "organization_name": org_name,
        "category_slug": category_slug,
    }


def list_managed(db: Session, organization_id: uuid.UUID | None = None) -> list[dict]:
    stmt = (
        select(VenueEvent, Location, Organization.name, Category.slug)
        .join(Location, Location.id == VenueEvent.location_id)
        .join(Organization, Organization.id == VenueEvent.organization_id)
        .join(Subcategory, Subcategory.id == Location.subcategory_id)
        .join(Category, Category.id == Subcategory.category_id)
        .order_by(VenueEvent.starts_at.desc())
    )
    if organization_id is not None:
        stmt = stmt.where(VenueEvent.organization_id == organization_id)
    return [_row(event, loc, name, slug) for event, loc, name, slug in db.execute(stmt.limit(200)).all()]


def _public_stmt():
    now = datetime.now(UTC)
    return (
        select(VenueEvent, Location, Organization.name, Category.slug)
        .join(Location, Location.id == VenueEvent.location_id)
        .join(Merchant, Merchant.id == Location.merchant_id)
        .join(City, City.id == Location.city_id)
        .join(Organization, Organization.id == VenueEvent.organization_id)
        .join(Subcategory, Subcategory.id == Location.subcategory_id)
        .join(Category, Category.id == Subcategory.category_id)
        .where(
            VenueEvent.status == "published",
            VenueEvent.ends_at >= now,
            Location.status == "published",
            Merchant.commercial_status == "approved",
            City.opened.is_(True),
            Location.is_demo.is_(False),
            Merchant.is_demo.is_(False),
        )
    )


def get_public(db: Session, event_id: uuid.UUID) -> dict | None:
    found = db.execute(_public_stmt().where(VenueEvent.id == event_id)).first()
    if found is None:
        return None
    event, loc, name, slug = found
    return _row(event, loc, name, slug)


def list_public(db: Session, *, city: str | None = None, location_slug: str | None = None, limit: int = 30) -> list[dict]:
    stmt = _public_stmt().order_by(VenueEvent.starts_at)
    if city:
        stmt = stmt.where(City.slug == city)
    if location_slug:
        stmt = stmt.where(Location.slug == location_slug)
    return [_row(event, loc, name, slug) for event, loc, name, slug in db.execute(stmt.limit(limit)).all()]
