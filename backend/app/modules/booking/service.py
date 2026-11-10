"""Disponibilités réelles et cycle de vie des réservations.

    HELD (5 min max, capacité + crédits bloqués) --confirm--> CONFIRMED --(lot 3)--> REDEEMED
      |                                               |
      +--expiration / annulation--> EXPIRED/CANCELLED  +--annulation--> CANCELLED
                                                      |    (gratuite : crédits libérés ;
                                                      |     tardive : moitié rendue, moitié consommée)
                                                      +--non présenté--> NO_SHOW (crédits consommés)

Prix : voir pricing.py (heure de pointe, remplissage, dernière minute), figé à la réserve.

Ordre des verrous (anti-interblocage) : portefeuille -> réservation -> inventaire/occupation -> lots.
"""
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from psycopg.errors import ExclusionViolation
from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import Range, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.modules.booking import pricing
from app.modules.booking.models import (
    ACTIVE_STATUSES,
    HOLD_MINUTES,
    Booking,
    ExternalBlock,
    ResourceOccupancy,
    SessionInventory,
)
from app.modules.catalog import availability
from app.modules.catalog.models import Location, Merchant, Offer, Resource, Subcategory
from app.modules.platform.service import emit
from app.modules.wallet import service as wallet_service

BOOKABLE_MODES = ("resource_slot", "capacity_session", "open_access")
CAPACITY_MODES = ("capacity_session", "open_access")
BOOKING_HORIZON_DAYS = 30


class BookingError(Exception):
    def __init__(self, code: str, message: str, status: int = 409, extra: dict | None = None):
        super().__init__(message)
        self.code, self.message, self.status, self.extra = code, message, status, extra or {}


# ---------------------------------------------------------------- chargement


def load_offer(db: Session, offer_id: uuid.UUID) -> Offer:
    offer = db.scalar(
        select(Offer)
        .options(
            selectinload(Offer.current_version),
            selectinload(Offer.resources),
            selectinload(Offer.location).selectinload(Location.merchant).selectinload(Merchant.market),
            selectinload(Offer.location).selectinload(Location.opening_hours),
            selectinload(Offer.location).selectinload(Location.exceptions),
            selectinload(Offer.location).selectinload(Location.subcategory).selectinload(Subcategory.category),
            selectinload(Offer.location).selectinload(Location.city),
        )
        .where(Offer.id == offer_id)
    )
    if offer is None or not offer.is_active or offer.current_version is None:
        raise BookingError("offer_not_found", "Prestation introuvable.", 404)
    loc = offer.location
    if loc.status != "published" or loc.merchant.commercial_status != "approved":
        raise BookingError("offer_not_found", "Prestation introuvable.", 404)
    return offer


def _bookable_resources(offer: Offer) -> list[Resource]:
    return [r for r in offer.resources if r.is_active and r.kind == "staff"] or [
        r for r in offer.resources if r.is_active
    ]


def _tz(offer: Offer) -> ZoneInfo:
    return ZoneInfo(offer.location.merchant.market.timezone)


# ---------------------------------------------------------------- disponibilités


@dataclass
class SlotOut:
    starts_at: datetime
    local_time: str
    available: bool
    remaining: int | None = None
    free_resource_ids: list[uuid.UUID] = field(default_factory=list)
    price_credits: int = 0
    price_adjustments: list[str] = field(default_factory=list)


def _priced(slot: SlotOut, offer: Offer, tz: ZoneInfo, now: datetime, fill: float) -> SlotOut:
    price = pricing.slot_price(offer.current_version.price_credits, starts_at=slot.starts_at, tz=tz, now=now, fill=fill)
    slot.price_credits, slot.price_adjustments = price.credits, list(price.adjustments)
    return slot


def _slot_grid(offer: Offer, day: date, now: datetime) -> list[datetime]:
    loc = offer.location
    return availability.day_slots(
        day=day,
        weekly=loc.opening_hours,
        exceptions=loc.exceptions,
        duration_min=offer.current_version.duration_min,
        timezone=loc.merchant.market.timezone,
        now=now,
    )


