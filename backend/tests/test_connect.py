"""Compte de versement du commerçant (Stripe Connect) : ouverture, page du prestataire, statut par webhook signé."""
import uuid

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.catalog.models import Merchant
from app.modules.ops.models import AuditEvent
from app.modules.payments.provider import StripeProvider, sign
from tests.conftest import login
from tests.test_partners import application, real_user, services  # noqa: F401 (fixture)
from tests.test_payments import SECRET, _event, post_webhook, process_all


def _new_partner(client) -> tuple[dict, str]:
    h, _ = real_user()
    r = client.post("/api/v1/partners/applications", headers=h, json=application())
    assert r.status_code == 201, r.text
    return h, r.json()["merchant_id"]


def test_sandbox_onboarding_until_payouts_enabled(client, services):
    h, merchant_id = _new_partner(client)
    before = client.get("/api/v1/partner/settlements", headers=h).json()
    assert before["psp_status"] == "not_started" and not before["has_payout_account"] and before["psp_configured"]

    link = client.post("/api/v1/partner/payout-account/onboarding", headers=h)
    assert link.status_code == 200, link.text
    url = link.json()["url"]
    assert "/payments/sandbox/onboarding/acct_sbx_" in url
    with SessionLocal() as db:
        m = db.get(Merchant, uuid.UUID(merchant_id))
        assert m.psp_status == "pending" and m.psp_account_id.startswith("acct_sbx_")
        account = m.psp_account_id
        assert db.scalar(select(AuditEvent.id).where(AuditEvent.action == "merchant.payout_account_created",
                                                     AuditEvent.object_id == m.id))
    # Un second clic réutilise le même compte (pas de doublon chez le prestataire).
    client.post("/api/v1/partner/payout-account/onboarding", headers=h)
    with SessionLocal() as db:
        assert db.get(Merchant, uuid.UUID(merchant_id)).psp_account_id == account

    # Page du bac à sable puis validation : webhook signé account.updated, traité comme un vrai.
    page = client.get(f"/api/v1/payments/sandbox/onboarding/{account}?retour=http://localhost:3000/partner/reglements?versements=retour")
    assert page.status_code == 200 and "aucune donnée bancaire" in page.text
    done = client.post(f"/api/v1/payments/sandbox/onboarding/{account}/complete",
                       data={"retour": "https://ailleurs.example/vol"}, follow_redirects=False)
    assert done.status_code == 303 and done.headers["location"].startswith("http://localhost:3000/")  # pas de redirection ouverte
    process_all()
    after = client.get("/api/v1/partner/settlements", headers=h).json()
    assert after["psp_status"] == "verified" and after["payouts_enabled"]
    # Pas d'espace prestataire en bac à sable : refus explicite, jamais un faux lien.
    dash = client.post("/api/v1/partner/payout-account/dashboard", headers=h)
    assert dash.status_code == 409 and dash.json()["detail"]["code"] == "no_dashboard"


def test_payout_account_rules(client, services):
    h, merchant_id = _new_partner(client)
    # Avant vérification : pas d'espace prestataire.
    assert client.post("/api/v1/partner/payout-account/dashboard", headers=h).json()["detail"]["code"] == "account_not_ready"
    # Réservé au responsable.
    assert client.post("/api/v1/partner/payout-account/onboarding",
                       headers=login(client, "client@xpass.demo")).status_code == 403
    # Partenaire suspendu : pas d'ouverture.
    with SessionLocal() as db, db.begin():
        db.get(Merchant, uuid.UUID(merchant_id)).commercial_status = "suspended"
    r = client.post("/api/v1/partner/payout-account/onboarding", headers=h)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "merchant_not_allowed"
    # Webhook refusé du prestataire : statut « rejected », plus de lien proposé.
    with SessionLocal() as db, db.begin():
        m = db.get(Merchant, uuid.UUID(merchant_id))
        m.commercial_status, m.psp_account_id, m.psp_status = "approved", f"acct_sbx_{uuid.uuid4().hex[:16]}", "pending"
        account = m.psp_account_id
    body = _event("account.updated", {"id": account, "payouts_enabled": False, "charges_enabled": False,
                                      "requirements": {"disabled_reason": "rejected.fraud"}})
    assert post_webhook(client, body).status_code == 200
    process_all()
    assert client.get("/api/v1/partner/settlements", headers=h).json()["psp_status"] == "rejected"
    assert client.post("/api/v1/partner/payout-account/onboarding", headers=h).json()["detail"]["code"] == "psp_rejected"


def test_connect_webhook_secret_is_accepted(client, monkeypatch):
    """Les événements des comptes connectés arrivent sur un endpoint Stripe distinct, avec son propre secret."""
    monkeypatch.setenv("PSP_CONNECT_WEBHOOK_SECRET", "whsec_connect_0123456789abcdef")
    get_settings.cache_clear()
    try:
        body = _event("account.updated", {"id": "acct_inconnu", "payouts_enabled": True})
        assert post_webhook(client, body, sign("whsec_connect_0123456789abcdef", body)).status_code == 200
        assert post_webhook(client, _event("account.updated", {"id": "x"}), sign("mauvais-secret-0123456", body)).status_code == 400
    finally:
        monkeypatch.delenv("PSP_CONNECT_WEBHOOK_SECRET")
        get_settings.cache_clear()
    assert SECRET  # secret principal toujours utilisé par les autres tests


def test_stripe_requests(monkeypatch):
    """Paramètres envoyés à Stripe (sans appel réseau) : compte Express, lien d'inscription à usage unique."""
    calls = []

    def fake_post(self, path, data, idempotency_key):
        calls.append((path, data, idempotency_key))
        return {"id": "acct_123", "url": "https://connect.stripe.com/setup/e/acct_123/abc"}

    monkeypatch.setattr(StripeProvider, "_post", fake_post)
    p = StripeProvider("sk_test_x")
    mid = uuid.uuid4()
    assert p.create_connected_account(merchant_id=mid, email="gerant@exemple.fr", country="FR", business_name="Salon") == "acct_123"
    path, data, key = calls[0]
    assert path == "/accounts" and data["type"] == "express" and data["country"] == "FR"
    assert data["capabilities[transfers][requested]"] == "true" and data["metadata[xpass_merchant_id]"] == str(mid)
    assert key == f"account-{mid}"  # idempotent : un seul compte par commerçant
    url = p.onboarding_link(account_id="acct_123", refresh_url="http://localhost:3000/r", return_url="http://localhost:3000/ok")
    assert url.startswith("https://connect.stripe.com/")
    assert calls[1][0] == "/account_links" and calls[1][1]["type"] == "account_onboarding"
