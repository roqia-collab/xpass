"""Réseau de commerçants : inscription d'un partenaire réel et photos envoyées par les commerçants."""
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentPrincipal, DbSession
from app.modules.catalog import management as m
from app.modules.catalog import onboarding, photos
from app.modules.catalog.models import Location, LocationChangeRequest, Offer
from app.modules.identity.models import Membership, User
from app.modules.ops import service as ops
from app.modules.ops.service import audit

router = APIRouter(tags=["réseau de commerçants"])


def _error(exc: onboarding.OnboardingError | photos.PhotoError | m.ManageError, status: int | None = None):
    return HTTPException(status or getattr(exc, "status", 422), {"code": exc.code, "message": exc.message})


# ---------------------------------------------------------------- inscription


class CompanyOut(BaseModel):
    status: str  # verified | unavailable
    siret: str
    legal_name: str | None = None
    trade_name: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    naf_code: str | None = None


@router.get("/partners/siret/{siret}", response_model=CompanyOut)
def check_siret(siret: str, principal: CurrentPrincipal) -> CompanyOut:
    """Aperçu de l'entreprise avant candidature (annuaire public). Compte XPASS requis."""
    try:
        company, check = onboarding.check_company(siret)
    except onboarding.OnboardingError as exc:
        raise _error(exc) from exc
    if company is None:
        return CompanyOut(status=check["status"], siret=onboarding.directory.normalize_siret(siret))
    return CompanyOut(status="verified", siret=company.siret, legal_name=company.legal_name,
                      trade_name=company.trade_name, address=company.address, postal_code=company.postal_code,
                      city=company.city, naf_code=company.naf_code)


class ApplicationIn(BaseModel):
    siret: str = Field(min_length=14, max_length=20)
    display_name: str = Field("", max_length=120)
    contact_phone: str = Field(min_length=6, max_length=30)
    location_name: str = Field(min_length=2, max_length=120)
    subcategory_slug: str = Field(min_length=2, max_length=32)
    kind_label: str = Field("", max_length=80)
    address_line: str = Field(min_length=3, max_length=200)
    postal_code: str = Field(pattern=r"^\d{5}$")
    city: str = Field(min_length=2, max_length=80)
    description: str = Field("", max_length=2000)


class ApplicationOut(BaseModel):
    merchant_id: uuid.UUID
    location_id: uuid.UUID
    company_check: str
    address_label: str


@router.post("/partners/applications", response_model=ApplicationOut, status_code=201)
def apply(body: ApplicationIn, principal: CurrentPrincipal, db: DbSession) -> ApplicationOut:
    try:
        merchant = onboarding.apply(db, principal.user, onboarding.Application(**body.model_dump()))
        location = db.scalar(select(Location).where(Location.merchant_id == merchant.id))
        out = ApplicationOut(merchant_id=merchant.id, location_id=location.id,
                             company_check=merchant.company_check["status"], address_label=location.geocode_label or "")
        db.commit()
        return out
    except onboarding.OnboardingError as exc:
        db.rollback()
        raise _error(exc) from exc


# ---------------------------------------------------------------- photos


async def _read(file: UploadFile) -> bytes:
    data = await file.read(photos.MAX_BYTES + 1)
    try:
        return photos.prepare(data)
    except photos.PhotoError as exc:
        raise _error(exc, 422) from exc


@router.post("/partner/locations/{location_id}/cover", response_model=dict)
async def upload_cover(location_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession,
                       file: UploadFile = File(...)) -> dict:
    try:
        loc = m.load_location(db, principal, location_id, m.OWNER)
    except m.ManageError as exc:
        raise _error(exc) from exc
    jpeg = await _read(file)
    key = onboarding.new_media_key(loc.merchant_id)
    photos.store(key, jpeg)
    loc.cover_image_key = key
    audit(db, actor_kind="partner", actor_user_id=principal.user.id, action="location.photo", object_type="location",
          object_id=loc.id, object_label=loc.name, details={"key": key})
    db.commit()
    return {"image_key": key}


@router.post("/partner/locations/{location_id}/offers/{offer_id}/image", response_model=dict)
async def upload_offer_image(location_id: uuid.UUID, offer_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession,
                             file: UploadFile = File(...)) -> dict:
    try:
        loc = m.load_location(db, principal, location_id, m.OWNER)
    except m.ManageError as exc:
        raise _error(exc) from exc
    offer = db.scalar(select(Offer).where(Offer.id == offer_id, Offer.location_id == loc.id))
    if offer is None:
        raise HTTPException(404, {"code": "offer_not_found", "message": "Prestation introuvable."})
    jpeg = await _read(file)
    key = onboarding.new_media_key(loc.merchant_id)
    photos.store(key, jpeg)
    offer.image_key = key
    db.commit()
    return {"image_key": key}


# ---------------------------------------------------------------- équipe (comptes de connexion)


class TeamAccessOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    linked: bool  # première connexion faite
    is_you: bool
    created_at: datetime


class TeamInviteIn(BaseModel):
    email: str = Field(max_length=254)
    role: Literal["merchant_owner", "merchant_staff"] = "merchant_staff"


