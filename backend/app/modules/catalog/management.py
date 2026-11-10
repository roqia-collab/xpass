"""Gestion de l'établissement par le commerçant (maquettes 18 et 21).

Règles :
- seul le responsable (`merchant_owner`) modifie le catalogue ; le personnel peut bloquer des plages ;
- toute modification d'une prestation crée une NOUVELLE version : les réservations existantes gardent
  le prix, la durée et la politique d'annulation de la version qu'elles ont réservée ;
- le mode de réservation d'une prestation ne change pas après sa création ;
- une ressource avec des réservations à venir ne peut pas être désactivée ;
- les changements d'horaires n'annulent jamais de réservation : les réservations concernées sont signalées.
"""
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.modules.booking.models import ACTIVE_STATUSES, Booking, ExternalBlock, ResourceOccupancy
from app.modules.catalog.models import (
    Location,
    Merchant,
    Offer,
    OfferResource,
    OfferVersion,
    OpeningHours,
    Resource,
    ScheduleException,
)
from app.modules.platform.service import emit

OWNER = ("merchant_owner",)
STAFF = ("merchant_owner", "merchant_staff")


class ManageError(Exception):
    def __init__(self, code: str, message: str, status: int = 409, extra: dict | None = None):
        super().__init__(message)
        self.code, self.message, self.status, self.extra = code, message, status, extra or {}


def load_location(db: Session, principal, location_id: uuid.UUID, roles: tuple[str, ...]) -> Location:
    location = db.scalar(
        select(Location)
        .options(
            selectinload(Location.merchant).selectinload(Merchant.market),
            selectinload(Location.offers).selectinload(Offer.current_version),
            selectinload(Location.offers).selectinload(Offer.resources),
            selectinload(Location.resources),
            selectinload(Location.opening_hours),
            selectinload(Location.exceptions),
        )
        .where(Location.id == location_id)
    )
    if location is None or location.merchant_id not in principal.scope_ids("merchant", roles):
        allowed = location is not None and location.merchant_id in principal.scope_ids("merchant", STAFF)
        raise ManageError(
            "forbidden",
            "Seul le responsable de l'établissement peut effectuer cette modification." if allowed
            else "Vous n'avez pas accès à cet établissement.",
            403,
        )
    return location


def _tz(location: Location) -> ZoneInfo:
    return ZoneInfo(location.merchant.market.timezone)


def _future_bookings(db: Session, *, now: datetime, **where) -> int:
    stmt = select(func.count()).select_from(Booking).where(Booking.status.in_(ACTIVE_STATUSES), Booking.starts_at > now)
    for column, value in where.items():
        stmt = stmt.where(getattr(Booking, column) == value)
    return int(db.scalar(stmt))


# ---------------------------------------------------------------- établissement


def update_location(db: Session, location: Location, *, description: str, access_info: str | None,
                    meeting_point: str | None, wheelchair_accessible: bool, review_url: str | None) -> None:
    if review_url and not review_url.startswith("https://"):
        raise ManageError("invalid_review_url", "Le lien d'avis doit commencer par https://.", 422)
    location.description = description.strip()
    location.access_info = (access_info or "").strip() or None
    location.meeting_point = (meeting_point or "").strip() or None
    location.wheelchair_accessible = wheelchair_accessible
    location.review_url = (review_url or "").strip() or None
    emit(db, "location", location.id, "location.updated", {"location_id": str(location.id)})


# ---------------------------------------------------------------- prestations


@dataclass
class OfferInput:
    title: str
    summary: str
    duration_min: int
    price_credits: int
    participants_min: int
    participants_max: int
    capacity: int | None
    free_cancellation_hours: int
    resource_ids: list[uuid.UUID]


def _check_offer(location: Location, booking_mode: str, data: OfferInput) -> list[Resource]:
    if data.duration_min % 15 != 0:
        raise ManageError("invalid_duration", "La durée doit être un multiple de 15 minutes.", 422)
    resources = {r.id: r for r in location.resources}
    chosen = []
    for rid in data.resource_ids:
        r = resources.get(rid)
        if r is None:
            raise ManageError("invalid_resource", "Cette ressource n'appartient pas à l'établissement.", 422)
        if not r.is_active:
            raise ManageError("inactive_resource", f"{r.name} est désactivé(e).", 422)
        chosen.append(r)
    if booking_mode == "resource_slot" and not chosen:
        raise ManageError("resource_required", "Choisissez au moins un professionnel ou une ressource.", 422)
    if booking_mode in ("capacity_session", "open_access") and not data.capacity:
        raise ManageError("capacity_required", "Indiquez la capacité de la séance.", 422)
    if booking_mode == "resource_slot" and data.capacity:
        raise ManageError("capacity_not_allowed", "La capacité ne s'applique pas aux rendez-vous individuels.", 422)
    return chosen


