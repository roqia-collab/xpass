import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import CurrentPrincipal, DbSession
from app.modules.booking import service
from app.modules.booking.models import Booking
from app.modules.booking.schemas import (
    PassOut,
    ReceiptOut,
    AvailabilityOut,
    BookingListOut,
    BookingOut,
    DaySchema,
    HoldIn,
    SlotSchema,
    booking_out,
)
from app.modules.catalog.models import Location, Merchant, Subcategory
from app.modules.platform.service import IdempotencyMismatch, run_idempotent
from app.modules.redemption import service as redemption_service
from app.modules.redemption.models import Receipt

router = APIRouter(tags=["réservations"])

IdemKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)]


def _http(exc: service.BookingError) -> HTTPException:
    return HTTPException(exc.status, {"code": exc.code, "message": exc.message, **exc.extra})


def _load(db: Session, ids: list[uuid.UUID]) -> list[Booking]:
    return list(
        db.scalars(
            select(Booking)
            .options(
                selectinload(Booking.location).selectinload(Location.merchant).selectinload(Merchant.market),
                selectinload(Booking.location).selectinload(Location.city),
                selectinload(Booking.location).selectinload(Location.subcategory).selectinload(Subcategory.category),
                selectinload(Booking.offer_version),
                selectinload(Booking.resource),
            )
            .where(Booking.id.in_(ids))
        )
    )


def _receipt_refs(db: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    return dict(db.execute(select(Receipt.booking_id, Receipt.reference).where(Receipt.booking_id.in_(ids))).all())


def _out(db: Session, booking_id: uuid.UUID) -> dict:
    db.expire_all()
    b = _load(db, [booking_id])[0]
    funding = service.funding_by_source(db, [b.id]).get(b.id, {})
    return booking_out(b, funding, receipt_reference=_receipt_refs(db, [b.id]).get(b.id)).model_dump(mode="json")


def _idempotent(db: Session, principal, scope: str, key: str, body: dict, action) -> JSONResponse:
    try:
        result = run_idempotent(db, user_id=principal.user.id, scope=scope, key=key, body=body, action=action)
    except IdempotencyMismatch as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"code": "idempotency_mismatch", "message": "Clé d'idempotence déjà utilisée pour une autre requête."},
        ) from exc
    except service.BookingError as exc:
        db.rollback()
        raise _http(exc) from exc
    headers = {"Idempotent-Replayed": "true"} if result.replayed else {}
    return JSONResponse(result.body, status_code=result.status, headers=headers)


# ---------------------------------------------------------------- disponibilités (public)


@router.get("/catalog/offers/{offer_id}/availability", response_model=AvailabilityOut)
def offer_availability(offer_id: uuid.UUID, db: DbSession, day: Annotated[date | None, Query(alias="date")] = None):
    try:
        offer = service.load_offer(db, offer_id)
    except service.BookingError as exc:
        raise _http(exc) from exc
    now = datetime.now(UTC)
    tz = offer.location.merchant.market.timezone
    today = now.astimezone(ZoneInfo(tz)).date()
    day = day or today
    if day < today or day > today + timedelta(days=service.BOOKING_HORIZON_DAYS):
        raise HTTPException(422, {"code": "out_of_horizon", "message": "Date hors de la période réservable."})
    v = offer.current_version
    slots = service.compute_slots(db, offer, day, now)
    return AvailabilityOut(
        offer_id=offer.id,
        offer_title=v.title,
        booking_mode=offer.booking_mode,
        duration_min=v.duration_min,
        price_credits=v.price_credits,
        participants_min=v.participants_min,
        participants_max=v.participants_max,
        location_slug=offer.location.slug,
        location_name=offer.location.name,
        city_name=offer.location.city.name,
        timezone=tz,
        date=day,
        days=[DaySchema(date=d, open=o) for d, o in service.bookable_days(offer, today, 14, now)],
        resources=[
            {"id": str(r.id), "name": r.name, "role_label": r.role_label}
            for r in service._bookable_resources(offer)
        ]
        if offer.booking_mode == "resource_slot"
        else [],
        slots=[SlotSchema(**s.__dict__) for s in slots],
    )


# ---------------------------------------------------------------- commandes (idempotentes)