def compute_slots(db: Session, offer: Offer, day: date, now: datetime) -> list[SlotOut]:
    version = offer.current_version
    grid = _slot_grid(offer, day, now)
    if not grid or offer.booking_mode not in BOOKABLE_MODES:
        return []
    duration = timedelta(minutes=version.duration_min)
    tz = _tz(offer)

    if offer.booking_mode in CAPACITY_MODES:
        used = dict(
            db.execute(
                select(SessionInventory.starts_at, SessionInventory.capacity - SessionInventory.reserved).where(
                    SessionInventory.offer_id == offer.id, SessionInventory.starts_at.in_(grid)
                )
            ).all()
        )
        out = []
        capacity = version.capacity or 0
        for s in grid:
            remaining = used.get(s, capacity)
            fill = (capacity - remaining) / capacity if capacity else 0.0
            out.append(_priced(SlotOut(s, s.astimezone(tz).strftime("%H:%M"), remaining > 0, remaining=remaining),
                               offer, tz, now, fill))
        return out

    resources = _bookable_resources(offer)
    ids = [r.id for r in resources]
    day_range = Range(grid[0], grid[-1] + duration)
    busy = db.execute(
        select(ResourceOccupancy.resource_id, ResourceOccupancy.during).where(
            ResourceOccupancy.resource_id.in_(ids),
            ResourceOccupancy.is_active.is_(True),
            ResourceOccupancy.during.overlaps(day_range),
        )
    ).all()
    out = []
    for s in grid:
        e = s + duration
        free = [
            rid for rid in ids
            if not any(b_rid == rid and b.lower < e and s < b.upper for b_rid, b in busy)
        ]
        fill = 1 - len(free) / len(ids) if ids else 0.0
        out.append(_priced(SlotOut(s, s.astimezone(tz).strftime("%H:%M"), bool(free), free_resource_ids=free),
                           offer, tz, now, fill))
    return out


def _slot_fill(db: Session, offer: Offer, starts_at: datetime) -> float:
    """Part occupée du créneau au moment de la réserve (mêmes règles que compute_slots)."""
    if offer.booking_mode in CAPACITY_MODES:
        row = db.execute(
            select(SessionInventory.reserved, SessionInventory.capacity).where(
                SessionInventory.offer_id == offer.id, SessionInventory.starts_at == starts_at
            )
        ).first()
        return row[0] / row[1] if row and row[1] else 0.0
    ids = [r.id for r in _bookable_resources(offer)]
    if not ids:
        return 0.0
    during = Range(starts_at, starts_at + timedelta(minutes=offer.current_version.duration_min), bounds="[)")
    busy = db.scalar(
        select(func.count(func.distinct(ResourceOccupancy.resource_id))).where(
            ResourceOccupancy.resource_id.in_(ids),
            ResourceOccupancy.is_active.is_(True),
            ResourceOccupancy.during.overlaps(during),
        )
    )
    return (busy or 0) / len(ids)


def bookable_days(offer: Offer, start: date, days: int, now: datetime) -> list[tuple[date, bool]]:
    """Jours ouverts (selon horaires) ; la disponibilité fine se lit jour par jour."""
    return [(start + timedelta(days=i), bool(_slot_grid(offer, start + timedelta(days=i), now))) for i in range(days)]


# ---------------------------------------------------------------- expiration


def _free_capacity(db: Session, booking: Booking) -> None:
    db.execute(
        update(ResourceOccupancy)
        .where(ResourceOccupancy.booking_id == booking.id, ResourceOccupancy.is_active.is_(True))
        .values(is_active=False)
    )
    if booking.inventory_id is not None:
        db.execute(
            update(SessionInventory)
            .where(SessionInventory.id == booking.inventory_id)
            .values(reserved=SessionInventory.reserved - booking.party_size)
        )


def _lock_wallet_then_booking(db: Session, booking_id: uuid.UUID, *, skip_locked: bool = False) -> Booking | None:
    wallet_id = db.scalar(select(Booking.wallet_id).where(Booking.id == booking_id))
    if wallet_id is None:
        return None
    from app.modules.wallet.models import Wallet

    locked = db.scalar(select(Wallet.id).where(Wallet.id == wallet_id).with_for_update(skip_locked=skip_locked))
    if locked is None:
        return None  # portefeuille occupé par une autre transaction : elle traitera la réservation
    return db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())


def _expire(db: Session, booking: Booking, now: datetime) -> None:
    booking.status = "expired"
    booking.expired_at = now
    _free_capacity(db, booking)
    wallet_service.settle(db, booking.wallet_id, booking_id=booking.id, kind="release", memo="Réserve expirée")
    emit(db, "booking", booking.id, "booking.expired", {"booking_id": str(booking.id)})