def _new_version(db: Session, offer: Offer, data: OfferInput, previous: OfferVersion | None) -> OfferVersion:
    number = (db.scalar(select(func.max(OfferVersion.version)).where(OfferVersion.offer_id == offer.id)) or 0) + 1
    version = OfferVersion(
        offer_id=offer.id,
        version=number,
        title=data.title.strip(),
        summary=data.summary.strip(),
        includes=previous.includes if previous else None,
        language=previous.language if previous else None,
        duration_min=data.duration_min,
        price_credits=data.price_credits,
        participants_min=data.participants_min,
        participants_max=data.participants_max,
        capacity=data.capacity,
        free_cancellation_hours=data.free_cancellation_hours,
        external_ticket_note=previous.external_ticket_note if previous else None,
    )
    db.add(version)
    db.flush()
    offer.current_version_id = version.id
    return version


def _set_resources(db: Session, offer: Offer, resources: list[Resource]) -> None:
    db.execute(delete(OfferResource).where(OfferResource.offer_id == offer.id))
    for r in resources:
        db.add(OfferResource(offer_id=offer.id, resource_id=r.id))


def create_offer(db: Session, location: Location, *, booking_mode: str, data: OfferInput, publish: bool) -> Offer:
    if booking_mode == "external_ticket":
        raise ManageError("unsupported_mode", "Les billets externes sont configurés par l'équipe XPASS.", 422)
    resources = _check_offer(location, booking_mode, data)
    offer = Offer(
        location_id=location.id, booking_mode=booking_mode, is_active=publish,
        sort_order=max((o.sort_order for o in location.offers), default=0) + 1,
    )
    db.add(offer)
    db.flush()
    _new_version(db, offer, data, None)
    _set_resources(db, offer, resources)
    db.flush()
    emit(db, "offer", offer.id, "offer.created", {"location_id": str(location.id)})
    return offer


def update_offer(db: Session, location: Location, offer_id: uuid.UUID, data: OfferInput) -> OfferVersion:
    offer = next((o for o in location.offers if o.id == offer_id), None)
    if offer is None:
        raise ManageError("offer_not_found", "Prestation introuvable.", 404)
    # Verrou : deux enregistrements simultanés ne peuvent pas créer le même numéro de version.
    db.scalar(select(Offer.id).where(Offer.id == offer.id).with_for_update())
    resources = _check_offer(location, offer.booking_mode, data)
    version = _new_version(db, offer, data, offer.current_version)
    _set_resources(db, offer, resources)
    db.flush()
    emit(db, "offer", offer.id, "offer.version_published", {"version": version.version})
    return version


def set_offer_active(db: Session, location: Location, offer_id: uuid.UUID, active: bool) -> Offer:
    offer = next((o for o in location.offers if o.id == offer_id), None)
    if offer is None:
        raise ManageError("offer_not_found", "Prestation introuvable.", 404)
    if active and offer.booking_mode == "resource_slot" and not any(r.is_active for r in offer.resources):
        raise ManageError("resource_required", "Associez un professionnel actif avant de publier.", 422)
    # Dépublier n'annule pas les réservations existantes : elles restent honorées.
    offer.is_active = active
    db.flush()
    return offer


# ---------------------------------------------------------------- équipe et ressources


def create_resource(db: Session, location: Location, *, kind: str, name: str, role_label: str) -> Resource:
    resource = Resource(
        location_id=location.id, kind=kind, name=name.strip(), role_label=role_label.strip(), is_active=True,
        sort_order=max((r.sort_order for r in location.resources), default=0) + 1,
    )
    db.add(resource)
    db.flush()
    return resource


def update_resource(db: Session, location: Location, resource_id: uuid.UUID, *, name: str, role_label: str,
                    active: bool, now: datetime | None = None) -> Resource:
    now = now or datetime.now(UTC)
    resource = next((r for r in location.resources if r.id == resource_id), None)
    if resource is None:
        raise ManageError("resource_not_found", "Ressource introuvable.", 404)
    if resource.is_active and not active:
        pending = _future_bookings(db, now=now, resource_id=resource.id)
        if pending:
            raise ManageError(
                "has_future_bookings",
                f"{resource.name} a {pending} réservation(s) à venir : elles doivent être honorées ou annulées avant.",
                409, {"bookings": pending},
            )
        # Une prestation qui n'aurait plus aucune ressource active est retirée de la vente.
        for offer in location.offers:
            if offer.booking_mode == "resource_slot" and offer.is_active and all(
                r.id == resource.id or not r.is_active for r in offer.resources
            ):
                offer.is_active = False
    resource.name, resource.role_label, resource.is_active = name.strip(), role_label.strip(), active
    db.flush()
    return resource