@router.post("/bookings", status_code=201, response_model=BookingOut, responses={409: {}, 422: {}})
def hold(body: HoldIn, principal: CurrentPrincipal, db: DbSession, idempotency_key: IdemKey):
    """Crée une réserve HELD de 5 minutes : capacité ET crédits bloqués. Rien n'est consommé."""

    def action():
        booking = service.create_hold(
            db,
            user_id=principal.user.id,
            offer_id=body.offer_id,
            starts_at=body.starts_at,
            party_size=body.party_size,
            resource_id=body.resource_id,
            expected_price_credits=body.expected_price_credits,
        )
        db.flush()
        return 201, _out(db, booking.id)

    return _idempotent(db, principal, "bookings.hold", idempotency_key, body.model_dump(mode="json"), action)


class EventHoldIn(BaseModel):
    event_id: uuid.UUID
    party_size: int = Field(1, ge=1, le=1)
    expected_price_credits: int | None = Field(None, ge=1, le=500)


@router.post("/bookings/events", status_code=201, response_model=BookingOut, responses={409: {}, 422: {}})
def hold_event(body: EventHoldIn, principal: CurrentPrincipal, db: DbSession, idempotency_key: IdemKey):
    """Réserve une place sur la séance publiée. Même confirmation ensuite qu'une prestation."""

    def action():
        booking = service.create_event_hold(
            db, user_id=principal.user.id, event_id=body.event_id, party_size=body.party_size,
            expected_price_credits=body.expected_price_credits,
        )
        db.flush()
        return 201, _out(db, booking.id)

    return _idempotent(db, principal, "bookings.event_hold", idempotency_key, body.model_dump(mode="json"), action)


@router.post("/bookings/{booking_id}/confirm", response_model=BookingOut)
def confirm(booking_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession, idempotency_key: IdemKey):
    def action():
        service.confirm(db, user_id=principal.user.id, booking_id=booking_id)
        return 200, _out(db, booking_id)

    return _idempotent(db, principal, "bookings.confirm", idempotency_key, {"booking_id": str(booking_id)}, action)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingOut)
def cancel(booking_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession, idempotency_key: IdemKey):
    def action():
        service.cancel(db, user_id=principal.user.id, booking_id=booking_id)
        return 200, _out(db, booking_id)

    return _idempotent(db, principal, "bookings.cancel", idempotency_key, {"booking_id": str(booking_id)}, action)


# ---------------------------------------------------------------- lecture


@router.get("/bookings", response_model=BookingListOut)
def list_bookings(
    principal: CurrentPrincipal, db: DbSession, scope: Literal["upcoming", "past", "cancelled"] = "upcoming"
):
    now = datetime.now(UTC)
    rows = db.execute(
        select(Booking.id, Booking.status, Booking.ends_at).where(Booking.user_id == principal.user.id)
    ).all()

    def bucket(status_: str, ends_at: datetime) -> str | None:
        if status_ in ("cancelled", "expired"):
            return "cancelled" if status_ == "cancelled" else None
        if status_ == "held":
            return None  # réserve non confirmée : visible seulement dans le parcours de confirmation
        return "upcoming" if ends_at > now and status_ == "confirmed" else "past"

    buckets: dict[str, list[uuid.UUID]] = {"upcoming": [], "past": [], "cancelled": []}
    for bid, st, ends in rows:
        b = bucket(st, ends)
        if b:
            buckets[b].append(bid)
    items = _load(db, buckets[scope])
    items.sort(key=lambda b: b.starts_at, reverse=scope != "upcoming")
    funding = service.funding_by_source(db, [b.id for b in items])
    refs = _receipt_refs(db, [b.id for b in items])
    return BookingListOut(
        items=[booking_out(b, funding.get(b.id, {}), now, refs.get(b.id)) for b in items],
        counts={k: len(v) for k, v in buckets.items()},
    )


