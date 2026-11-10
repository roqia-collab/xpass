"""Équipe gérée par le commerçant : invitations par e-mail, rôles, retraits et garde-fous."""
import uuid

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.identity.models import User
from app.modules.notifications.service import build
from app.modules.ops.models import AuditEvent
from app.modules.platform.models import OutboxEvent
from tests.conftest import login


def _owner(client) -> tuple[dict, str]:
    h = login(client, "partenaire@xpass.demo")
    location_id = client.get("/api/v1/partner/locations", headers=h).json()[0]["id"]
    return h, location_id


def _as_demo(email: str) -> None:
    """Connexion de test : la connexion sans mot de passe n'accepte que les comptes marqués démo."""
    with SessionLocal() as db, db.begin():
        db.scalar(select(User).where(User.email == email)).is_demo = True


def test_owner_invites_and_removes_staff(client):
    h, loc = _owner(client)
    email = f"equipe-{uuid.uuid4().hex[:8]}@exemple.fr"
    r = client.post(f"/api/v1/partner/locations/{loc}/access", headers=h, json={"email": email, "role": "merchant_staff"})
    assert r.status_code == 201, r.text
    membership_id = r.json()["id"]

    rows = client.get(f"/api/v1/partner/locations/{loc}/access", headers=h).json()
    me = next(x for x in rows if x["is_you"])
    assert me["role"] == "merchant_owner"
    row = next(x for x in rows if x["email"] == email)
    assert row["role"] == "merchant_staff" and row["linked"] is False

    # L'e-mail nomme la personne qui invite ; le geste est tracé comme venant du partenaire.
    with SessionLocal() as db:
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "access.granted",
                                                    OutboxEvent.aggregate_id == uuid.UUID(membership_id)))
        mail = build(db, event)
        assert "Partenaire Démo" in mail.body and "http" not in mail.body
        assert db.scalar(select(AuditEvent.actor_kind).where(AuditEvent.action == "access.granted",
                                                             AuditEvent.details["email"].astext == email)) == "partner"

    # Le collaborateur voit le portail (lecture, scanner) mais ne gère ni l'équipe ni le catalogue.
    _as_demo(email)
    staff = login(client, email)
    assert client.get("/api/v1/partner/locations", headers=staff).status_code == 200
    assert client.get(f"/api/v1/partner/locations/{loc}/access", headers=staff).status_code == 403
    assert client.post(f"/api/v1/partner/locations/{loc}/access", headers=staff,
                       json={"email": "autre@exemple.fr", "role": "merchant_staff"}).status_code == 403

    assert client.post(f"/api/v1/partner/locations/{loc}/access/{membership_id}/revoke", headers=h).status_code == 200
    assert client.get("/api/v1/partner/locations", headers=staff).status_code == 403


def test_team_guards(client):
    h, loc = _owner(client)
    rows = client.get(f"/api/v1/partner/locations/{loc}/access", headers=h).json()
    me = next(x for x in rows if x["is_you"])
    # Pas de retrait de son propre accès, ni du dernier responsable.
    r = client.post(f"/api/v1/partner/locations/{loc}/access/{me['id']}/revoke", headers=h)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "own_access"
    # Rôle hors commerçant refusé ; doublon refusé.
    assert client.post(f"/api/v1/partner/locations/{loc}/access", headers=h,
                       json={"email": "rh@exemple.fr", "role": "hr_admin"}).status_code == 422
    email = f"co-{uuid.uuid4().hex[:8]}@exemple.fr"
    assert client.post(f"/api/v1/partner/locations/{loc}/access", headers=h,
                       json={"email": email, "role": "merchant_owner"}).status_code == 201
    assert client.post(f"/api/v1/partner/locations/{loc}/access", headers=h,
                       json={"email": email, "role": "merchant_owner"}).status_code == 409
    # Un accès d'un autre commerçant n'est pas visible ni retirable d'ici.
    admin = login(client, "admin@xpass.demo")
    others = client.get("/api/v1/admin/organizations", headers=admin).json()
    hr = client.get(f"/api/v1/admin/access?scope_type=organization&scope_id={others[0]['id']}", headers=admin).json()
    if hr:
        assert client.post(f"/api/v1/partner/locations/{loc}/access/{hr[0]['id']}/revoke", headers=h).status_code == 404
    # Un autre commerçant n'accède pas à cette équipe.
    assert client.get(f"/api/v1/partner/locations/{loc}/access", headers=login(client, "client@xpass.demo")).status_code == 403
