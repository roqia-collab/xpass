"""Gestion de l'établissement par le commerçant (lot 5) : prestations, équipe, horaires, fermetures, blocages."""
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from app.api.deps import CurrentPrincipal, DbSession
from app.modules.booking import service as booking_service
from app.modules.booking.models import ExternalBlock
from app.modules.catalog import management as m
from app.modules.catalog.models import OfferVersion, Resource

router = APIRouter(prefix="/partner/locations/{location_id}", tags=["commerçant"])


def _http(exc: m.ManageError | booking_service.BookingError) -> HTTPException:
    return HTTPException(exc.status, {"code": exc.code, "message": exc.message, **exc.extra})


# ---------------------------------------------------------------- schémas


class OfferIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    summary: str = Field("", max_length=240)
    duration_min: int = Field(ge=15, le=480)
    price_credits: int = Field(ge=1, le=10_000)
    participants_min: int = Field(1, ge=1, le=50)
    participants_max: int = Field(1, ge=1, le=50)
    capacity: int | None = Field(None, ge=1, le=500)
    free_cancellation_hours: int = Field(24, ge=0, le=168)
    resource_ids: list[uuid.UUID] = []

    @model_validator(mode="after")
    def _participants(self):
        if self.participants_max < self.participants_min:
            raise ValueError("Le maximum de participants doit être supérieur ou égal au minimum.")
        return self

    def to_input(self) -> m.OfferInput:
        return m.OfferInput(**self.model_dump(include=set(OfferIn.model_fields)))


class OfferCreateIn(OfferIn):
    booking_mode: Literal["resource_slot", "capacity_session", "open_access"]
    publish: bool = False


class ActiveIn(BaseModel):
    active: bool


class ResourceIn(BaseModel):
    kind: Literal["staff", "equipment", "room"] = "staff"
    name: str = Field(min_length=1, max_length=80)
    role_label: str = Field(min_length=1, max_length=80)


class ResourceUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    role_label: str = Field(min_length=1, max_length=80)
    active: bool


class HoursIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    opens_at: time
    closes_at: time


class ExceptionIn(BaseModel):
    day: date
    is_closed: bool = True
    opens_at: time | None = None
    closes_at: time | None = None
    reason: str | None = Field(None, max_length=160)


class LocationIn(BaseModel):
    description: str = Field("", max_length=2000)
    access_info: str | None = Field(None, max_length=240)
    meeting_point: str | None = Field(None, max_length=240)
    wheelchair_accessible: bool = False
    review_url: str | None = Field(None, max_length=500)


class BlockIn(BaseModel):
    resource_id: uuid.UUID
    # Heures murales du lieu (« 2026-11-03T12:00 »), converties avec le fuseau du marché.
    local_start: datetime
    local_end: datetime
    reason: str = Field(min_length=2, max_length=160)


class ImpactOut(BaseModel):
    """Réservations à venir hors des nouveaux horaires : jamais annulées automatiquement."""

    ok: bool = True
    bookings_outside_hours: int = 0


class VersionOut(BaseModel):
    id: uuid.UUID
    version: int
    title: str
    summary: str
    duration_min: int
    price_credits: int
    participants_min: int
    participants_max: int
    capacity: int | None
    free_cancellation_hours: int


class ManagedOfferOut(BaseModel):
    id: uuid.UUID
    booking_mode: str
    is_active: bool
    image_key: str | None
    current: VersionOut
    resource_ids: list[uuid.UUID]
    versions_count: int


class ManagedResourceOut(BaseModel):
    id: uuid.UUID
    kind: str
    name: str
    role_label: str
    is_active: bool


class ManagedHoursOut(BaseModel):
    weekday: int
    opens_at: str
    closes_at: str


class ManagedExceptionOut(BaseModel):
    id: uuid.UUID
    day: date
    is_closed: bool
    opens_at: str | None
    closes_at: str | None
    reason: str | None


class ManageOut(BaseModel):
    id: uuid.UUID
    name: str
    district_label: str
    can_edit: bool
    description: str
    access_info: str | None
    meeting_point: str | None
    wheelchair_accessible: bool
    review_url: str | None
    cover_image_key: str | None
    offers: list[ManagedOfferOut]
    resources: list[ManagedResourceOut]
    hours: list[ManagedHoursOut]
    exceptions: list[ManagedExceptionOut]


