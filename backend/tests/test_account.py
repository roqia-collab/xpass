"""Lot 8a : connexion OIDC (liaison des comptes), profil, export, suppression, assistance, e-mails."""
import json
import time
import urllib.request
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select, text

from app.core import security
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.identity.models import User
from app.modules.notifications import service as notifications
from app.modules.platform.models import OutboxEvent
from tests.conftest import login
from tests.test_bookings import COUPE, free_slot, hold, make_customer, post

ISSUER = "http://idp.test/realms/xpass"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _Jwks:
    def get_signing_key_from_jwt(self, token):
        return type("K", (), {"key": KEY.public_key()})()


@pytest.fixture
def oidc(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "oidc_issuer", ISSUER)
    monkeypatch.setattr(s, "oidc_audience", "xpass-api")
    monkeypatch.setattr(s, "oidc_jwks_url", "http://idp.test/certs")
    monkeypatch.setattr(security, "_jwks_client", lambda url: _Jwks())

    def token(sub: str, email: str | None, verified: bool = True, aud: str = "xpass-api", ttl: int = 300, **extra):
        now = int(time.time())
        claims = {"sub": sub, "iss": ISSUER, "aud": aud, "iat": now, "exp": now + ttl, "email": email,
                  "email_verified": verified, "name": "Nina Test", **extra}
        return {"Authorization": f"Bearer {jwt.encode(claims, KEY, algorithm='RS256')}"}

    return token


# ---------------------------------------------------------------- OIDC


def test_oidc_first_login_creates_customer_once(client, oidc):
    email, sub = f"nina-{uuid.uuid4().hex[:8]}@exemple.fr", str(uuid.uuid4())
    h = oidc(sub, email)
    me = client.get("/api/v1/me", headers=h).json()
    assert me["email"] == email and me["display_name"] == "Nina Test" and me["email_verified"] is True
    assert client.get("/api/v1/me", headers=h).json()["id"] == me["id"]
    with SessionLocal() as db:
        assert db.scalar(text("SELECT count(*) FROM users WHERE email = :e"), {"e": email}) == 1


def test_oidc_requires_verified_email_valid_audience_and_freshness(client, oidc):
    email = f"x-{uuid.uuid4().hex[:8]}@exemple.fr"
    assert client.get("/api/v1/me", headers=oidc(str(uuid.uuid4()), email, verified=False)).status_code == 401
    assert client.get("/api/v1/me", headers=oidc(str(uuid.uuid4()), email, aud="autre")).status_code == 401
    assert client.get("/api/v1/me", headers=oidc(str(uuid.uuid4()), email, ttl=-60)).status_code == 401
    forged = jwt.encode({"sub": "x", "iss": ISSUER, "aud": "xpass-api", "exp": int(time.time()) + 60,
                         "email": email, "email_verified": True},
                        rsa.generate_private_key(public_exponent=65537, key_size=2048), algorithm="RS256")
    assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_oidc_links_existing_account_by_verified_email_only_once(client, oidc):
    """Un salarié invité ou un commerçant créé avant sa première connexion retrouve son compte."""
    email = make_customer(personal=12)
    sub = str(uuid.uuid4())
    me = client.get("/api/v1/me", headers=oidc(sub, email)).json()
    with SessionLocal() as db:
        assert str(db.scalar(select(User.id).where(User.email == email))) == me["id"]
    assert client.get("/api/v1/wallet", headers=oidc(sub, email)).json()["available"] == 12
    # Un autre sujet (autre compte chez le fournisseur) ne peut pas reprendre ce compte.
    assert client.get("/api/v1/me", headers=oidc(str(uuid.uuid4()), email)).status_code == 401


# ---------------------------------------------------------------- profil, export, suppression


def test_notifications_inbox_lists_confirmed_booking(client):
    h = login(client, make_customer(personal=40))
    assert client.get("/api/v1/me/notifications", headers=h).json() == []
    oid = COUPE()
    held = hold(client, h, oid, free_slot(client, oid)).json()
    post(client, h, f"/api/v1/bookings/{held['id']}/confirm")
    inbox = client.get("/api/v1/me/notifications", headers=h).json()
    assert inbox and inbox[0]["kind"] == "booking.confirmed"
    assert inbox[0]["route"] == f"/reservations/{held['id']}"
    assert "Réservation confirmée" in inbox[0]["title"]


def test_profile_preferences(client):
    h = login(client, make_customer())
    r = client.patch("/api/v1/me", json={"display_name": "Camille M.", "locale": "en", "notify_email": False}, headers=h)
    assert r.json() == {"display_name": "Camille M.", "locale": "en", "notify_email": False}
    assert client.patch("/api/v1/me", json={"locale": "de"}, headers=h).status_code == 422
    me = client.get("/api/v1/me", headers=h).json()
    assert (me["locale"], me["notify_email"], me["email_verified"]) == ("en", False, False)