def expire_due_holds(db: Session, now: datetime | None = None, limit: int = 200) -> int:
    """Expire les réserves HELD échues. Appelé par Celery beat et avant chaque nouvelle réserve."""
    now = now or datetime.now(UTC)
    ids = db.scalars(
        select(Booking.id)
        .where(Booking.status == "held", Booking.hold_expires_at <= now)
        .order_by(Booking.hold_expires_at)
        .limit(limit)
    ).all()
    count = 0
    for booking_id in ids:
        booking = _lock_wallet_then_booking(db, booking_id, skip_locked=True)
        if booking and booking.status == "held" and booking.hold_expires_at <= now:
            _expire(db, booking, now)
            count += 1
    db.flush()
    return count


# ---------------------------------------------------------------- réserve


def create_hold(
    db: Session,
    *,
    user_id: uuid.UUID,
    offer_id: uuid.UUID,
    starts_at: datetime,
    party_size: int,
    resource_id: uuid.UUID | None,
    expected_price_credits: int | None = None,
    now: datetime | None = None,
) -> Booking:
    now = now or datetime.now(UTC)
    if starts_at.tzinfo is None:
        raise BookingError("invalid_start", "L'heure de début doit inclure un fuseau.", 422)
    offer = load_offer(db, offer_id)
    version = offer.current_version
    location = offer.location
    if offer.booking_mode not in BOOKABLE_MODES:
        raise BookingError("not_bookable", "Cette prestation se réserve auprès du distributeur (billet externe).", 422)
    if location.merchant.psp_status != "verified":
        raise BookingError("partner_not_ready", "Ce partenaire n'accepte pas encore de réservation.", 409)
    if not version.participants_min <= party_size <= version.participants_max:
        raise BookingError(
            "invalid_party_size",
            f"Nombre de participants entre {version.participants_min} et {version.participants_max}.",
            422,
        )

    tz = _tz(offer)
    starts_at = starts_at.astimezone(UTC)
    day = starts_at.astimezone(tz).date()
    if day > now.astimezone(tz).date() + timedelta(days=BOOKING_HORIZON_DAYS):
        raise BookingError("out_of_horizon", "Date trop lointaine.", 422)
    if starts_at not in [s.astimezone(UTC) for s in _slot_grid(offer, day, now)]:
        raise BookingError("invalid_slot", "Ce créneau n'existe pas ou n'est plus réservable.", 422)

    # Les réserves échues ne doivent pas bloquer la capacité (5 min maximum).
    expire_due_holds(db, now)

    price = pricing.slot_price(version.price_credits, starts_at=starts_at, tz=tz, now=now,
                               fill=_slot_fill(db, offer, starts_at))
    if expected_price_credits is not None and expected_price_credits != price.credits:
        raise BookingError(
            "price_changed",
            f"Le prix de ce créneau est passé à {price.credits} crédit(s) par personne.",
            409,
            {"price_credits": price.credits, "price_adjustments": list(price.adjustments)},
        )
    total = price.credits * party_size
    ends_at = starts_at + timedelta(minutes=version.duration_min)
    wallet = wallet_service.get_or_create_wallet(db, user_id, location.merchant.market_id, lock=True)

    booking = Booking(
        id=uuid.uuid4(),
        user_id=user_id,
        wallet_id=wallet.id,
        location_id=location.id,
        offer_id=offer.id,
        offer_version_id=version.id,
        starts_at=starts_at,
        ends_at=ends_at,
        party_size=party_size,
        price_credits_per_person=price.credits,
        price_adjustments=list(price.adjustments),
        total_credits=total,
        status="held",
        hold_expires_at=now + timedelta(minutes=HOLD_MINUTES),
        free_cancellation_until=starts_at - timedelta(hours=version.free_cancellation_hours),
    )

    try:
        with db.begin_nested():
            db.add(booking)
            db.flush()
    except IntegrityError as exc:
        raise BookingError("duplicate_booking", "Vous avez déjà une réservation pour ce créneau.", 409) from exc

    if offer.booking_mode in CAPACITY_MODES:
        _take_capacity(db, offer, booking)
    else:
        _take_resource(db, offer, booking, resource_id)

    try:
        wallet_service.reserve(
            db,
            wallet,
            amount=total,
            category_slug=location.subcategory.category.slug,
            at=starts_at,
            booking_id=booking.id,
            memo=f"Réservation · {version.title}",
        )
    except wallet_service.InsufficientCredits as exc:
        raise BookingError(
            "insufficient_credits", str(exc), 409, {"needed": exc.needed, "available": exc.available}
        ) from exc

    emit(db, "booking", booking.id, "booking.held", {"booking_id": str(booking.id), "total_credits": total})
    db.flush()
    return booking