def _owner_location(db, principal, location_id: uuid.UUID):
    try:
        return m.load_location(db, principal, location_id, m.OWNER)
    except m.ManageError as exc:
        raise _error(exc) from exc


def _ops_error(exc: ops.OpsError) -> HTTPException:
    return HTTPException(exc.status, {"code": exc.code, "message": exc.message})


@router.get("/partner/locations/{location_id}/access", response_model=list[TeamAccessOut])
def team_access(location_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> list[TeamAccessOut]:
    """Comptes ayant accès au portail de ce commerçant (responsable uniquement)."""
    loc = _owner_location(db, principal, location_id)
    rows = db.execute(select(Membership, User).join(User, User.id == Membership.user_id)
                      .where(Membership.scope_type == "merchant", Membership.scope_id == loc.merchant_id)
                      .order_by(Membership.created_at)).all()
    return [TeamAccessOut(id=mb.id, email=u.email, display_name=u.display_name, role=mb.role,
                          linked=u.oidc_subject is not None, is_you=u.id == principal.user.id, created_at=mb.created_at)
            for mb, u in rows]


@router.post("/partner/locations/{location_id}/access", response_model=dict, status_code=201)
def team_invite(location_id: uuid.UUID, body: TeamInviteIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    loc = _owner_location(db, principal, location_id)
    try:
        mb = ops.grant_access(db, email=body.email, scope_type="merchant", scope_id=loc.merchant_id, role=body.role,
                              by=principal.user.id, actor_kind="partner", by_name=principal.user.display_name)
        db.commit()
        return {"id": str(mb.id)}
    except ops.OpsError as exc:
        db.rollback()
        raise _ops_error(exc) from exc


@router.post("/partner/locations/{location_id}/access/{membership_id}/revoke", response_model=dict)
def team_revoke(location_id: uuid.UUID, membership_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> dict:
    loc = _owner_location(db, principal, location_id)
    try:
        ops.revoke_access(db, membership_id=membership_id, by=principal.user.id, scope_id=loc.merchant_id,
                          actor_kind="partner")
        db.commit()
        return {"ok": True}
    except ops.OpsError as exc:
        db.rollback()
        raise _ops_error(exc) from exc


# ---------------------------------------------------------------- établissements supplémentaires


class LocationCreateIn(BaseModel):
    location_name: str = Field(min_length=2, max_length=120)
    subcategory_slug: str = Field(min_length=2, max_length=32)
    kind_label: str = Field("", max_length=80)
    address_line: str = Field(min_length=3, max_length=200)
    postal_code: str = Field(pattern=r"^\d{5}$")
    city: str = Field(min_length=2, max_length=80)
    description: str = Field("", max_length=2000)


@router.post("/partner/locations/{location_id}/siblings", response_model=dict, status_code=201)
def add_location(location_id: uuid.UUID, body: LocationCreateIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    """Nouvel établissement du même commerçant (responsable uniquement), en brouillon jusqu'à publication XPASS."""
    loc = _owner_location(db, principal, location_id)
    try:
        new = onboarding.add_location(db, principal.user, loc.merchant, onboarding.LocationData(**body.model_dump()))
        out = {"id": str(new.id), "address_label": new.geocode_label}
        db.commit()
        return out
    except onboarding.OnboardingError as exc:
        db.rollback()
        raise _error(exc) from exc


# ---------------------------------------------------------------- demandes de modification


class ChangeIn(BaseModel):
    name: str = Field("", max_length=120)
    subcategory_slug: str = Field("", max_length=32)
    kind_label: str = Field("", max_length=80)
    address_line: str = Field("", max_length=200)
    postal_code: str = Field("", pattern=r"^(\d{5})?$")
    city: str = Field("", max_length=80)


class ChangeOut(BaseModel):
    id: uuid.UUID
    status: str
    changes: dict
    decision_reason: str | None
    created_at: datetime
    decided_at: datetime | None


@router.get("/partner/locations/{location_id}/change-requests", response_model=list[ChangeOut])
def change_requests(location_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> list[ChangeOut]:
    _owner_location(db, principal, location_id)
    rows = db.scalars(select(LocationChangeRequest).where(LocationChangeRequest.location_id == location_id)
                      .order_by(LocationChangeRequest.created_at.desc()).limit(5)).all()
    return [ChangeOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/partner/locations/{location_id}/change-requests", response_model=ChangeOut, status_code=201)
def request_change(location_id: uuid.UUID, body: ChangeIn, principal: CurrentPrincipal, db: DbSession) -> ChangeOut:
    loc = _owner_location(db, principal, location_id)
    if body.address_line and not (body.postal_code and body.city):
        raise HTTPException(422, {"code": "address_incomplete", "message": "Indiquez la rue, le code postal et la commune."})
    try:
        req = onboarding.request_change(db, principal.user, loc, onboarding.ChangeData(**body.model_dump()))
        out = ChangeOut.model_validate(req, from_attributes=True)
        db.commit()
        return out
    except onboarding.OnboardingError as exc:
        db.rollback()
        raise _error(exc) from exc


# ---------------------------------------------------------------- statistiques (maquette 21 : « Statistiques »)


class WeekPoint(BaseModel):
    week_start: str
    visits: int
    gross_minor: int


class TopOffer(BaseModel):
    title: str
    visits: int
    credits: int


class StatsOut(BaseModel):
    days: int
    currency: str
    visits: int
    unique_customers: int
    credits_used: int
    gross_minor: int
    commission_minor: int
    net_minor: int
    pending_valuation: int  # prestations pas encore valorisées (barème) : exclues des montants
    upcoming_bookings: int
    cancellations: int
    late_cancellations: int
    # Clients absents (ni annulation ni passage) : crédits consommés et versés à l'établissement.
    no_shows: int = 0
    # Visites réservées à un prix ajusté (heure de pointe / forte demande, ou dernière minute).
    surcharged_visits: int = 0
    discounted_visits: int = 0
    weeks: list[WeekPoint]
    top_offers: list[TopOffer]
    weekdays: list[int]  # visites du lundi (0) au dimanche (6), heure locale de l'établissement


@router.get("/partner/locations/{location_id}/stats", response_model=StatsOut)
def location_stats(location_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession,
                   days: int = 30) -> StatsOut:
    """Indicateurs de l'établissement sur la période (responsable uniquement : montants financiers)."""
    from datetime import UTC, timedelta

    from sqlalchemy import func

    from app.modules.booking.models import Booking
    from app.modules.catalog.models import Market, OfferVersion
    from app.modules.redemption.models import PartnerPayable

    if days not in (7, 30, 90, 365):
        raise HTTPException(422, {"code": "invalid_period", "message": "Période : 7, 30, 90 ou 365 jours."})
    loc = _owner_location(db, principal, location_id)
    market = db.get(Market, loc.merchant.market_id)
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    redeemed = (Booking.location_id == loc.id, Booking.status == "redeemed", Booking.redeemed_at >= since)

    visits, customers = db.execute(select(func.count(), func.count(func.distinct(Booking.user_id))).where(*redeemed)).one()
    pay = db.execute(
        select(func.coalesce(func.sum(PartnerPayable.credits), 0),
               func.coalesce(func.sum(PartnerPayable.amount_minor), 0),
               func.coalesce(func.sum(PartnerPayable.commission_minor), 0),
               func.count().filter(PartnerPayable.amount_minor.is_(None)),
               func.count().filter(PartnerPayable.kind == "late_cancellation"),
               func.count().filter(PartnerPayable.kind == "no_show"))
        .where(PartnerPayable.location_id == loc.id, PartnerPayable.occurred_at >= since)
    ).one()
    upcoming = db.scalar(select(func.count()).select_from(Booking).where(
        Booking.location_id == loc.id, Booking.status == "confirmed", Booking.starts_at > now))
    cancellations = db.scalar(select(func.count()).select_from(Booking).where(
        Booking.location_id == loc.id, Booking.status == "cancelled", Booking.cancelled_at >= since))

    local = func.timezone(market.timezone, Booking.redeemed_at)
    week = func.date_trunc("week", local)
    weeks = db.execute(
        select(week, func.count(), func.coalesce(func.sum(PartnerPayable.amount_minor), 0))
        .select_from(Booking).outerjoin(PartnerPayable, PartnerPayable.booking_id == Booking.id)
        .where(*redeemed).group_by(week).order_by(week)
    ).all()
    top = db.execute(
        select(OfferVersion.title, func.count(), func.coalesce(func.sum(Booking.total_credits), 0))
        .join(OfferVersion, OfferVersion.id == Booking.offer_version_id)
        .where(*redeemed).group_by(OfferVersion.title).order_by(func.count().desc()).limit(5)
    ).all()
    adjusted = db.execute(select(
        func.count().filter(Booking.price_adjustments.overlap(["peak", "demand"])),
        func.count().filter(Booking.price_adjustments.contains(["last_minute"])),
    ).where(*redeemed)).one()
    dow = dict(db.execute(select(func.extract("isodow", local), func.count()).where(*redeemed)
                          .group_by(func.extract("isodow", local))).all())
    gross, commission = int(pay[1]), int(pay[2])
    return StatsOut(
        days=days, currency=market.currency, visits=visits, unique_customers=customers, credits_used=int(pay[0]),
        gross_minor=gross, commission_minor=commission, net_minor=gross - commission, pending_valuation=int(pay[3]),
        upcoming_bookings=upcoming, cancellations=cancellations, late_cancellations=int(pay[4]),
        no_shows=int(pay[5]), surcharged_visits=int(adjusted[0]), discounted_visits=int(adjusted[1]),
        weeks=[WeekPoint(week_start=w.date().isoformat(), visits=n, gross_minor=int(g)) for w, n, g in weeks],
        top_offers=[TopOffer(title=t, visits=n, credits=int(c)) for t, n, c in top],
        weekdays=[int(dow.get(d, 0)) for d in range(1, 8)],
    )