# ---------------------------------------------------------------- horaires et fermetures


def _bookings_outside(db: Session, location: Location, now: datetime, horizon_days: int = 60) -> int:
    """Réservations à venir qui tombent hors des horaires (après le changement)."""
    from app.modules.catalog import availability

    tz = _tz(location)
    rows = db.execute(
        select(Booking.starts_at, Booking.ends_at).where(
            Booking.location_id == location.id, Booking.status.in_(ACTIVE_STATUSES),
            Booking.starts_at > now, Booking.starts_at < now + timedelta(days=horizon_days),
        )
    ).all()
    db.refresh(location, ["opening_hours", "exceptions"])
    outside = 0
    for start, end in rows:
        local_start, local_end = start.astimezone(tz), end.astimezone(tz)
        windows = availability.day_windows(local_start.date(), location.opening_hours, location.exceptions)
        if not any(w.opens_at <= local_start.time() and local_end.time() <= w.closes_at for w in windows):
            outside += 1
    return outside


def replace_hours(db: Session, location: Location, hours: list[tuple[int, time, time]],
                  now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    by_day: dict[int, list[tuple[time, time]]] = {}
    for weekday, opens, closes in hours:
        if not 0 <= weekday <= 6 or closes <= opens:
            raise ManageError("invalid_hours", "Chaque plage doit finir après son début.", 422)
        by_day.setdefault(weekday, []).append((opens, closes))
    for windows in by_day.values():
        windows.sort()
        if any(a[1] > b[0] for a, b in zip(windows, windows[1:])):
            raise ManageError("overlapping_hours", "Deux plages se chevauchent le même jour.", 422)
    db.execute(delete(OpeningHours).where(OpeningHours.location_id == location.id))
    for weekday, opens, closes in hours:
        db.add(OpeningHours(location_id=location.id, weekday=weekday, opens_at=opens, closes_at=closes))
    db.flush()
    return _bookings_outside(db, location, now)


def add_exception(db: Session, location: Location, *, day: date, is_closed: bool, opens_at: time | None,
                  closes_at: time | None, reason: str | None, now: datetime | None = None) -> tuple[ScheduleException, int]:
    now = now or datetime.now(UTC)
    if day < now.astimezone(_tz(location)).date():
        raise ManageError("past_day", "Cette date est passée.", 422)
    if not is_closed and (opens_at is None or closes_at is None or closes_at <= opens_at):
        raise ManageError("invalid_hours", "Indiquez des horaires valides pour cette journée.", 422)
    if db.scalar(select(ScheduleException.id).where(ScheduleException.location_id == location.id,
                                                    ScheduleException.day == day)):
        raise ManageError("duplicate_day", "Une exception existe déjà pour cette date.", 409)
    exc = ScheduleException(location_id=location.id, day=day, is_closed=is_closed,
                            opens_at=None if is_closed else opens_at, closes_at=None if is_closed else closes_at,
                            reason=(reason or "").strip() or None)
    db.add(exc)
    db.flush()
    return exc, _bookings_outside(db, location, now)


def delete_exception(db: Session, location: Location, exception_id: uuid.UUID) -> None:
    deleted = db.execute(delete(ScheduleException).where(
        ScheduleException.id == exception_id, ScheduleException.location_id == location.id))
    if deleted.rowcount == 0:
        raise ManageError("exception_not_found", "Fermeture introuvable.", 404)


# ---------------------------------------------------------------- blocages


def remove_block(db: Session, location: Location, block_id: uuid.UUID) -> None:
    block = db.scalar(select(ExternalBlock).where(ExternalBlock.id == block_id, ExternalBlock.location_id == location.id,
                                                  ExternalBlock.is_active.is_(True)).with_for_update())
    if block is None:
        raise ManageError("block_not_found", "Blocage introuvable.", 404)
    block.is_active = False
    db.execute(update(ResourceOccupancy).where(ResourceOccupancy.external_block_id == block.id)
               .values(is_active=False))
    db.flush()