def _take_capacity(db: Session, offer: Offer, booking: Booking) -> None:
    capacity = offer.current_version.capacity
    if not capacity:
        raise BookingError("not_bookable", "Capacité non configurée pour cette séance.", 422)
    db.execute(
        insert(SessionInventory)
        .values(id=uuid.uuid4(), offer_id=offer.id, starts_at=booking.starts_at, capacity=capacity, reserved=0)
        .on_conflict_do_nothing(index_elements=["offer_id", "starts_at"])
    )
    # Mise à jour conditionnelle atomique : jamais plus de places que la capacité.
    inventory_id = db.scalar(
        update(SessionInventory)
        .where(
            SessionInventory.offer_id == offer.id,
            SessionInventory.starts_at == booking.starts_at,
            SessionInventory.reserved + booking.party_size <= SessionInventory.capacity,
        )
        .values(reserved=SessionInventory.reserved + booking.party_size)
        .returning(SessionInventory.id)
    )
    if inventory_id is None:
        raise BookingError("slot_full", "Cette séance est complète.", 409)
    booking.inventory_id = inventory_id


def _take_resource(db: Session, offer: Offer, booking: Booking, wanted: uuid.UUID | None) -> None:
    candidates = _bookable_resources(offer)
    if wanted is not None:
        candidates = [r for r in candidates if r.id == wanted]
        if not candidates:
            raise BookingError("invalid_resource", "Ce professionnel ne réalise pas cette prestation.", 422)
    if not candidates:
        raise BookingError("not_bookable", "Aucune ressource n'est rattachée à cette prestation.", 422)
    during = Range(booking.starts_at, booking.ends_at, bounds="[)")
    for resource in candidates:
        try:
            # La contrainte d'exclusion tranche les courses : un seul gagnant par ressource et plage.
            with db.begin_nested():
                db.add(ResourceOccupancy(resource_id=resource.id, booking_id=booking.id, during=during))
                db.flush()
            booking.resource_id = resource.id
            return
        except IntegrityError as exc:
            if not isinstance(exc.orig, ExclusionViolation):
                raise
    raise BookingError("slot_unavailable", "Ce créneau vient d'être pris. Choisissez-en un autre.", 409)


# ---------------------------------------------------------------- confirmation / annulation


def _owned(db: Session, user_id: uuid.UUID, booking_id: uuid.UUID) -> Booking:
    booking = _lock_wallet_then_booking(db, booking_id)
    if booking is None or booking.user_id != user_id:
        raise BookingError("booking_not_found", "Réservation introuvable.", 404)
    return booking


def confirm(db: Session, *, user_id: uuid.UUID, booking_id: uuid.UUID, now: datetime | None = None) -> Booking:
    now = now or datetime.now(UTC)
    booking = _owned(db, user_id, booking_id)
    if booking.status == "confirmed":
        return booking  # idempotent
    if booking.status == "held" and booking.hold_expires_at <= now:
        _expire(db, booking, now)
        db.commit()
        raise BookingError("hold_expired", "Le délai de 5 minutes est dépassé : le créneau a été libéré.", 409)
    if booking.status != "held":
        raise BookingError("invalid_state", "Cette réservation ne peut plus être confirmée.", 409)
    booking.status = "confirmed"
    booking.confirmed_at = now
    booking.hold_expires_at = None
    emit(db, "booking", booking.id, "booking.confirmed", {"booking_id": str(booking.id)})
    db.flush()
    return booking


