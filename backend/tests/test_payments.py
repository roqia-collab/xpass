"""Abonnements, webhooks signés et règlements partenaires (bac à sable, vrai PostgreSQL)."""
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import app
from app.modules.catalog.models import Location
from app.modules.payments import service as pay
from app.modules.payments.models import MoneyJournal, MoneyJournalLine, PaymentWebhookEvent
from app.modules.payments.provider import SandboxProvider, sign
from app.modules.settlement import service as settle
from tests.conftest import login
from tests.test_bookings import make_customer, wallet
from tests.test_redemption import confirmed_booking, redeem

SECRET = "whsec_test_0123456789abcdef"


def _event(event_type: str, obj: dict, event_id: str | None = None) -> bytes:
    return json.dumps({"id": event_id or f"evt_{uuid.uuid4().hex}", "type": event_type, "livemode": False,
                       "data": {"object": obj}}).encode()


def post_webhook(client, body: bytes, signature: str | None = None):
    return client.post("/api/v1/payments/webhooks/sandbox", content=body,
                       headers={"Stripe-Signature": signature if signature is not None else sign(SECRET, body),
                                "Content-Type": "application/json"})


def process_all() -> None:
    with SessionLocal() as db:
        pay.process_pending(db)


def subscribe(client) -> tuple[dict, str]:
    """Client abonné via le bac à sable ; retourne (en-têtes, id d'abonnement)."""
    h = login(client, make_customer())
    r = client.post("/api/v1/subscription/checkout", json={"plan_code": "essentiel"},
                    headers={**h, "Idempotency-Key": uuid.uuid4().hex})
    assert r.status_code == 201, r.text
    checkout_id = r.json()["checkout_url"].rsplit("/", 1)[1]
    assert client.post(f"/api/v1/payments/sandbox/checkout/{checkout_id}/pay", follow_redirects=False).status_code == 303
    process_all()
    with SessionLocal() as db:
        sub_id = db.scalar(text("SELECT id FROM subscriptions WHERE psp_checkout_id = :c"), {"c": checkout_id})
    return h, str(sub_id)


# ---------------------------------------------------------------- signature et persistance


def test_webhook_signature_is_required(client):
    body = _event("invoice.paid", {"id": "in_x"})
    assert post_webhook(client, body, signature="").status_code == 400
    assert post_webhook(client, body, signature=sign("mauvais-secret-000000", body)).status_code == 400
    stale = sign(SECRET, body, timestamp=int(time.time()) - 3600)
    assert post_webhook(client, body, signature=stale).status_code == 400
    # Corps modifié après signature.
    assert post_webhook(client, body + b" ", signature=sign(SECRET, body)).status_code == 400
    assert client.post("/api/v1/payments/webhooks/stripe", content=body,
                       headers={"Stripe-Signature": sign(SECRET, body)}).status_code == 400
    with SessionLocal() as db:
        assert db.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.payload["data"]["object"]["id"].astext == "in_x")) is None


def test_webhook_is_persisted_and_deduplicated(client):
    body = _event("ping.unknown", {"id": "obj_1"}, event_id=f"evt_dup_{uuid.uuid4().hex}")
    first, again = post_webhook(client, body).json(), post_webhook(client, body).json()
    assert (first["duplicate"], again["duplicate"]) == (False, True)
    event_id = json.loads(body)["id"]
    with SessionLocal() as db:
        assert db.scalar(text("SELECT count(*) FROM payment_webhook_events WHERE event_id = :e"), {"e": event_id}) == 1
    process_all()
    with SessionLocal() as db:
        assert db.scalar(text("SELECT outcome FROM payment_webhook_events WHERE event_id = :e"), {"e": event_id}) == "ignored"
        with pytest.raises(DBAPIError, match="ajout seul"):
            db.execute(text("DELETE FROM payment_webhook_events WHERE event_id = :e"), {"e": event_id})


# ---------------------------------------------------------------- abonnement


