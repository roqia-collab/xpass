"""Gestion des comptes d'exploitation.

Usage :
    docker compose exec api python -m app.seed.accounts create-admin --email vous@exemple.fr --name "Prénom Nom"
    docker compose exec api python -m app.seed.accounts grant --email vous@exemple.fr --name "Prénom Nom"
    docker compose exec api python -m app.seed.accounts remove-demo

`create-admin` crée (ou promeut) un compte réel administrateur de la plateforme. Le mot de passe n'est jamais
géré ici : il se choisit sur la page sécurisée (fournisseur d'identité), puis la connexion relie le compte
par son adresse e-mail vérifiée.

`remove-demo` ferme les comptes de démonstration (`is_demo`) : réservations à venir annulées (crédits rendus
par le journal), accès professionnels retirés, données personnelles effacées. Les écritures financières sont
conservées sans identité, comme pour une suppression de compte demandée par un client.
"""
import sys
from datetime import UTC, datetime

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.modules.booking import service as booking_service
from app.modules.booking.models import ACTIVE_STATUSES, Booking
from app.modules.identity.account import delete_account
from app.modules.catalog.models import Market
from app.modules.identity.models import Membership, Organization, User
from app.modules.ops.service import OpsError, grant_access


def create_admin(db, email: str, name: str) -> User:
    email = email.strip().lower()
    if "@" not in email or len(name.strip()) < 2:
        raise SystemExit("Adresse e-mail ou nom invalide.")
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, display_name=name.strip(), is_demo=False)
        db.add(user)
        db.flush()
    elif user.deleted_at is not None or user.is_demo:
        raise SystemExit("Cette adresse appartient à un compte supprimé ou de démonstration.")
    has_role = db.scalar(select(Membership.id).where(
        Membership.user_id == user.id, Membership.scope_type == "platform", Membership.role == "platform_admin"))
    if has_role is None:
        db.add(Membership(user_id=user.id, scope_type="platform", scope_id=None, role="platform_admin"))
    db.flush()
    return user


def grant_spaces(db, email: str, name: str) -> User:
    """Administrateur plateforme + administrateur RH de l'entreprise Alystra."""
    user = create_admin(db, email, name)
    org = db.scalar(select(Organization).where(Organization.name == "Alystra"))
    if org is None:
        market_id = db.scalar(select(Market.id).where(Market.code == "FR"))
        if market_id is None:
            raise SystemExit("Marché FR introuvable. Lancez d'abord le seed de démonstration.")
        org = Organization(market_id=market_id, name="Alystra", sector_label="Services", city_label="Paris")
        db.add(org)
        db.flush()
    try:
        grant_access(db, email=user.email, scope_type="organization", scope_id=org.id, role="hr_admin",
                     by=user.id, actor_kind="operator", by_name=name)
    except OpsError as exc:
        if exc.code != "already_granted":
            raise
    return user


def remove_demo_accounts(db, now: datetime | None = None) -> list[str]:
    now = now or datetime.now(UTC)
    removed = []
    for user in db.scalars(select(User).where(User.is_demo.is_(True), User.deleted_at.is_(None))).all():
        upcoming = db.scalars(select(Booking.id).where(
            Booking.user_id == user.id, Booking.status.in_(ACTIVE_STATUSES), Booking.starts_at > now)).all()
        for booking_id in upcoming:
            booking_service.cancel(db, user_id=user.id, booking_id=booking_id, now=now)
        db.execute(delete(Membership).where(Membership.user_id == user.id))
        removed.append(user.email)
        delete_account(db, user, now=now)
    return removed


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("create-admin", "grant", "remove-demo"):
        print(__doc__)
        return 2
    with SessionLocal() as db, db.begin():
        if argv[0] in ("create-admin", "grant"):
            args = dict(zip(argv[1::2], argv[2::2]))
            if "--email" not in args or "--name" not in args:
                print("Précisez --email et --name.")
                return 2
            if argv[0] == "grant":
                user = grant_spaces(db, args["--email"], args["--name"])
                print(f"Admin et RH prêts : {user.email}. Connectez-vous avec Google sur les portails.")
            else:
                user = create_admin(db, args["--email"], args["--name"])
                print(f"Administrateur prêt : {user.email}. Choisissez le mot de passe sur la page sécurisée.")
        else:
            removed = remove_demo_accounts(db)
            print(f"{len(removed)} compte(s) de démonstration fermé(s) : {', '.join(removed) or 'aucun'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