def cancel(db: Session, *, user_id: uuid.UUID, booking_id: uuid.UUID, now: datetime | None = None) -> Booking:
    now = now or datetime.now(UTC)
    booking = _owned(db, user_id, booking_id)
    if booking.status in ("cancelled", "expired"):
        return booking  # idempotent
    if booking.status not in ACTIVE_STATUSES:
        raise BookingError("invalid_state", "Cette réservation ne peut plus être annulée.", 409)
    if booking.starts_at <= now:
        raise BookingError("already_started", "La prestation a déjà commencé.", 409)

    late = booking.status == "confirmed" and now >= booking.free_cancellation_until
    booking.status = "cancelled"
    booking.cancelled_at = now
    booking.late_cancellation = late
    booking.cancel_reason = "Annulation tardive" if late else "Annulation par le client"
    _free_capacity(db, booking)
    if late:
        # Tardive : la moitié est rendue, l'autre consommée et versée au partenaire.
        refund = pricing.late_cancellation_refund(booking.total_credits)
        wallet_service.settle_split(
            db, booking.wallet_id, booking_id=booking.id, capture=booking.total_credits - refund,
            capture_memo="Annulation tardive · part conservée", release_memo="Annulation tardive · moitié rendue",
        )
        booking.refunded_credits = refund
        from app.modules.redemption.service import record_late_cancellation_payable

        record_late_cancellation_payable(db, booking, credits=booking.total_credits - refund)
    else:
        wallet_service.settle(
            db, booking.wallet_id, booking_id=booking.id, kind="release", memo="Restitution de crédits · annulation"
        )
        booking.refunded_credits = booking.total_credits
    emit(db, "booking", booking.id, "booking.cancelled", {"booking_id": str(booking.id), "late": late})
    db.flush()
    return booking


def mark_no_shows(db: Session, now: datetime | None = None, limit: int = 200) -> int:
    """Réservations confirmées jamais validées, fenêtre du QR close : crédits consommés, partenaire payé."""
    from app.modules.redemption.service import REDEEM_LATE, record_no_show_payable

    now = now or datetime.now(UTC)
    ids = db.scalars(
        select(Booking.id)
        .where(Booking.status == "confirmed", Booking.ends_at < now - REDEEM_LATE)
        .order_by(Booking.ends_at)
        .limit(limit)
    ).all()
    count = 0
    for booking_id in ids:
        booking = _lock_wallet_then_booking(db, booking_id, skip_locked=True)
        if booking is None or booking.status != "confirmed" or booking.ends_at >= now - REDEEM_LATE:
            continue
        booking.status = "no_show"
        wallet_service.settle(db, booking.wallet_id, booking_id=booking.id, kind="capture", memo="Absence (non présenté)")
        record_no_show_payable(db, booking, now)
        emit(db, "booking", booking.id, "booking.no_show", {"booking_id": str(booking.id)})
        count += 1
    db.flush()
    return count


# ---------------------------------------------------------------- blocages partenaire


def block_resource(
    db: Session, *, location_id: uuid.UUID, resource_id: uuid.UUID, start: datetime, end: datetime, reason: str,
    created_by: uuid.UUID | None,
) -> ExternalBlock:
    if end <= start:
        raise BookingError("invalid_range", "La fin doit suivre le début.", 422)
    block = ExternalBlock(
        id=uuid.uuid4(), location_id=location_id, resource_id=resource_id, during=Range(start, end, bounds="[)"),
        reason=reason, created_by=created_by,
    )
    try:
        with db.begin_nested():
            db.add(block)
            db.flush()
            db.add(ResourceOccupancy(resource_id=resource_id, external_block_id=block.id, during=block.during))
            db.flush()
    except IntegrityError as exc:
        if isinstance(exc.orig, ExclusionViolation):
            raise BookingError("overlap", "Cette plage chevauche une réservation ou un autre blocage.", 409) from exc
        raise
    return block


# ---------------------------------------------------------------- lecture


def funding_by_source(db: Session, booking_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
    """Répartition initiale des crédits réservés, par source (écritures « reserve »)."""
    from app.modules.wallet.models import CreditJournal, CreditJournalLine, CreditLot

    rows = db.execute(
        select(CreditJournal.booking_id, CreditLot.source, func.sum(CreditJournalLine.amount))
        .join(CreditJournalLine, CreditJournalLine.journal_id == CreditJournal.id)
        .join(CreditLot, CreditLot.id == CreditJournalLine.lot_id)
        .where(
            and_(
                CreditJournal.booking_id.in_(booking_ids),
                CreditJournal.kind == "reserve",
                CreditJournalLine.account == "reserved",
            )
        )
        .group_by(CreditJournal.booking_id, CreditLot.source)
    ).all()
    result: dict[uuid.UUID, dict[str, int]] = {}
    for bid, source, total in rows:
        result.setdefault(bid, {})[source] = int(total)
    return result