def test_checkout_grants_nothing_until_signed_invoice_is_processed(client):
    h = login(client, make_customer())
    r = client.post("/api/v1/subscription/checkout", json={"plan_code": "essentiel"},
                    headers={**h, "Idempotency-Key": uuid.uuid4().hex})
    checkout_id = r.json()["checkout_url"].rsplit("/", 1)[1]
    assert "aucun argent" in client.get(f"/api/v1/payments/sandbox/checkout/{checkout_id}").text
    # Retour navigateur « succès » : aucun effet.
    assert wallet(client, h)["available"] == 0
    client.post(f"/api/v1/payments/sandbox/checkout/{checkout_id}/pay", follow_redirects=False)
    # Webhooks persistés mais pas encore traités : toujours rien.
    assert wallet(client, h)["available"] == 0
    assert client.get("/api/v1/subscription", headers=h).json()["status"] is None
    process_all()
    w = wallet(client, h)
    assert w["available"] == 100 and w["by_source"]["personal"]["available"] == 100
    sub = client.get("/api/v1/subscription", headers=h).json()
    assert sub["status"] == "active" and sub["plan"]["code"] == "essentiel" and sub["sandbox"] is True
    assert [(i["amount_minor"], i["currency"], i["credits"], i["livemode"]) for i in sub["invoices"]] == [(10000, "EUR", 100, False)]
    # Page de paiement à usage unique.
    assert client.post(f"/api/v1/payments/sandbox/checkout/{checkout_id}/pay").status_code == 404


def test_one_credit_allocation_per_invoice(client):
    h, sub_id = subscribe(client)
    with SessionLocal() as db:
        psp_sub = db.scalar(text("SELECT psp_subscription_id FROM subscriptions WHERE id = :s"), {"s": sub_id})
    invoice = {"id": f"in_{uuid.uuid4().hex}", "subscription": psp_sub, "amount_paid": 10000, "currency": "eur",
               "lines": {"data": [{"period": {"start": int(time.time()), "end": int(time.time()) + 86400 * 30}}]}}
    # Même facture annoncée par deux événements différents (invoice.paid puis invoice.payment_succeeded).
    post_webhook(client, _event("invoice.paid", invoice))
    post_webhook(client, _event("invoice.payment_succeeded", invoice))
    process_all()
    assert wallet(client, h)["available"] == 200  # 100 initiaux + 100 de cette facture, une seule fois
    with SessionLocal() as db:
        assert db.scalar(text("SELECT count(*) FROM credit_lots WHERE origin_ref = :r"),
                         {"r": f"sandbox:{invoice['id']}"}) == 1


def test_concurrent_processing_applies_once(client):
    h, sub_id = subscribe(client)
    with SessionLocal() as db:
        psp_sub = db.scalar(text("SELECT psp_subscription_id FROM subscriptions WHERE id = :s"), {"s": sub_id})
    body = _event("invoice.paid", {"id": f"in_{uuid.uuid4().hex}", "subscription": psp_sub, "amount_paid": 10000,
                                   "currency": "eur"})
    post_webhook(client, body)
    with SessionLocal() as db:
        event_id = db.scalar(text("SELECT id FROM payment_webhook_events WHERE event_id = :e"),
                             {"e": json.loads(body)["id"]})
    barrier = Barrier(5)

    def run(_):
        barrier.wait()
        with SessionLocal() as db:
            return pay.process_event(db, event_id)

    with ThreadPoolExecutor(5) as pool:
        outcomes = list(pool.map(run, range(5)))
    assert outcomes.count("applied") == 1, outcomes
    assert wallet(client, h)["available"] == 200


