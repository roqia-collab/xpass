"""Lecture pour les portails commerçant, RH et administration."""
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import CurrentPrincipal, DbSession, forbidden
from app.modules.catalog import repository, service
from app.modules.booking.models import Booking
from app.modules.catalog.models import COMMERCIAL_STATUS, Location, Market, Merchant, OfferVersion, Resource
from app.modules.catalog.schemas import LocationDetailOut
from app.modules.identity.models import Membership, Organization, User

router = APIRouter()


# ---------- Commerçant ----------


class AffiliationOut(BaseModel):
    organization_name: str | None
    published_locations: int


@router.get("/partner/affiliation", response_model=AffiliationOut, tags=["commerçant"])
def partner_affiliation(principal: CurrentPrincipal, db: DbSession,
                        location_id: uuid.UUID | None = None) -> AffiliationOut:
    """Service RH qui a créé ce commerçant, et nombre d'établissements visibles dans l'application."""
    merchant_ids = principal.scope_ids("merchant", ("merchant_owner", "merchant_staff"))
    if not merchant_ids:
        raise forbidden("Ce compte n'est rattaché à aucun établissement.")
    merchant = None
    if location_id is not None:
        loc = db.get(Location, location_id)
        if loc is not None and loc.merchant_id in merchant_ids:
            merchant = db.get(Merchant, loc.merchant_id)
    if merchant is None:
        merchant = db.get(Merchant, merchant_ids[0])
    org = db.get(Organization, merchant.organization_id) if merchant and merchant.organization_id else None
    published = 0
    if merchant is not None:
        published = db.scalar(select(func.count()).select_from(Location).where(
            Location.merchant_id == merchant.id, Location.status == "published")) or 0
    return AffiliationOut(organization_name=org.name if org else None, published_locations=int(published))


@router.get("/partner/locations", response_model=list[LocationDetailOut], tags=["commerçant"])
def partner_locations(principal: CurrentPrincipal, db: DbSession) -> list[LocationDetailOut]:
    merchant_ids = principal.scope_ids("merchant", ("merchant_owner", "merchant_staff"))
    if not merchant_ids:
        raise forbidden("Ce compte n'est rattaché à aucun établissement.")
    rows = repository.list_merchant_locations(db, merchant_ids)
    return [service.location_detail(loc, lat, lng, include_inactive=True) for loc, lat, lng in rows]


class PartnerBookingOut(BaseModel):
    id: uuid.UUID
    status: str
    location_id: uuid.UUID
    offer_title: str
    resource_id: uuid.UUID | None
    resource_name: str | None
    customer_name: str
    party_size: int
    total_credits: int
    # Prix figé à la réservation et ajustements appliqués (peak, demand, last_minute).
    price_credits_per_person: int = 0
    price_adjustments: list[str] = []
    starts_at: datetime
    ends_at: datetime
    local_start: str
    local_end: str