def test_export_contains_my_data_only(client):
    h = login(client, make_customer(personal=40))
    oid = COUPE()
    hold(client, h, oid, free_slot(client, oid))
    r = client.get("/api/v1/me/export", headers=h)
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert data["account"]["email"].endswith("@xpass.demo")
    assert len(data["bookings"]) == 1 and data["bookings"][0]["offer"] == "Coupe et coiffage"
    assert data["credit_lots"][0]["granted_credits"] == 40


def test_account_deletion(client):
    email = make_customer(personal=40)
    h = login(client, email)
    oid = COUPE()
    b = hold(client, h, oid, free_slot(client, oid)).json()
    post(client, h, f"/api/v1/bookings/{b['id']}/confirm")
    assert client.post("/api/v1/me/delete", json={"confirm": "oui"}, headers=h).status_code == 422
    r = client.post("/api/v1/me/delete", json={"confirm": "SUPPRIMER"}, headers=h)
    assert r.json()["detail"]["code"] == "has_bookings"
    post(client, h, f"/api/v1/bookings/{b['id']}/cancel")
    assert client.post("/api/v1/me/delete", json={"confirm": "SUPPRIMER"}, headers=h).json() == {"deleted": True}
    assert client.get("/api/v1/me", headers=h).status_code == 401
    with SessionLocal() as db:
        assert db.scalar(select(func_count()).where(User.email == email)) == 0
        # Le journal financier est conservé, sans identité.
        assert db.scalar(text("SELECT count(*) FROM bookings WHERE id = :b"), {"b": b["id"]}) == 1
    assert client.post("/api/v1/me/delete", json={"confirm": "SUPPRIMER"},
                       headers=login(client, "partenaire@xpass.demo")).json()["detail"]["code"] == "has_roles"


def func_count():
    from sqlalchemy import func

    return func.count(User.id)


# ---------------------------------------------------------------- assistance


def test_support_request_and_operator_reply(client):
    h = login(client, make_customer())
    assert client.post("/api/v1/me/support", json={"category": "credits", "subject": "?", "message": "court"},
                       headers=h).status_code == 422
    r = client.post("/api/v1/me/support", json={"category": "credits", "subject": "Crédits manquants",
                                                "message": "Mes crédits employeur ne sont pas arrivés."}, headers=h)
    assert r.status_code == 201 and r.json()["reference"].startswith("S-")
    other = login(client, make_customer())
    assert client.get("/api/v1/me/support", headers=other).json() == []
    assert client.get("/api/v1/admin/support", headers=h).status_code == 403
    admin = login(client, "admin@xpass.demo")
    req = next(x for x in client.get("/api/v1/admin/support", headers=admin).json() if x["id"] == r.json()["id"])
    assert req["customer_email"].endswith("@xpass.demo")
    assert client.post(f"/api/v1/admin/support/{req['id']}/reply", json={"reply": "Ils arrivent dès le virement de "
                                                                          "votre employeur.", "close": True},
                       headers=admin).json() == {"status": "closed"}
    mine = client.get("/api/v1/me/support", headers=h).json()[0]
    assert mine["status"] == "closed" and mine["reply"].startswith("Ils arrivent")
    with SessionLocal() as db:
        ev = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "support.answered",
                                                 OutboxEvent.aggregate_id == uuid.UUID(req["id"])))
        mail = notifications.build(db, ev)
    assert mail.subject == f"Réponse à votre demande {req['reference']}" and "Ils arrivent" in mail.body


# ---------------------------------------------------------------- e-mails


def test_mail_respects_preferences_and_never_contains_qr(client):
    h = login(client, make_customer(personal=40))
    oid = COUPE()
    b = hold(client, h, oid, free_slot(client, oid)).json()
    post(client, h, f"/api/v1/bookings/{b['id']}/confirm")
    client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h)
    with SessionLocal() as db:
        ev = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "booking.confirmed",
                                                 OutboxEvent.aggregate_id == uuid.UUID(b["id"])))
        mail = notifications.build(db, ev)
        assert "est confirmée" in mail.body and "18 crédits" in mail.body and "XPASS1" not in mail.body
    client.patch("/api/v1/me", json={"notify_email": False}, headers=h)
    with SessionLocal() as db:
        ev = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "booking.confirmed",
                                                 OutboxEvent.aggregate_id == uuid.UUID(b["id"])))
        assert notifications.build(db, ev) is None


def _mailpit_messages() -> list[dict]:
    with urllib.request.urlopen("http://mailpit:8025/api/v1/messages", timeout=3) as r:
        return json.load(r)["messages"]


def test_real_smtp_delivery_to_mailpit(monkeypatch):
    try:
        _mailpit_messages()
    except OSError:
        pytest.skip("Mailpit indisponible (tests hors docker compose)")
    s = get_settings()
    monkeypatch.setattr(s, "smtp_host", "mailpit")
    monkeypatch.setattr(s, "smtp_port", 1025)
    monkeypatch.setattr(s, "smtp_starttls", False)
    subject = f"Test XPASS {uuid.uuid4().hex[:6]}"
    notifications.send(notifications.Mail("destinataire@exemple.fr", subject, "Corps du message"))
    assert any(m["Subject"] == subject for m in _mailpit_messages())
