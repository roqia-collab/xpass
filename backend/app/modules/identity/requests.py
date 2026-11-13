"""Formulaire public, puis mot de passe choisi par l'admin (RH) ou par le RH (commerçant)."""
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.catalog.models import City, Market, Merchant
from app.modules.catalog.onboarding import slugify
from app.modules.identity.models import AccessRequest, Membership, User
from app.modules.identity.passwords import check_password, set_login_password
from app.modules.notifications.service import Mail, send
from app.modules.ops.service import OpsError, create_rh_service, grant_access


def _gmail(value: str) -> str:
    email = (value or "").strip().lower()
    domain = email.split("@")[-1] if "@" in email else ""
    if "@" not in email or "." not in domain or len(email) > 254 or domain not in ("gmail.com", "googlemail.com"):
        raise OpsError("gmail_required", "Indiquez une adresse Gmail (@gmail.com).", 422)
    return email


def _clip(value: str, limit: int, label: str) -> str:
    text_value = " ".join((value or "").split())
    if len(text_value) < 2 or len(text_value) > limit:
        raise OpsError("invalid_field", f"{label} : entre 2 et {limit} caractères.", 422)
    return text_value


def submit_request(db: Session, *, kind: str, gmail: str, full_name: str, place_name: str, city: str, message: str) -> AccessRequest:
    if kind not in ("rh", "merchant"):
        raise OpsError("invalid_kind", "Choisissez un service RH ou un commerçant.", 422)
    email = _gmail(gmail)
    pending = db.scalar(select(AccessRequest.id).where(AccessRequest.gmail == email, AccessRequest.status == "pending"))
    if pending is not None:
        raise OpsError("already_pending", "Une demande est déjà en cours pour cette adresse Gmail.", 409)
    row = AccessRequest(
        kind=kind,
        gmail=email,
        full_name=_clip(full_name, 120, "Le nom"),
        place_name=_clip(place_name, 160, "Le nom du service ou de l'établissement"),
        city=_clip(city, 80, "La ville"),
        message=(message or "").strip()[:1000],
        status="pending",
    )
    db.add(row)
    db.flush()
    return row


def notify_admin(db: Session, row: AccessRequest) -> None:
    """E-mail d'alerte, sans mot de passe. La demande reste visible même si l'e-mail ne part pas."""
    settings = get_settings()
    if not settings.smtp_host:
        return
    admin = db.scalar(
        select(User.email)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.role == "platform_admin", User.deleted_at.is_(None), User.is_active.is_(True))
        .limit(1)
    )
    if not admin:
        return
    kind = "Service RH" if row.kind == "rh" else "Commerçant"
    base = settings.portals_public_url.rstrip("/")
    link = f"{base}/admin/demandes" if "localhost" in base or "127.0.0.1" in base else f"{base.replace('://', '://admin.', 1)}/admin/demandes"
    try:
        send(Mail(
            to=admin,
            subject=f"XPASS — nouvelle demande {kind}",
            body=(
                f"Une personne a rempli le formulaire d'accès.\n\n"
                f"Type : {kind}\n"
                f"Nom : {row.full_name}\n"
                f"Gmail : {row.gmail}\n"
                f"Lieu : {row.place_name}\n"
                f"Ville : {row.city}\n"
                f"Message : {row.message or '—'}\n\n"
                f"Ouvrez {link} pour accepter "
                f"et choisir le mot de passe. Le mot de passe n'est pas dans cet e-mail : "
                f"vous le choisissez, puis vous le donnez à la personne."
            ),
        ))
    except Exception:
        return


def create_gmail_admin(db: Session, *, gmail: str, full_name: str, password: str) -> User:
    """Un administrateur déjà en place ouvre un autre admin. L'identifiant est le Gmail."""
    email = _gmail(gmail)
    name = _clip(full_name, 120, "Le nom")
    set_login_password(email=email, password=password, display_name=name)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, display_name=name, is_active=True, is_demo=False)
        db.add(user)
        db.flush()
    elif user.deleted_at is not None or not user.is_active:
        raise OpsError("account_closed", "Ce compte est fermé.", 409)
    else:
        user.display_name = name
    exists = db.scalar(select(Membership.id).where(
        Membership.user_id == user.id, Membership.role == "platform_admin", Membership.scope_type == "platform",
    ))
    if exists is None:
        db.add(Membership(user_id=user.id, scope_type="platform", scope_id=None, role="platform_admin"))
        db.flush()
    return user


def list_admins(db: Session) -> list[User]:
    return list(db.scalars(
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.role == "platform_admin", User.deleted_at.is_(None))
        .order_by(User.created_at)
    ))