def test_amount_mismatch_is_never_applied(client):
    h, sub_id = subscribe(client)
    with SessionLocal() as db:
        psp_sub = db.scalar(text("SELECT psp_subscription_id FROM subscriptions WHERE id = :s"), {"s": sub_id})
    body = _event("invoice.paid", {"id": f"in_{uuid.uuid4().hex}", "subscription": psp_sub, "amount_paid": 100,
                                   "currency": "eur"})
    post_webhook(client, body)
    process_all()
    process_all()
    assert wallet(client, h)["available"] == 100
    with SessionLocal() as db:
        row = db.execute(text("SELECT processed_at, attempts, last_error FROM payment_webhook_events WHERE event_id = :e"),
                         {"e": json.loads(body)["id"]}).one()
    assert row[0] is None and row[1] == pay.MAX_ATTEMPTS and "PaymentAnomaly" in row[2]


def test_event_for_unknown_subscription_is_retried_later(client):
    body = _event("invoice.paid", {"id": f"in_{uuid.uuid4().hex}", "subscription": "sub_inconnu", "amount_paid": 10000,
                                   "currency": "eur"})
    post_webhook(client, body)
    process_all()
    with SessionLocal() as db:
        row = db.execute(text("SELECT processed_at, attempts, last_error FROM payment_webhook_events WHERE event_id = :e"),
                         {"e": json.loads(body)["id"]}).one()
    assert row[0] is None and row[1] == 1 and "RetryLater" in row[2]


def test_auto_renew_and_single_live_subscription(client):
    h, _ = subscribe(client)
    again = client.post("/api/v1/subscription/checkout", json={"plan_code": "essentiel"},
                        headers={**h, "Idempotency-Key": uuid.uuid4().hex})
    assert again.status_code == 409 and again.json()["detail"]["code"] == "already_subscribed"
    off = client.post("/api/v1/subscription/auto-renew", json={"enabled": False}, headers=h).json()
    assert off["cancel_at_period_end"] is True and off["status"] == "active"
    on = client.post("/api/v1/subscription/auto-renew", json={"enabled": True}, headers=h).json()
    assert on["cancel_at_period_end"] is False


def test_checkout_other_plan_replaces_live_subscription(client):
    from tests.test_plans import _new_plan

    intense = _new_plan(client, login(client, "admin@xpass.demo"))
    h, sub_id = subscribe(client)
    r = client.post("/api/v1/subscription/checkout", json={"plan_code": intense["code"]},
                    headers={**h, "Idempotency-Key": uuid.uuid4().hex})
    assert r.status_code == 201 and r.json().get("checkout_url"), r.text
    with SessionLocal() as db:
        old = db.scalar(text("SELECT status FROM subscriptions WHERE id = :s"), {"s": sub_id})
        live = db.scalar(text(
            "SELECT count(*) FROM subscriptions WHERE user_id = (SELECT user_id FROM subscriptions WHERE id = :s) "
            "AND status IN ('incomplete','active','past_due')"), {"s": sub_id})
    assert old == "expired" and live == 1


def test_foreign_provider_leftover_does_not_block_checkout(client):
    h, sub_id = subscribe(client)
    with SessionLocal() as db, db.begin():
        db.execute(text("UPDATE subscriptions SET provider = 'stripe', psp_subscription_id = 'sub_sbx_deadbeef' "
                        "WHERE id = :s"), {"s": sub_id})
    r = client.post("/api/v1/subscription/checkout", json={"plan_code": "essentiel"},
                    headers={**h, "Idempotency-Key": uuid.uuid4().hex})
    assert r.status_code == 201 and r.json().get("checkout_url"), r.text


def test_subscription_on_provider_rejects_sandbox_ids():
    from types import SimpleNamespace

    stripe = SimpleNamespace(name="stripe")
    leftover = SimpleNamespace(provider="stripe", psp_subscription_id="sub_sbx_abc")
    real = SimpleNamespace(provider="stripe", psp_subscription_id="sub_1Real")
    other = SimpleNamespace(provider="sandbox", psp_subscription_id="sub_1Real")
    assert pay.subscription_on_provider(leftover, stripe) is False
    assert pay.subscription_on_provider(real, stripe) is True
    assert pay.subscription_on_provider(other, stripe) is False


