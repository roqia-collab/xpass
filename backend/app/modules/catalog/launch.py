"""Réseau de lancement : Paris d'abord.

Une autre ville s'ouvre seulement quand un salarié peut déjà réserver à Paris,
qu'une entreprise a payé, que Stripe est en mode réel et qu'un commerçant
peut recevoir un versement (commission déduite).
"""
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.catalog.models import City, Location, Merchant, Offer
from app.modules.catalog.onboarding import slugify
from app.modules.employer.models import EmployerInvoice
from app.modules.ops.service import OpsError, audit

PARIS = "paris"
MIN_VENUES = 15
MIN_PAID_COMPANIES = 1


class LaunchError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        self.code, self.message, self.status = code, message, status


def stripe_mode() -> str:
    """live, test, sandbox ou absent. La clé n'est jamais renvoyée."""
    settings = get_settings()
    key = settings.psp_secret_key or ""
    if settings.psp_provider == "stripe" and key.startswith("sk_live_"):
        return "live"
    if settings.psp_provider == "stripe" and key.startswith("sk_test_"):
        return "test"
    return settings.psp_provider or "absent"


def _active_offer():
    return exists().where(
        Offer.location_id == Location.id,
        Offer.is_active.is_(True),
        Offer.current_version_id.is_not(None),
    )


def paris_venues(db: Session) -> int:
    return int(db.scalar(
        select(func.count(Location.id))
        .join(Merchant, Merchant.id == Location.merchant_id)
        .join(City, City.id == Location.city_id)
        .where(
            Location.is_demo.is_(False),
            Merchant.is_demo.is_(False),
            Location.status == "published",
            Merchant.commercial_status == "approved",
            City.slug == PARIS,
            _active_offer(),
        )
    ) or 0)


def paid_companies(db: Session) -> int:
    return int(db.scalar(
        select(func.count(func.distinct(EmployerInvoice.organization_id))).where(
            EmployerInvoice.status == "paid",
            EmployerInvoice.is_demo.is_(False),
        )
    ) or 0)


def payout_accounts(db: Session) -> int:
    return int(db.scalar(
        select(func.count(Merchant.id)).where(
            Merchant.is_demo.is_(False),
            Merchant.psp_status == "verified",
            Merchant.psp_account_id.is_not(None),
            ~Merchant.psp_account_id.like("acct_demo%"),
        )
    ) or 0)


def network_is_real(db: Session) -> bool:
    return paris_venues(db) >= MIN_VENUES


def blockers(db: Session) -> list[str]:
    missing: list[str] = []
    venues = paris_venues(db)
    if venues < MIN_VENUES:
        missing.append(
            f"Paris compte {venues} établissement(s) publié(s) avec une prestation active, il en faut {MIN_VENUES}."
        )
    paid = paid_companies(db)
    if paid < MIN_PAID_COMPANIES:
        missing.append(
            "Aucune entreprise n'a encore réglé une facture. Les crédits n'apparaissent dans l'application "
            "qu'une fois le paiement confirmé."
        )
    if stripe_mode() != "live":
        missing.append("Stripe est encore en test : les factures et les versements ne déplacent pas d'argent.")
    if payout_accounts(db) < 1:
        missing.append(
            "Aucun commerçant n'a de compte de versement vérifié. La commission XPASS est déduite du virement, "
            "qui ne part pas sans ce compte."
        )
    return missing


def status(db: Session) -> dict:
    venues = paris_venues(db)
    return {
        "city": "Paris",
        "venues": venues,
        "venues_target": MIN_VENUES,
        "paid_companies": paid_companies(db),
        "companies_target": 2,
        "payout_accounts": payout_accounts(db),
        "stripe_mode": stripe_mode(),
        "demo_hidden": network_is_real(db),
        "second_city_allowed": not blockers(db),
        "lawyer_validated": False,
    }


def require_opened_label(db: Session, city_label: str) -> str:
    label = (city_label or "Paris").strip() or "Paris"
    city = db.scalar(select(City).where(City.slug == slugify(label), City.opened.is_(True)))
    if city is None:
        opened = list(db.scalars(select(City.name).where(City.opened.is_(True)).order_by(City.name)))
        names = ", ".join(opened) or "Paris"
        raise LaunchError(
            "city_closed",
            f"Seule {names} est ouverte. Une autre ville s'ouvre quand le réseau parisien a vraiment démarré.",
        )
    return city.name


def open_city(db: Session, slug: str, *, by, reason: str) -> City:
    missing = blockers(db)
    if missing:
        raise LaunchError("network_not_ready", " ".join(missing))
    city = db.scalar(select(City).where(City.slug == slugify(slug)))
    if city is None:
        raise LaunchError("city_unknown", "Cette ville n'est pas dans le référentiel.", 404)
    city.opened = True
    db.flush()
    audit(
        db, actor_kind="operator", actor_user_id=by, action="city.opened", object_type="city",
        object_id=city.id, object_label=city.name, reason=reason,
    )
    return city
