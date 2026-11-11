"""Chaîne Admin → RH → commerçant → application client.

Le service RH crée un commerçant déjà validé. Son établissement et sa première prestation
sont publiés : le catalogue client les affiche tout de suite.
"""
import uuid
from dataclasses import dataclass
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog import management, onboarding
from app.modules.catalog.management import OfferInput
from app.modules.catalog.models import Category, Location, Market, Merchant, Offer, OfferVersion
from app.modules.employer.models import EmployerContract
from app.modules.identity.models import Membership, Organization, User
from app.modules.ops.service import audit, grant_access

COVERS = {
    "sport": "demo/heroes/sport.jpg",
    "culture": "demo/heroes/culture.jpg",
    "beaute": "demo/heroes/beaute.jpg",
    "divertissement": "demo/heroes/divertissement.jpg",
}


@dataclass
class MerchantDraft:
    display_name: str
    owner_email: str
    location_name: str
    subcategory_slug: str
    address_line: str
    postal_code: str
    city: str
    description: str
    price_credits: int


def create_merchant_for_org(db: Session, org: Organization, actor: User, data: MerchantDraft) -> Merchant:
    display = (data.display_name or "").strip()
    venue = (data.location_name or "").strip()
    if len(display) < 2 or len(venue) < 2:
        raise onboarding.OnboardingError("invalid_name", "Indiquez le nom du commerçant et celui de l'établissement.")
    if not 1 <= data.price_credits <= 500:
        raise onboarding.OnboardingError("invalid_price", "Le prix doit être compris entre 1 et 500 crédits.")

    sub = onboarding._subcategory(db, data.subcategory_slug)
    place = onboarding._geocode(data.address_line, data.postal_code, data.city)
    market = db.get(Market, org.market_id)
    if market is None:
        raise onboarding.OnboardingError("market_missing", "Marché introuvable.", 503)
    city = onboarding._city(db, market, place)
    if not city.opened:
        raise onboarding.OnboardingError(
            "city_closed",
            "Cette ville n'est pas encore ouverte. Le réseau démarre à Paris : les prestations n'apparaissent "
            "dans l'application que pour une ville déjà ouverte.",
            409,
        )
    merchant = Merchant(
        market_id=market.id,
        organization_id=org.id,
        legal_name=display[:160],
        display_name=display[:120],
        commercial_status="approved",
        psp_status="not_started",
        city_label=city.name,
        is_demo=False,
    )
    db.add(merchant)
    db.flush()
    location = onboarding._new_location(db, merchant, city, sub, place, _location_view(data, sub.name))
    location.status = "published"
    cat_slug = db.scalar(select(Category.slug).where(Category.id == sub.category_id))
    location.cover_image_key = COVERS.get(cat_slug or "", "demo/heroes/sport.jpg")
    db.flush()
    contract = db.scalar(select(EmployerContract).where(EmployerContract.organization_id == org.id))
    management.create_offer(
        db, location, booking_mode="open_access", publish=True,
        data=OfferInput(
            title=location.name[:120],
            summary=(data.description or location.kind_label)[:240],
            duration_min=60,
            price_credits=data.price_credits,
            participants_min=1,
            participants_max=1,
            capacity=12,
            free_cancellation_hours=contract.free_cancellation_hours if contract else 24,
            resource_ids=[],
        ),
    )
    management.replace_hours(
        db, location,
        [(day, time(9, 0), time(19, 0)) for day in range(6)],
    )
    grant_access(
        db, email=data.owner_email, scope_type="merchant", scope_id=merchant.id, role="merchant_owner",
        by=actor.id, actor_kind="hr", by_name=actor.display_name,
    )
    audit(
        db, actor_kind="hr", actor_user_id=actor.id, action="merchant.created_by_hr", object_type="merchant",
        object_id=merchant.id, object_label=merchant.display_name,
        details={"organization_id": str(org.id), "location": location.name, "published": True},
    )
    return merchant


def preview_address(address_line: str, postal_code: str, city: str) -> dict:
    """Adresse officielle (Base Adresse Nationale) avant de créer ou modifier."""
    place = onboarding._geocode(address_line, postal_code, city)
    return {
        "label": place.label,
        "address_line": onboarding._address_line(place, address_line),
        "postal_code": place.postal_code,
        "city": place.city,
        "district": place.district or "",
        "latitude": place.latitude,
        "longitude": place.longitude,
    }


def _owned(db: Session, org: Organization, merchant_id: uuid.UUID) -> Merchant:
    merchant = db.get(Merchant, merchant_id)
    if merchant is None or merchant.organization_id != org.id:
        raise onboarding.OnboardingError("merchant_not_found", "Ce commerçant n'appartient pas à votre service RH.", 404)
    return merchant


