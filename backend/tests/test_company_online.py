"""Entreprises : paiement en ligne des factures (bac à sable / Stripe) et synchronisation RH par clé d'API."""
import uuid

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.employer.models import Employee, EmployerInvoice, OrganizationApiKey
from app.modules.payments.provider import StripeProvider
from tests.conftest import login
from tests.test_payments import process_all


def _invoice(client, hr) -> str:
    r = client.post("/api/v1/company/invoices", headers=hr, json={"amount_minor": 12_000})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_invoice_paid_online_through_signed_webhook(client):
    hr = login(client, "rh@xpass.demo")
    inv = _invoice(client, hr)
    r = client.post(f"/api/v1/company/invoices/{inv}/pay", headers=hr)
    assert r.status_code == 200, r.text
    assert f"/payments/sandbox/invoice/{inv}" in r.json()["url"]
    page = client.get(f"/api/v1/payments/sandbox/invoice/{inv}?retour=http://localhost:3000/company/factures")
    assert page.status_code == 200 and "aucun argent" in page.text
    done = client.post(f"/api/v1/payments/sandbox/invoice/{inv}/pay", data={"retour": "http://localhost:3000/company/factures"},
                       follow_redirects=False)
    assert done.status_code == 303 and "paiement=retour" in done.headers["location"]
    process_all()
    with SessionLocal() as db:
        assert db.get(EmployerInvoice, uuid.UUID(inv)).status == "paid"
    # Plus payable ; personne d'autre ne peut lancer le paiement.
    assert client.post(f"/api/v1/company/invoices/{inv}/pay", headers=hr).status_code == 409
    other = _invoice(client, hr)
    assert client.post(f"/api/v1/company/invoices/{other}/pay", headers=login(client, "partenaire@xpass.demo")).status_code == 403


def test_stripe_invoice_checkout_parameters(monkeypatch):
    calls = []
    monkeypatch.setattr(StripeProvider, "_post", lambda self, path, data, idempotency_key: calls.append((path, data, idempotency_key))
                        or {"id": "cs_1", "url": "https://checkout.stripe.com/c/pay/cs_1"})
    iid = uuid.uuid4()
    c = StripeProvider("sk_test_x").create_invoice_checkout(invoice_id=iid, reference="FAC-1", amount_minor=12_000,
                                                             currency="EUR", customer_email="rh@exemple.fr",
                                                             return_url="https://pro.exemple.fr/company/factures")
    path, data, key = calls[0]
    assert c.url.startswith("https://checkout.stripe.com/") and path == "/checkout/sessions" and data["mode"] == "payment"
    assert "payment_method_types[0]" not in data and data["line_items[0][price_data][unit_amount]"] == "12000"
    assert data["metadata[xpass_invoice_id]"] == str(iid) and key == f"invoice-checkout-{iid}"


def test_stripe_change_plan_and_cancel_parameters(monkeypatch):
    gets, posts, deletes = [], [], []
    monkeypatch.setattr(StripeProvider, "_get", lambda self, path, params=None: gets.append((path, params)) or {
        "items": {"data": [{"id": "si_1", "price": {"id": "price_old"}}]}
    })
    monkeypatch.setattr(StripeProvider, "_post", lambda self, path, data, idempotency_key: posts.append((path, data)) or {})
    monkeypatch.setattr(StripeProvider, "_delete", lambda self, path: deletes.append(path) or {"id": "sub_1", "status": "canceled"})
    p = StripeProvider("sk_test_x")
    p.change_subscription_price("sub_1", "price_new")
    assert gets[0][0] == "/subscriptions/sub_1" and gets[0][1]["expand[]"] == "items.data"
    assert posts[0][0] == "/subscriptions/sub_1" and posts[0][1]["items[0][price]"] == "price_new"
    p.cancel_subscription("sub_1")
    assert deletes == ["/subscriptions/sub_1"]


def test_hr_sync_with_api_key(client):
    hr = login(client, "rh@xpass.demo")
    created = client.post("/api/v1/company/api-keys", headers=hr, json={"label": "Logiciel RH"})
    assert created.status_code == 201, created.text
    raw, key_id = created.json()["key"], created.json()["id"]
    assert raw.startswith("xph_")
    with SessionLocal() as db:  # seule l'empreinte est conservée
        assert db.scalar(select(OrganizationApiKey.key_hash).where(OrganizationApiKey.id == uuid.UUID(key_id))) != raw
    assert all("key" not in k for k in client.get("/api/v1/company/api-keys", headers=hr).json())

    auth = {"Authorization": f"Bearer {raw}"}
    a, b = f"sync-{uuid.uuid4().hex[:6]}@exemple.fr", f"sync-{uuid.uuid4().hex[:6]}@exemple.fr"
    body = {"employees": [{"email": a, "first_name": "Alix", "last_name": "Martin"},
                          {"email": b.upper(), "first_name": "Bo", "last_name": "Durand"},
                          {"email": "pas-un-email", "first_name": "X", "last_name": "Y"}]}
    dry = client.put("/api/v1/hr-sync/employees?dry_run=true", headers=auth, json=body).json()
    assert dry["invited"] == 2 and dry["skipped"][0]["reason"] == "adresse invalide"
    with SessionLocal() as db:
        assert db.scalar(select(Employee.id).where(Employee.email == a)) is None  # simulation : rien d'écrit
    assert client.put("/api/v1/hr-sync/employees", headers=auth, json=body).json()["invited"] == 2
    # Renommage puis retrait des absents.
    body2 = {"employees": [{"email": a, "first_name": "Alix", "last_name": "Martin-Roy"}], "remove_missing": True}
    r = client.put("/api/v1/hr-sync/employees", headers=auth, json=body2).json()
    assert r["updated"] == 1 and r["removed"] >= 1
    with SessionLocal() as db:
        assert db.scalar(select(Employee.status).where(Employee.email == b)) == "removed"
    # Clé révoquée ou fausse : refus.
    assert client.post(f"/api/v1/company/api-keys/{key_id}/revoke", headers=hr).status_code == 200
    assert client.put("/api/v1/hr-sync/employees", headers=auth, json=body2).status_code == 401
    assert client.put("/api/v1/hr-sync/employees", headers={"Authorization": "Bearer xph_faux"}, json=body2).status_code == 401