class BlockOut(BaseModel):
    id: uuid.UUID
    resource_id: uuid.UUID
    resource_name: str
    reason: str
    local_start: str
    local_end: str


def _hm(t: time | None) -> str | None:
    return t.strftime("%H:%M") if t else None


# ---------------------------------------------------------------- lecture


@router.get("/manage", response_model=ManageOut)
def manage(location_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> ManageOut:
    try:
        loc = m.load_location(db, principal, location_id, m.STAFF)
    except m.ManageError as exc:
        raise _http(exc) from exc
    counts = dict(db.execute(
        select(OfferVersion.offer_id, OfferVersion.version).where(OfferVersion.offer_id.in_([o.id for o in loc.offers]))
        .order_by(OfferVersion.version)
    ).all())
    today = datetime.now(ZoneInfo(loc.merchant.market.timezone)).date()
    return ManageOut(
        id=loc.id, name=loc.name, district_label=loc.district_label,
        can_edit=loc.merchant_id in principal.scope_ids("merchant", m.OWNER),
        description=loc.description, access_info=loc.access_info, meeting_point=loc.meeting_point,
        wheelchair_accessible=loc.wheelchair_accessible, review_url=loc.review_url, cover_image_key=loc.cover_image_key,
        offers=[
            ManagedOfferOut(
                id=o.id, booking_mode=o.booking_mode, is_active=o.is_active, image_key=o.image_key,
                current=VersionOut.model_validate(o.current_version, from_attributes=True),
                resource_ids=[r.id for r in o.resources], versions_count=counts.get(o.id, 1),
            )
            for o in loc.offers if o.current_version is not None and o.sort_order < 90
        ],
        resources=[ManagedResourceOut.model_validate(r, from_attributes=True) for r in loc.resources],
        hours=[ManagedHoursOut(weekday=h.weekday, opens_at=_hm(h.opens_at), closes_at=_hm(h.closes_at))
               for h in loc.opening_hours],
        exceptions=[
            ManagedExceptionOut(id=e.id, day=e.day, is_closed=e.is_closed, opens_at=_hm(e.opens_at),
                                closes_at=_hm(e.closes_at), reason=e.reason)
            for e in sorted(loc.exceptions, key=lambda e: e.day) if e.day >= today
        ],
    )


# ---------------------------------------------------------------- écriture


def _run(db, principal, location_id: uuid.UUID, roles, fn):
    try:
        loc = m.load_location(db, principal, location_id, roles)
        result = fn(loc)
        db.commit()
        return result
    except (m.ManageError, booking_service.BookingError) as exc:
        db.rollback()
        raise _http(exc) from exc


@router.patch("", response_model=ImpactOut)
def update_location(location_id: uuid.UUID, body: LocationIn, principal: CurrentPrincipal, db: DbSession):
    _run(db, principal, location_id, m.OWNER, lambda loc: m.update_location(db, loc, **body.model_dump()))
    return ImpactOut()


@router.post("/offers", status_code=201, response_model=ImpactOut)
def create_offer(location_id: uuid.UUID, body: OfferCreateIn, principal: CurrentPrincipal, db: DbSession):
    _run(db, principal, location_id, m.OWNER, lambda loc: m.create_offer(
        db, loc, booking_mode=body.booking_mode, data=body.to_input(), publish=body.publish))
    return ImpactOut()


@router.put("/offers/{offer_id}", response_model=ImpactOut)
def update_offer(location_id: uuid.UUID, offer_id: uuid.UUID, body: OfferIn, principal: CurrentPrincipal, db: DbSession):
    _run(db, principal, location_id, m.OWNER, lambda loc: m.update_offer(db, loc, offer_id, body.to_input()))
    return ImpactOut()


@router.post("/offers/{offer_id}/active", response_model=ImpactOut)
def set_offer_active(location_id: uuid.UUID, offer_id: uuid.UUID, body: ActiveIn, principal: CurrentPrincipal,
                     db: DbSession):
    _run(db, principal, location_id, m.OWNER, lambda loc: m.set_offer_active(db, loc, offer_id, body.active))
    return ImpactOut()


@router.post("/resources", status_code=201, response_model=ImpactOut)
def create_resource(location_id: uuid.UUID, body: ResourceIn, principal: CurrentPrincipal, db: DbSession):
    _run(db, principal, location_id, m.OWNER, lambda loc: m.create_resource(db, loc, **body.model_dump()))
    return ImpactOut()


@router.put("/resources/{resource_id}", response_model=ImpactOut)
def update_resource(location_id: uuid.UUID, resource_id: uuid.UUID, body: ResourceUpdateIn,
                    principal: CurrentPrincipal, db: DbSession):
    _run(db, principal, location_id, m.OWNER, lambda loc: m.update_resource(db, loc, resource_id, **body.model_dump()))
    return ImpactOut()


@router.put("/hours", response_model=ImpactOut)
def replace_hours(location_id: uuid.UUID, body: list[HoursIn], principal: CurrentPrincipal, db: DbSession):
    n = _run(db, principal, location_id, m.OWNER,
             lambda loc: m.replace_hours(db, loc, [(h.weekday, h.opens_at, h.closes_at) for h in body]))
    return ImpactOut(bookings_outside_hours=n)


@router.post("/exceptions", status_code=201, response_model=ImpactOut)
def add_exception(location_id: uuid.UUID, body: ExceptionIn, principal: CurrentPrincipal, db: DbSession):
    _, n = _run(db, principal, location_id, m.OWNER, lambda loc: m.add_exception(db, loc, **body.model_dump()))
    return ImpactOut(bookings_outside_hours=n)


@router.delete("/exceptions/{exception_id}", response_model=ImpactOut)
def delete_exception(location_id: uuid.UUID, exception_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession):
    _run(db, principal, location_id, m.OWNER, lambda loc: m.delete_exception(db, loc, exception_id))
    return ImpactOut()


# ---------------------------------------------------------------- blocages (personnel autorisé)


@router.get("/blocks", response_model=list[BlockOut])
def list_blocks(location_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession,
                start: Annotated[date, Query()], days: Annotated[int, Query(ge=1, le=7)] = 1) -> list[BlockOut]:
    try:
        loc = m.load_location(db, principal, location_id, m.STAFF)
    except m.ManageError as exc:
        raise _http(exc) from exc
    tz = ZoneInfo(loc.merchant.market.timezone)
    lo = datetime.combine(start, time.min, tz)
    hi = lo + timedelta(days=days)
    rows = db.execute(
        select(ExternalBlock, Resource.name).join(Resource, Resource.id == ExternalBlock.resource_id)
        .where(ExternalBlock.location_id == loc.id, ExternalBlock.is_active.is_(True))
    ).all()
    out = []
    for b, name in rows:
        if b.during.upper <= lo or b.during.lower >= hi:
            continue
        out.append(BlockOut(
            id=b.id, resource_id=b.resource_id, resource_name=name, reason=b.reason,
            local_start=b.during.lower.astimezone(tz).replace(tzinfo=None).isoformat(timespec="minutes"),
            local_end=b.during.upper.astimezone(tz).replace(tzinfo=None).isoformat(timespec="minutes"),
        ))
    return sorted(out, key=lambda x: x.local_start)


@router.post("/blocks", status_code=201, response_model=ImpactOut)
def create_block(location_id: uuid.UUID, body: BlockIn, principal: CurrentPrincipal, db: DbSession):
    def fn(loc):
        if body.resource_id not in {r.id for r in loc.resources if r.is_active}:
            raise m.ManageError("invalid_resource", "Ressource inconnue ou inactive.", 422)
        tz = ZoneInfo(loc.merchant.market.timezone)
        start = body.local_start.replace(tzinfo=tz).astimezone(UTC)
        end = body.local_end.replace(tzinfo=tz).astimezone(UTC)
        if end - start > timedelta(days=14):
            raise m.ManageError("too_long", "Un blocage ne peut pas dépasser 14 jours.", 422)
        if end <= datetime.now(UTC):
            raise m.ManageError("past_range", "Cette plage est déjà passée.", 422)
        return booking_service.block_resource(db, location_id=loc.id, resource_id=body.resource_id, start=start,
                                              end=end, reason=body.reason.strip(), created_by=principal.user.id)

    _run(db, principal, location_id, m.STAFF, fn)
    return ImpactOut()


@router.delete("/blocks/{block_id}", response_model=ImpactOut)
def delete_block(location_id: uuid.UUID, block_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession):
    _run(db, principal, location_id, m.STAFF, lambda loc: m.remove_block(db, loc, block_id))
    return ImpactOut()
