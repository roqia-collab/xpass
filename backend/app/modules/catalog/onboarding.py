"""Inscription d'un commerçant réel : entreprise (SIRET vérifié), premier établissement (adresse géocodée).

Parcours : la personne a un compte XPASS (e-mail vérifié) → elle dépose sa candidature → XPASS crée le
partenaire « à vérifier », l'établissement en brouillon (invisible des clients) et lui donne le rôle de
responsable. L'équipe XPASS valide ensuite le dossier puis publie l'établissement (lot 7).
"""
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalog.models import City, Location, LocationChangeRequest, Market, Merchant, Subcategory
from app.modules.directory import service as directory
from app.modules.identity.models import Membership, User
from app.modules.ops.service import audit
from app.modules.platform.service import emit

OPEN_STATUSES = ("draft", "pending_review", "documents_missing")


class OnboardingError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


@dataclass
class Application:
    siret: str
    display_name: str
    contact_phone: str
    location_name: str
    subcategory_slug: str
    kind_label: str
    address_line: str
    postal_code: str
    city: str
    description: str


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:100] or "lieu"


def _point(lat: float, lng: float) -> str:
    return f"SRID=4326;POINT({lng} {lat})"


def check_company(siret: str) -> tuple[directory.Company | None, dict]:
    """Contrôle SIRET : format, puis annuaire. Retourne l'entreprise et le résultat à conserver."""
    siret = directory.normalize_siret(siret)
    if not directory.siret_is_valid(siret):
        raise OnboardingError("invalid_siret", "Le SIRET doit comporter 14 chiffres valides.")
    try:
        company = directory.lookup_siret(siret)
    except directory.ServiceUnavailable:
        return None, {"status": "unavailable"}
    if company is None:
        raise OnboardingError("siret_not_found", "Ce SIRET est introuvable dans l'annuaire des entreprises.")
    if not company.active:
        raise OnboardingError("siret_closed", "Cet établissement est fermé selon l'annuaire des entreprises.")
    return company, {"status": "verified", **company.as_dict()}


def _city(db: Session, market: Market, place: directory.Place) -> City:
    name = re.sub(r"\s+\d+(er|e)?\s+Arrondissement$", "", place.city, flags=re.I).strip() or place.city
    slug = slugify(name)
    city = db.scalar(select(City).where(City.market_id == market.id, City.slug == slug))
    if city is None:
        city = City(market_id=market.id, slug=slug, name=name[:80], center=_point(place.latitude, place.longitude))
        db.add(city)
        db.flush()
    return city


def _unique_slug(db: Session, base: str) -> str:
    slug, n = base, 2
    while db.scalar(select(Location.id).where(Location.slug == slug)) is not None:
        slug, n = f"{base}-{n}", n + 1
    return slug


def _subcategory(db: Session, slug: str) -> Subcategory:
    sub = db.scalar(select(Subcategory).where(Subcategory.slug == slug))
    if sub is None:
        raise OnboardingError("invalid_subcategory", "Choisissez une activité dans la liste.")
    return sub


def _geocode(address_line: str, postal_code: str, city: str) -> directory.Place:
    try:
        place = directory.geocode(address_line, postal_code, city)
    except directory.ServiceUnavailable as exc:
        raise OnboardingError("geocoder_unavailable",
                              "Le service d'adresses ne répond pas. Réessayez dans quelques minutes.", 503) from exc
    if place is None:
        raise OnboardingError("address_not_found",
                              "Adresse introuvable dans la Base Adresse Nationale : vérifiez le numéro, la rue et le code postal.")
    return place


def _address_line(place: directory.Place, typed: str) -> str:
    return (" ".join(x for x in (place.housenumber, place.street) if x) or typed.strip())[:200]


def _new_location(db: Session, merchant: Merchant, city: City, sub: Subcategory, place: directory.Place, data) -> Location:
    location = Location(
        merchant_id=merchant.id,
        city_id=city.id,
        subcategory_id=sub.id,
        slug=_unique_slug(db, slugify(f"{data.location_name}-{city.name}")),
        name=data.location_name.strip()[:120],
        kind_label=(data.kind_label.strip() or sub.name)[:80],
        description=data.description.strip()[:2000],
        address_line=_address_line(place, data.address_line),
        postal_code=place.postal_code[:12],
        district_label=directory.district_label(place.postal_code, place.city),
        geo=_point(place.latitude, place.longitude),
        geocode_label=place.label[:200],
        geocode_score=round(place.score, 3),
        status="draft",  # invisible des clients jusqu'à la validation et la publication par XPASS
        is_demo=False,
    )
    db.add(location)
    db.flush()
    return location