@router.get("/bookings/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession):
    found = _load(db, [booking_id])
    if not found or found[0].user_id != principal.user.id:
        raise HTTPException(404, {"code": "booking_not_found", "message": "Réservation introuvable."})
    b = found[0]
    return booking_out(
        b, service.funding_by_source(db, [b.id]).get(b.id, {}), receipt_reference=_receipt_refs(db, [b.id]).get(b.id)
    )


def _owned_booking(db: Session, principal, booking_id: uuid.UUID) -> Booking:
    found = _load(db, [booking_id])
    if not found or found[0].user_id != principal.user.id:
        raise HTTPException(404, {"code": "booking_not_found", "message": "Réservation introuvable."})
    return found[0]


@router.post("/bookings/{booking_id}/pass", response_model=PassOut)
def issue_pass(booking_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> PassOut:
    """Émet un QR + code court valables 60 s (les précédents sont révoqués). Aucun effet financier."""
    try:
        issued = redemption_service.issue_pass(db, user_id=principal.user.id, booking_id=booking_id)
        db.commit()
    except service.BookingError as exc:
        db.rollback()
        raise _http(exc) from exc
    return PassOut(
        qr_payload=issued.qr_payload,
        manual_code=issued.manual_code,
        expires_at=issued.expires_at,
        expires_in=int(redemption_service.TOKEN_TTL.total_seconds()),
    )


@router.get("/bookings/{booking_id}/receipt", response_model=ReceiptOut)
def receipt(booking_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> ReceiptOut:
    b = _owned_booking(db, principal, booking_id)
    r = db.scalar(select(Receipt).where(Receipt.booking_id == b.id))
    if r is None or b.redeemed_at is None:
        raise HTTPException(404, {"code": "receipt_not_found", "message": "Pas encore de reçu pour cette réservation."})
    tz = b.location.merchant.market.timezone
    order = ["employer", "promotional", "personal"]
    return ReceiptOut(
        reference=r.reference,
        booking_id=b.id,
        location_name=b.location.name,
        offer_title=b.offer_version.title,
        city_name=b.location.city.name,
        cover_image_key=b.location.cover_image_key,
        redeemed_at=b.redeemed_at,
        local_redeemed_at=b.redeemed_at.astimezone(ZoneInfo(tz)).replace(tzinfo=None).isoformat(timespec="minutes"),
        credits_total=r.credits_total,
        funding=[{"source": s, "credits": r.funding[s]} for s in order if r.funding.get(s)],
        review_url=b.location.review_url,
    )


@router.get("/bookings/{booking_id}/calendar.ics", response_class=Response)
def calendar_ics(booking_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> Response:
    """Fichier agenda sans aucun jeton QR (seulement horaire, lieu et titre)."""
    b = _owned_booking(db, principal, booking_id)
    if b.status not in ("confirmed", "redeemed"):
        raise HTTPException(409, {"code": "not_confirmed", "message": "Réservation non confirmée."})
    loc = b.location
    body = redemption_service.ics_for(
        b,
        title=f"{b.offer_version.title} · {loc.name}",
        address=f"{loc.address_line}, {loc.postal_code} {loc.city.name}",
    )
    return Response(
        body,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="xpass-{b.id}.ics"'},
    )


class DisputeIn(BaseModel):
    reason: str = Field(max_length=2000)


class MyDisputeOut(BaseModel):
    reference: str
    status: str
    created_at: datetime
    credits_restored: int | None
    resolution_reason: str | None


@router.post("/bookings/{booking_id}/disputes", status_code=201, response_model=MyDisputeOut)
def open_dispute(booking_id: uuid.UUID, body: DisputeIn, principal: CurrentPrincipal, db: DbSession) -> MyDisputeOut:
    """Réclamation du client sur une prestation utilisée ou une annulation tardive (examinée par XPASS)."""
    from app.modules.ops import service as ops

    try:
        d = ops.open_dispute(db, user_id=principal.user.id, booking_id=booking_id, reason=body.reason)
        db.commit()
    except ops.OpsError as exc:
        db.rollback()
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc
    return MyDisputeOut.model_validate(d, from_attributes=True)


@router.get("/bookings/{booking_id}/disputes", response_model=list[MyDisputeOut])
def my_disputes(booking_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> list[MyDisputeOut]:
    from app.modules.ops.models import Dispute

    _owned_booking(db, principal, booking_id)
    rows = db.scalars(select(Dispute).where(Dispute.booking_id == booking_id).order_by(Dispute.created_at.desc()))
    # Les notes internes de l'équipe XPASS ne sont jamais exposées au client.
    return [MyDisputeOut.model_validate(d, from_attributes=True) for d in rows]