def list_requests(db: Session) -> list[AccessRequest]:
    return list(db.scalars(select(AccessRequest).order_by(AccessRequest.created_at.desc()).limit(80)))


def _name(db: Session, email: str, full_name: str) -> None:
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        user.display_name = full_name[:120]


def _ensure_paris(db: Session) -> None:
    market_id = db.scalar(select(Market.id).where(Market.code == "FR"))
    if market_id is None:
        market = Market(code="FR", name="France", country_code="FR", currency="EUR", timezone="Europe/Paris", default_locale="fr-FR")
        db.add(market)
        db.flush()
        market_id = market.id
    opened = db.scalar(select(City.id).where(City.opened.is_(True)))
    if opened is not None:
        return
    db.execute(text("UPDATE cities SET opened = true WHERE slug = 'paris' AND opened = false"))
    db.execute(
        text(
            "INSERT INTO cities (id, market_id, slug, name, center, opened) "
            "SELECT gen_random_uuid(), :mid, 'paris', 'Paris', ST_GeogFromText('POINT(2.3522 48.8566)'), true "
            "WHERE NOT EXISTS (SELECT 1 FROM cities WHERE slug = 'paris')"
        ),
        {"mid": market_id},
    )


def _accept_merchant(db: Session, row: AccessRequest, actor_id: uuid.UUID) -> None:
    market_id = db.scalar(select(Market.id).where(Market.code == "FR"))
    if market_id is None:
        raise OpsError("market_missing", "Le marché France n'est pas prêt.", 503)
    merchant = Merchant(
        market_id=market_id,
        legal_name=row.place_name[:160],
        display_name=row.place_name[:120],
        commercial_status="approved",
        psp_status="not_started",
        city_label=row.city[:80],
        is_demo=False,
    )
    db.add(merchant)
    db.flush()
    try:
        grant_access(
            db, email=row.gmail, scope_type="merchant", scope_id=merchant.id, role="merchant_owner",
            by=actor_id, actor_kind="operator",
        )
    except OpsError as exc:
        if exc.code != "already_granted":
            raise


def accept_request(db: Session, request_id: uuid.UUID, *, password: str, actor_id: uuid.UUID, actor_name: str | None) -> AccessRequest:
    row = db.scalar(select(AccessRequest).where(AccessRequest.id == request_id).with_for_update())
    if row is None:
        raise OpsError("not_found", "Demande introuvable.", 404)
    if row.status != "pending":
        raise OpsError("already_decided", "Cette demande a déjà été traitée.", 409)
    password = check_password(password)
    set_login_password(email=row.gmail, password=password, display_name=row.full_name)
    if row.kind == "rh":
        if slugify(row.city) == "paris":
            _ensure_paris(db)
        try:
            create_rh_service(db, name=row.place_name, city_label=row.city, hr_email=row.gmail, by=actor_id, by_name=actor_name)
        except OpsError as exc:
            if exc.code != "already_granted":
                raise
    else:
        _accept_merchant(db, row, actor_id)
    _name(db, row.gmail, row.full_name)
    row.status = "accepted"
    row.decided_by = actor_id
    row.decided_at = datetime.now(UTC)
    db.flush()
    return row


def refuse_request(db: Session, request_id: uuid.UUID, *, actor_id: uuid.UUID) -> AccessRequest:
    row = db.scalar(select(AccessRequest).where(AccessRequest.id == request_id).with_for_update())
    if row is None:
        raise OpsError("not_found", "Demande introuvable.", 404)
    if row.status != "pending":
        raise OpsError("already_decided", "Cette demande a déjà été traitée.", 409)
    row.status = "refused"
    row.decided_by = actor_id
    row.decided_at = datetime.now(UTC)
    db.flush()
    return row


def set_password_for_member(db: Session, *, email: str, password: str, merchant_org_ids: list[uuid.UUID] | None) -> None:
    """L'admin fixe le mot de passe d'un RH ou d'un commerçant. Le RH ne le fixe que pour ses commerçants."""
    email = (email or "").strip().lower()
    user = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None), User.is_active.is_(True)))
    if user is None:
        raise OpsError("unknown_account", "Aucun compte n'existe encore pour cette adresse.", 404)
    if merchant_org_ids is not None:
        owned = db.scalar(
            select(Merchant.id)
            .join(Membership, Membership.scope_id == Merchant.id)
            .where(
                Membership.user_id == user.id,
                Membership.scope_type == "merchant",
                Membership.role == "merchant_owner",
                Merchant.organization_id.in_(merchant_org_ids),
            )
        )
        if owned is None:
            raise OpsError("not_yours", "Ce commerçant n'appartient pas à votre service.", 404)
    set_login_password(email=email, password=password, display_name=user.display_name)