def apply(db: Session, user: User, data: Application, now: datetime | None = None) -> Merchant:
    now = now or datetime.now(UTC)
    if user.is_demo or not user.is_active or user.deleted_at is not None:
        raise OnboardingError("account_not_allowed", "Ce compte ne peut pas déposer de candidature.", 403)
    pending = db.scalar(
        select(func.count()).select_from(Membership).join(Merchant, Merchant.id == Membership.scope_id)
        .where(Membership.user_id == user.id, Membership.scope_type == "merchant",
               Merchant.commercial_status.in_(OPEN_STATUSES)))
    if pending:
        raise OnboardingError("application_pending", "Vous avez déjà un dossier en cours de validation.", 409)

    siret = directory.normalize_siret(data.siret)
    if db.scalar(select(Merchant.id).where(Merchant.siret == siret)) is not None:
        raise OnboardingError("siret_taken", "Ce SIRET est déjà inscrit sur XPASS. Contactez l'équipe XPASS.", 409)
    company, check = check_company(siret)

    sub = _subcategory(db, data.subcategory_slug)
    place = _geocode(data.address_line, data.postal_code, data.city)

    market = db.scalar(select(Market).where(Market.code == "FR"))
    city = _city(db, market, place)
    display = data.display_name.strip() or (company.trade_name if company else "") or data.location_name.strip()
    merchant = Merchant(
        market_id=market.id,
        legal_name=(company.legal_name if company else display)[:160],
        display_name=display[:120],
        commercial_status="pending_review",
        psp_status="not_started",
        city_label=city.name,
        is_demo=False,
        siret=siret,
        siren=company.siren if company else siret[:9],
        contact_phone=data.contact_phone.strip()[:30] or None,
        company_check=check,
        company_checked_at=now,
    )
    db.add(merchant)
    db.flush()
    location = _new_location(db, merchant, city, sub, place, data)
    db.add(Membership(user_id=user.id, scope_type="merchant", scope_id=merchant.id, role="merchant_owner"))
    db.flush()
    audit(db, actor_kind="partner", actor_user_id=user.id, action="merchant.applied", object_type="merchant",
          object_id=merchant.id, object_label=merchant.display_name,
          details={"siret": siret, "annuaire": check["status"], "adresse": place.label, "score": round(place.score, 3)})
    emit(db, "merchant", merchant.id, "merchant.applied", {"user_id": str(user.id), "location": location.name})
    return merchant


# ---------------------------------------------------------------- établissements supplémentaires


@dataclass
class LocationData:
    location_name: str
    subcategory_slug: str
    kind_label: str
    address_line: str
    postal_code: str
    city: str
    description: str


def add_location(db: Session, user: User, merchant: Merchant, data: LocationData) -> Location:
    """Nouvel établissement d'un commerçant existant : brouillon, publié par XPASS après relecture."""
    if merchant.commercial_status == "suspended":
        raise OnboardingError("merchant_suspended", "Compte partenaire suspendu : contactez l'équipe XPASS.", 409)
    sub = _subcategory(db, data.subcategory_slug)
    place = _geocode(data.address_line, data.postal_code, data.city)
    city = _city(db, db.get(Market, merchant.market_id), place)
    location = _new_location(db, merchant, city, sub, place, data)
    audit(db, actor_kind="partner", actor_user_id=user.id, action="location.created", object_type="location",
          object_id=location.id, object_label=location.name, details={"adresse": place.label, "score": round(place.score, 3)})
    emit(db, "location", location.id, "location.created", {"merchant_id": str(merchant.id)})
    return location


# ---------------------------------------------------------------- demandes de modification


@dataclass
class ChangeData:
    name: str
    subcategory_slug: str
    kind_label: str
    address_line: str
    postal_code: str
    city: str