def test_subscription_deleted_webhook_ends_subscription(client):
    h, sub_id = subscribe(client)
    with SessionLocal() as db:
        psp_sub = db.scalar(text("SELECT psp_subscription_id FROM subscriptions WHERE id = :s"), {"s": sub_id})
    post_webhook(client, _event("customer.subscription.deleted", {"id": psp_sub, "status": "canceled"}))
    process_all()
    assert client.get("/api/v1/subscription", headers=h).json()["status"] is None
    # Report seulement tant que l'abonnement est actif : les crédits d'abonnement disponibles expirent à la fin.
    assert wallet(client, h)["available"] == 0


# ---------------------------------------------------------------- journal monétaire


def test_money_journal_is_balanced_and_append_only():
    with SessionLocal() as db:
        assert db.scalar(text(
            "SELECT count(*) FROM (SELECT journal_id, currency FROM money_journal_lines "
            "GROUP BY journal_id, currency HAVING sum(amount_minor) <> 0) x")) == 0
        j = MoneyJournal(kind="test", memo="déséquilibré", ref_type="test", ref_id=uuid.uuid4())
        db.add(j)
        db.flush()
        db.add(MoneyJournalLine(journal_id=j.id, account="psp_cash", amount_minor=100, currency="EUR"))
        db.add(MoneyJournalLine(journal_id=j.id, account="customer_deferred", amount_minor=-99, currency="EUR"))
        db.flush()
        with pytest.raises(DBAPIError, match="déséquilibrée"):
            db.commit()
    with SessionLocal() as db:
        with pytest.raises(DBAPIError, match="ajout seul"):
            db.execute(text("UPDATE money_journal_lines SET amount_minor = amount_minor "
                            "WHERE id = (SELECT id FROM money_journal_lines LIMIT 1)"))


def test_commission_rounding():
    assert settle.commission_of(1800, 1000) == 180
    assert settle.commission_of(1805, 1000) == 181  # 180,5 -> 181
    assert settle.commission_of(1804, 1000) == 180
    assert settle.commission_of(0, 1000) == 0


# ---------------------------------------------------------------- règlements partenaires


def _merchant_id():
    with SessionLocal() as db:
        return db.scalar(select(Location.merchant_id).where(Location.slug == "atelier-belle-venue"))


def test_weekly_payout_transfer_and_reconciliation(client):
    # Une visite consommée (18 crédits -> 18,00 € brut, 1,80 € de commission) et un avoir de 2,00 €.
    h, b = confirmed_booking(client)
    p = client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
    assert redeem(client, login(client, "partenaire@xpass.demo"), {"qr": p["qr_payload"]}).status_code == 201
    merchant_id = _merchant_id()
    with SessionLocal() as db, db.begin():
        settle.create_adjustment(db, merchant_id=merchant_id, amount_minor=-200, label="Correction prestation",
                                 created_by=None)

    partner = login(client, "partenaire@xpass.demo")
    before = client.get("/api/v1/partner/settlements", headers=partner).json()
    assert before["terms"] == {"gross_minor_per_credit": 100, "commission_bps": 1000, "currency": "EUR", "is_demo": True}
    assert before["open_period"]["gross_minor"] >= 1800 and before["open_period"]["adjustments_minor"] <= -200

    # Une semaine plus tard, la période est fermée : le versement est constitué une seule fois.
    later = datetime.now(UTC) + timedelta(days=7)
    with SessionLocal() as db, db.begin():
        built = [x for x in settle.build_payouts(db, later) if x.merchant_id == merchant_id]
        assert len(built) == 1
        payout_id = built[0].id
        assert settle.build_payouts(db, later) == []
    with SessionLocal() as db:
        payout = db.execute(text("SELECT gross_minor, commission_minor, adjustments_minor, net_minor, status "
                                 "FROM partner_payouts WHERE id = :p"), {"p": payout_id}).one()
        sums = db.execute(text("SELECT sum(amount_minor), sum(commission_minor) FROM partner_payables WHERE payout_id = :p"),
                          {"p": payout_id}).one()
    gross, commission, adjustments, net, status = payout
    assert (gross, commission) == tuple(sums) and net == gross - commission + adjustments and status == "pending"

    # Transfert demandé au prestataire (bac à sable) puis confirmé par webhook signé.
    with SessionLocal() as db:
        assert settle.execute_pending(db, SandboxProvider(SECRET)) >= 1
    assert client.get("/api/v1/partner/settlements", headers=partner).json()["to_receive_minor"] >= net
    process_all()
    detail = client.get(f"/api/v1/partner/settlements/{payout_id}", headers=partner).json()
    assert detail["status"] == "paid" and detail["confirmed_minor"] == net
    assert any(line["gross_minor"] == 1800 and line["commission_minor"] == 180 for line in detail["lines"])
    assert any(a["label"] == "Correction prestation" for a in detail["adjustments"])
    with SessionLocal() as db:
        assert db.scalar(text("SELECT count(*) FROM partner_payables WHERE payout_id = :p AND status <> 'paid'"),
                         {"p": payout_id}) == 0
    csv = client.get(f"/api/v1/partner/settlements/{payout_id}/statement.csv", headers=partner)
    assert csv.status_code == 200 and "Net" in csv.text and "Correction prestation" in csv.text


