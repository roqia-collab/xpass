"""Accès commerçants et entreprises attribués par l'administration (rôles, audit, e-mail, retrait)."""
import uuid

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.catalog.models import Merchant
from app.modules.identity.models import Organization, User
from app.modules.notifications.service import build
from app.modules.ops.models import AuditEvent
from app.modules.platform.models import OutboxEvent
from tests.conftest import login


def _ids() -> tuple[str, str]:
    with SessionLocal() as db:
        merchant = db.scalar(select(Merchant.id).limit(1))
        org = db.scalar(select(Organization.id).limit(1))
        return str(merchant), str(org)


def test_admin_grants_merchant_access_to_new_email(client):
    admin = login(client, "admin@xpass.demo")
    merchant, _ = _ids()
    email = f"gerant-{uuid.uuid4().hex[:8]}@exemple.fr"

    r = client.post("/api/v1/admin/access", headers=admin,
                    json={"email": email.upper(), "scope_type": "merchant", "scope_id": merchant, "role": "merchant_owner"})
    assert r.status_code == 201, r.text
    membership_id = r.json()["id"]

    rows = client.get(f"/api/v1/admin/access?scope_type=merchant&scope_id={merchant}", headers=admin).json()
    row = next(x for x in rows if x["email"] == email)
    assert row["role"] == "merchant_owner" and row["linked"] is False

    # Le compte préparé accède à l'espace commerçant dès sa connexion (connexion de test : marqué démo ici).
    with SessionLocal() as db, db.begin():
        db.scalar(select(User).where(User.email == email)).is_demo = True
    assert client.get("/api/v1/partner/locations", headers=login(client, email)).status_code == 200

    # Doublon refusé, décision tracée, e-mail sans lien de connexion.
    again = client.post("/api/v1/admin/access", headers=admin,
                        json={"email": email, "scope_type": "merchant", "scope_id": merchant, "role": "merchant_owner"})
    assert again.status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(AuditEvent.id).where(AuditEvent.action == "access.granted",
                                                     AuditEvent.details["email"].astext == email))
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "access.granted",
                                                    OutboxEvent.aggregate_id == uuid.UUID(membership_id)))
        mail = build(db, event)
        assert mail.to == email and "Créer un compte" in mail.body and "http" not in mail.body

    assert client.post(f"/api/v1/admin/access/{membership_id}/revoke", headers=admin).status_code == 200
    assert client.get("/api/v1/partner/locations", headers=login(client, email)).status_code == 403


def test_access_rules(client):
    admin = login(client, "admin@xpass.demo")
    merchant, org = _ids()
    # Rôle incompatible avec l'espace, adresse invalide, espace inconnu.
    bad_role = {"email": "rh@exemple.fr", "scope_type": "organization", "scope_id": org, "role": "merchant_owner"}
    assert client.post("/api/v1/admin/access", headers=admin, json=bad_role).status_code == 422
    bad_mail = {"email": "pas-un-email", "scope_type": "organization", "scope_id": org, "role": "hr_admin"}
    assert client.post("/api/v1/admin/access", headers=admin, json=bad_mail).status_code == 422
    unknown = {"email": "x@exemple.fr", "scope_type": "merchant", "scope_id": str(uuid.uuid4()), "role": "merchant_staff"}
    assert client.post("/api/v1/admin/access", headers=admin, json=unknown).status_code == 404

    # Seul un administrateur attribue des accès ; un commerçant ne voit pas la liste.
    ok = {"email": f"rh-{uuid.uuid4().hex[:6]}@exemple.fr", "scope_type": "organization", "scope_id": org, "role": "hr_admin"}
    assert client.post("/api/v1/admin/access", headers=login(client, "partenaire@xpass.demo"), json=ok).status_code == 403
    assert client.get(f"/api/v1/admin/access?scope_type=merchant&scope_id={merchant}",
                      headers=login(client, "partenaire@xpass.demo")).status_code == 403
    assert client.post("/api/v1/admin/access", headers=admin, json=ok).status_code == 201
    orgs = client.get("/api/v1/admin/organizations", headers=admin).json()
    assert any(o["id"] == org and o["hr_accounts"] >= 2 for o in orgs)