def request_change(db: Session, user: User, location: Location, data: ChangeData) -> LocationChangeRequest:
    """Calcule les champs réellement modifiés ; une adresse est géocodée tout de suite (erreur immédiate)."""
    if db.scalar(select(LocationChangeRequest.id).where(LocationChangeRequest.location_id == location.id,
                                                        LocationChangeRequest.status == "pending")):
        raise OnboardingError("change_pending", "Une demande de modification est déjà en cours pour cet établissement.", 409)
    changes: dict = {}
    if data.name.strip() and data.name.strip() != location.name:
        changes["name"] = data.name.strip()[:120]
    if data.subcategory_slug and data.subcategory_slug != location.subcategory.slug:
        sub = _subcategory(db, data.subcategory_slug)
        changes["subcategory"] = {"id": str(sub.id), "slug": sub.slug, "name": sub.name}
    if data.kind_label.strip() and data.kind_label.strip() != location.kind_label:
        changes["kind_label"] = data.kind_label.strip()[:80]
    moved = (data.address_line.strip().lower() != location.address_line.lower()
             or data.postal_code.strip() != location.postal_code)
    if data.address_line.strip() and moved:
        place = _geocode(data.address_line, data.postal_code, data.city)
        changes["address"] = {
            "address_line": _address_line(place, data.address_line), "postal_code": place.postal_code[:12],
            "city": place.city, "district_label": directory.district_label(place.postal_code, place.city),
            "latitude": place.latitude, "longitude": place.longitude, "label": place.label[:200],
            "score": round(place.score, 3),
            "previous": f"{location.address_line}, {location.postal_code}",
        }
    if not changes:
        raise OnboardingError("no_change", "Aucune modification par rapport à la fiche actuelle.")
    req = LocationChangeRequest(location_id=location.id, requested_by=user.id, changes=changes, status="pending")
    db.add(req)
    db.flush()
    audit(db, actor_kind="partner", actor_user_id=user.id, action="location.change_requested", object_type="location",
          object_id=location.id, object_label=location.name, details={"fields": sorted(changes)})
    return req


def decide_change(db: Session, *, request_id: uuid.UUID, approve: bool, reason: str, by: uuid.UUID,
                  now: datetime | None = None) -> LocationChangeRequest:
    from app.modules.ops.service import _reason

    reason = _reason(reason)
    req = db.scalar(select(LocationChangeRequest).where(LocationChangeRequest.id == request_id).with_for_update())
    if req is None:
        raise OnboardingError("change_not_found", "Demande introuvable.", 404)
    if req.status != "pending":
        raise OnboardingError("change_decided", "Cette demande a déjà été traitée.", 409)
    location = db.get(Location, req.location_id)
    if approve:
        c = req.changes
        if "name" in c:
            location.name = c["name"]
        if "kind_label" in c:
            location.kind_label = c["kind_label"]
        if "subcategory" in c:
            location.subcategory_id = uuid.UUID(c["subcategory"]["id"])
        if "address" in c:
            a = c["address"]
            place = directory.Place(label=a["label"], latitude=a["latitude"], longitude=a["longitude"], score=a["score"],
                                    housenumber=None, street=None, postal_code=a["postal_code"], city=a["city"], district=None)
            location.city_id = _city(db, db.get(Market, location.merchant.market_id), place).id
            location.address_line, location.postal_code = a["address_line"], a["postal_code"]
            location.district_label = a["district_label"]
            location.geo = _point(a["latitude"], a["longitude"])
            location.geocode_label, location.geocode_score = a["label"], a["score"]
    req.status = "approved" if approve else "rejected"
    req.decision_reason, req.decided_by, req.decided_at = reason, by, now or datetime.now(UTC)
    audit(db, actor_kind="operator", actor_user_id=by, action="location.change_approved" if approve else "location.change_rejected",
          object_type="location", object_id=location.id, object_label=location.name, reason=reason,
          details={"fields": sorted(req.changes)})
    emit(db, "location_change", req.id, "location.change_decided", {"approved": approve})
    db.flush()
    return req


def new_media_key(merchant_id: uuid.UUID) -> str:
    return f"merchants/{merchant_id}/{uuid.uuid4().hex}.jpg"
