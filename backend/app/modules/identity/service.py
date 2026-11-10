import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.security import TokenClaims
from app.modules.catalog.models import Merchant
from app.modules.identity.models import Membership, Organization, User


@dataclass
class Principal:
    user: User

    def scope_ids(self, scope_type: str, roles: tuple[str, ...] | None = None) -> list[uuid.UUID]:
        return [
            m.scope_id
            for m in self.user.memberships
            if m.scope_type == scope_type and m.scope_id is not None and (roles is None or m.role in roles)
        ]

    def has_platform_role(self, *roles: str) -> bool:
        return any(m.scope_type == "platform" and m.role in roles for m in self.user.memberships)


def _load_user(db: Session, **where) -> User | None:
    stmt = select(User).options(selectinload(User.memberships)).filter_by(**where)
    return db.scalar(stmt)


def resolve_principal(db: Session, claims: TokenClaims) -> Principal | None:
    if claims.is_dev:
        try:
            user = _load_user(db, id=uuid.UUID(claims.subject))
        except ValueError:
            return None
    else:
        user = _load_user(db, oidc_subject=claims.subject) or _link_or_create(db, claims)
    if user is None or not user.is_active:
        return None
    return Principal(user=user)


def _link_or_create(db: Session, claims: TokenClaims) -> User | None:
    """Première connexion OIDC.

    Seule une adresse e-mail VÉRIFIÉE par le fournisseur permet de relier un compte existant (créé par une
    invitation RH, un rattachement commerçant ou les données de démonstration) ; sinon, aucun compte n'est
    créé et l'API répond 401 jusqu'à la vérification. Un compte déjà relié à un autre sujet n'est jamais repris.
    """
    if not claims.email or not claims.email_verified:
        return None
    existing = _load_user(db, email=claims.email)
    if existing is not None:
        if existing.oidc_subject and existing.oidc_subject != claims.subject:
            return None
        existing.oidc_subject = claims.subject
        db.commit()
        return _load_user(db, id=existing.id)
    user = User(email=claims.email, display_name=(claims.name or claims.email.split("@")[0])[:120],
                oidc_subject=claims.subject, is_active=True, is_demo=False)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # deux premières requêtes simultanées : l'autre a créé le compte
        db.rollback()
        return _load_user(db, oidc_subject=claims.subject)
    return _load_user(db, id=user.id)


def find_demo_user(db: Session, email: str) -> User | None:
    return _load_user(db, email=email.lower(), is_demo=True)


def describe_memberships(db: Session, memberships: list[Membership]) -> list[dict]:
    """Ajoute le nom lisible de chaque portée (marchand, organisation)."""
    merchant_ids = [m.scope_id for m in memberships if m.scope_type == "merchant"]
    org_ids = [m.scope_id for m in memberships if m.scope_type == "organization"]
    names: dict[uuid.UUID, str] = {}
    if merchant_ids:
        names |= {i: n for i, n in db.execute(select(Merchant.id, Merchant.display_name).where(Merchant.id.in_(merchant_ids)))}
    if org_ids:
        names |= {i: n for i, n in db.execute(select(Organization.id, Organization.name).where(Organization.id.in_(org_ids)))}
    return [
        {
            "scope_type": m.scope_type,
            "scope_id": m.scope_id,
            "scope_name": names.get(m.scope_id, "XPASS") if m.scope_id else "XPASS",
            "role": m.role,
        }
        for m in memberships
    ]