@router.get("/partner/bookings", response_model=list[PartnerBookingOut], tags=["commerçant"])
def partner_bookings(
    principal: CurrentPrincipal,
    db: DbSession,
    day: Annotated[date | None, Query(alias="date")] = None,
    days: Annotated[int, Query(ge=1, le=7)] = 1,
):
    """Réservations (réserves, confirmées, consommées) d'un jour ou d'une semaine (`days`), heures du lieu."""
    merchant_ids = principal.scope_ids("merchant", ("merchant_owner", "merchant_staff"))
    if not merchant_ids:
        raise forbidden("Ce compte n'est rattaché à aucun établissement.")
    rows = db.execute(
        select(Booking, OfferVersion.title, Resource.name, User.display_name, Market.timezone)
        .join(Location, Location.id == Booking.location_id)
        .join(Merchant, Merchant.id == Location.merchant_id)
        .join(Market, Market.id == Merchant.market_id)
        .join(OfferVersion, OfferVersion.id == Booking.offer_version_id)
        .join(User, User.id == Booking.user_id)
        .outerjoin(Resource, Resource.id == Booking.resource_id)
        .where(
            Location.merchant_id.in_(merchant_ids),
            Booking.status.in_(("held", "confirmed", "redeemed", "no_show")),
            # Fenêtre large en UTC, affinée ci-dessous dans le fuseau du marché.
            *(
                [Booking.starts_at >= datetime.combine(day, time.min, UTC) - timedelta(days=1),
                 Booking.starts_at < datetime.combine(day, time.min, UTC) + timedelta(days=days + 1)]
                if day else []
            ),
        )
        .order_by(Booking.starts_at)
    ).all()
    out = []
    for b, title, resource_name, customer, tz in rows:
        zone = ZoneInfo(tz)
        local_start = b.starts_at.astimezone(zone)
        if day is not None and not (day <= local_start.date() < day + timedelta(days=days)):
            continue
        out.append(
            PartnerBookingOut(
                id=b.id, status=b.status, location_id=b.location_id, offer_title=title, resource_id=b.resource_id,
                resource_name=resource_name, customer_name=customer, party_size=b.party_size,
                total_credits=b.total_credits, price_credits_per_person=b.price_credits_per_person,
                price_adjustments=list(b.price_adjustments or []), starts_at=b.starts_at, ends_at=b.ends_at,
                local_start=local_start.replace(tzinfo=None).isoformat(timespec="minutes"),
                local_end=b.ends_at.astimezone(zone).replace(tzinfo=None).isoformat(timespec="minutes"),
            )
        )
    return out


# ---------- Administration ----------


class MerchantAdminOut(BaseModel):
    id: uuid.UUID
    display_name: str
    legal_name: str
    city_label: str
    market_code: str
    commercial_status: str
    psp_status: str
    location_count: int
    is_demo: bool
    created_at: datetime


class MerchantStatsOut(BaseModel):
    by_commercial_status: dict[str, int]
    items: list[MerchantAdminOut]


@router.get("/admin/merchants", response_model=MerchantStatsOut, tags=["administration"])
def admin_merchants(principal: CurrentPrincipal, db: DbSession, status: str | None = None) -> MerchantStatsOut:
    if not principal.has_platform_role("platform_admin", "platform_operator"):
        raise forbidden()
    if status is not None and status not in COMMERCIAL_STATUS:
        status = None
    rows = repository.list_merchants(db, status)
    all_rows = rows if status is None else repository.list_merchants(db)
    counts = {s: 0 for s in COMMERCIAL_STATUS}
    for m, _ in all_rows:
        counts[m.commercial_status] += 1
    return MerchantStatsOut(
        by_commercial_status=counts,
        items=[
            MerchantAdminOut(
                id=m.id,
                display_name=m.display_name,
                legal_name=m.legal_name,
                city_label=m.city_label,
                market_code=m.market.code,
                commercial_status=m.commercial_status,
                psp_status=m.psp_status,
                location_count=n,
                is_demo=m.is_demo,
                created_at=m.created_at,
            )
            for m, n in rows
        ],
    )


# ---------- Entreprise / RH ----------


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    sector_label: str | None
    city_label: str | None
    hr_member_count: int
    is_demo: bool


@router.get("/company/organization", response_model=OrganizationOut, tags=["entreprise"])
def company_organization(principal: CurrentPrincipal, db: DbSession) -> OrganizationOut:
    org_ids = principal.scope_ids("organization", ("hr_admin", "hr_viewer"))
    if not org_ids:
        raise forbidden("Ce compte n'est rattaché à aucune organisation.")
    org = db.get(Organization, org_ids[0])
    assert org is not None
    hr_count = db.scalar(
        select(func.count()).select_from(Membership).where(
            Membership.scope_type == "organization", Membership.scope_id == org.id
        )
    )
    return OrganizationOut(
        id=org.id,
        name=org.name,
        sector_label=org.sector_label,
        city_label=org.city_label,
        hr_member_count=hr_count or 0,
        is_demo=org.is_demo,
    )
