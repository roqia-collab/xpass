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
from app.modules.catalog.models import Category, Location, Market, Merchant
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
            free_cancellation_hours=24,
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
    return [
        {
            "id": m.id,
            "display_name": m.display_name,
            "city_label": m.city_label,
            "commercial_status": m.commercial_status,
            "owner_email": owners.get(m.id),
            "venues": [
                {"id": loc.id, "name": loc.name, "slug": loc.slug, "status": loc.status}
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