def test_transfer_amount_mismatch_goes_to_reconcile(client):
    merchant_id = _merchant_id()
    with SessionLocal() as db, db.begin():
        settle.create_adjustment(db, merchant_id=merchant_id, amount_minor=500, label="Complément", created_by=None)
    with SessionLocal() as db, db.begin():
        payouts = [x for x in settle.build_payouts(db, datetime.now(UTC) + timedelta(days=14)) if x.merchant_id == merchant_id]
        payout_id, net = payouts[0].id, payouts[0].net_minor
        db.execute(text("UPDATE partner_payouts SET status = 'in_transit', provider = 'sandbox', "
                        "psp_transfer_id = :t WHERE id = :p"), {"t": f"tr_{payout_id.hex[:10]}", "p": payout_id})
    post_webhook(client, _event("transfer.created", {"id": f"tr_{payout_id.hex[:10]}", "amount": net - 1, "currency": "eur",
                                                     "metadata": {"xpass_payout_id": str(payout_id)}}))
    process_all()
    with SessionLocal() as db:
        assert db.execute(text("SELECT status, confirmed_minor FROM partner_payouts WHERE id = :p"),
                          {"p": payout_id}).one() == ("to_reconcile", net - 1)


def test_settlements_are_owner_only(client):
    customer = login(client, make_customer())
    assert client.get("/api/v1/partner/settlements", headers=customer).status_code == 403
    assert client.get("/api/v1/partner/settlements", headers=login(client, "rh@xpass.demo")).status_code == 403


def test_payments_disabled_without_provider(client, monkeypatch):
    h = login(client, make_customer())
    monkeypatch.setattr(get_settings(), "psp_provider", "")
    r = client.post("/api/v1/subscription/checkout", json={"plan_code": "essentiel"},
                    headers={**h, "Idempotency-Key": uuid.uuid4().hex})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "payments_disabled"
    assert client.get("/api/v1/subscription", headers=h).json()["payments_enabled"] is False


def test_sandbox_is_refused_in_production():
    from app.core.config import Settings

    with pytest.raises(ValueError, match="sandbox"):
        Settings(app_env="production", auth_dev_login_enabled=False, psp_provider="sandbox", psp_webhook_secret="x" * 20)
    with pytest.raises(ValueError, match="PSP_WEBHOOK_SECRET"):
        Settings(psp_provider="stripe", psp_secret_key="sk_test_x", psp_webhook_secret="")