def update_merchant_for_org(db: Session, org: Organization, actor: User, merchant_id: uuid.UUID, data: MerchantDraft) -> Merchant:
    merchant = _owned(db, org, merchant_id)
    location = db.scalar(select(Location).where(Location.merchant_id == merchant.id).order_by(Location.name))
    if location is None:
        raise onboarding.OnboardingError("location_missing", "Aucun établissement à modifier.")
    if not 1 <= data.price_credits <= 500:
        raise onboarding.OnboardingError("invalid_price", "Le prix doit être compris entre 1 et 500 crédits.")
    sub = onboarding._subcategory(db, data.subcategory_slug)
    place = onboarding._geocode(data.address_line, data.postal_code, data.city)
    market = db.get(Market, org.market_id)
    if market is None:
        raise onboarding.OnboardingError("market_missing", "Marché introuvable.", 503)
    city = onboarding._city(db, market, place)
    if not city.opened:
        raise onboarding.OnboardingError(
            "city_closed",
            "Cette ville n'est pas encore ouverte. Le réseau démarre à Paris.",
            409,
        )
    display = data.display_name.strip()
    venue = data.location_name.strip()
    merchant.display_name = display[:120]
    merchant.legal_name = display[:160]
    merchant.city_label = city.name
    location.name = venue[:120]
    location.subcategory_id = sub.id
    location.city_id = city.id
    location.description = (data.description or "").strip()[:2000]
    location.address_line = onboarding._address_line(place, data.address_line)
    location.postal_code = place.postal_code[:12]
    location.district_label = (place.district or city.name)[:40]
    location.geo = onboarding._point(place.latitude, place.longitude)
    offer = db.scalar(select(Offer).where(Offer.location_id == location.id).order_by(Offer.sort_order))
    if offer is not None and offer.current_version_id is not None:
        version = db.get(OfferVersion, offer.current_version_id)
        if version is not None:
            version.title = location.name[:120]
            version.summary = (location.description or location.kind_label)[:240]
            version.price_credits = data.price_credits
    audit(
        db, actor_kind="hr", actor_user_id=actor.id, action="merchant.updated_by_hr", object_type="merchant",
        object_id=merchant.id, object_label=merchant.display_name,
        details={"location": location.name, "address": location.address_line},
    )
    return merchant


def set_visibility(db: Session, org: Organization, actor: User, merchant_id: uuid.UUID, published: bool) -> Merchant:
    merchant = _owned(db, org, merchant_id)
    status = "published" if published else "hidden"
    for location in db.scalars(select(Location).where(Location.merchant_id == merchant.id)).all():
        location.status = status
    audit(
        db, actor_kind="hr", actor_user_id=actor.id,
        action="merchant.published_by_hr" if published else "merchant.hidden_by_hr",
        object_type="merchant", object_id=merchant.id, object_label=merchant.display_name,
        details={"status": status},
    )
    return merchant


def list_for_org(db: Session, org_id: uuid.UUID) -> list[dict]:
    merchants = db.scalars(
        select(Merchant).where(Merchant.organization_id == org_id).order_by(Merchant.display_name)
    ).all()
    if not merchants:
        return []
    ids = [m.id for m in merchants]
    venues = db.scalars(select(Location).where(Location.merchant_id.in_(ids)).order_by(Location.name)).all()
    owners = dict(db.execute(
        select(Membership.scope_id, User.email)
        .join(User, User.id == Membership.user_id)
        .where(Membership.scope_type == "merchant", Membership.role == "merchant_owner", Membership.scope_id.in_(ids))
    ).all())
    by_merchant: dict[uuid.UUID, list[Location]] = {}
    for loc in venues:
        by_merchant.setdefault(loc.merchant_id, []).append(loc)
    prices = dict(db.execute(
        select(Offer.location_id, OfferVersion.price_credits)
        .join(OfferVersion, OfferVersion.id == Offer.current_version_id)
        .where(Offer.location_id.in_([loc.id for loc in venues]))
    ).all()) if venues else {}
    return [
        {
            "id": m.id,
            "display_name": m.display_name,
            "city_label": m.city_label,
            "commercial_status": m.commercial_status,
            "owner_email": owners.get(m.id),
            "venues": [
                {
                    "id": loc.id,
                    "name": loc.name,
                    "slug": loc.slug,
                    "status": loc.status,
                    "address_line": loc.address_line,
                    "postal_code": loc.postal_code,
                    "district_label": loc.district_label,
                    "description": loc.description,
                    "cover_image_key": loc.cover_image_key,
                    "price_credits": prices.get(loc.id),
                    "subcategory_slug": loc.subcategory.slug if loc.subcategory else "",
                }
                for loc in by_merchant.get(m.id, [])
            ],
        }
        for m in merchants
    ]


def _location_view(data: MerchantDraft, kind: str):
    return type("Loc", (), {
        "location_name": data.location_name,
        "kind_label": kind,
        "description": (data.description or "").strip()[:2000],
        "address_line": data.address_line,
    })()
