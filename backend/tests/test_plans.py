"""Formules d'abonnement : report plafonné des crédits, changement de formule, gestion par l'administration."""
import time
import uuid

from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.modules.catalog.models import Market
from app.modules.wallet import service as wallet_service
from tests.conftest import login
from tests.test_bookings import wallet
from tests.test_payments import _event, post_webhook, process_all, subscribe


def _psp_sub(sub_id: str) -> str:
    with SessionLocal() as db:
        return db.scalar(text("SELECT psp_subscription_id FROM subscriptions WHERE id = :s"), {"s": sub_id})


def renew(client, sub_id: str, amount: int = 10000, price_id: str | None = None) -> None:
    line = {"period": {"start": int(time.time()), "end": int(time.time()) + 86400 * 30}}
    if price_id:
        line["price"] = {"id": price_id}
    invoice = {"id": f"in_{uuid.uuid4().hex}", "subscription": _psp_sub(sub_id), "amount_paid": amount,
               "currency": "eur", "lines": {"data": [line]}}
    post_webhook(client, _event("invoice.paid", invoice))
    process_all()


def _expired(sub_id: str) -> int:
    with SessionLocal() as db:
        return db.scalar(text(
            "SELECT coalesce(sum(b.expired), 0) FROM credit_lot_balances b JOIN credit_lots l ON l.id = b.lot_id "
            "JOIN wallets w ON w.id = l.wallet_id JOIN subscriptions s ON s.user_id = w.user_id WHERE s.id = :s"),
            {"s": sub_id})


def test_unused_credits_roll_over_up_to_one_month(client):
    h, sub_id = subscribe(client)  # 100 crédits (formule Essentiel)
    renew(client, sub_id)
    assert (wallet(client, h)["available"], _expired(sub_id)) == (200, 0)  # 100 reportés + 100 du nouveau mois
    renew(client, sub_id)
    # Report limité à 100 : les 100 plus anciens expirent.
    assert (wallet(client, h)["available"], _expired(sub_id)) == (200, 100)
    sub = client.get("/api/v1/subscription", headers=h).json()
    assert (sub["subscription_credits"], sub["rollover_cap"]) == (200, 100)


def test_rollover_cap_never_touches_employer_or_promotional_credits(client):
    h, sub_id = subscribe(client)
    with SessionLocal() as db, db.begin():
        user_id = db.scalar(text("SELECT user_id FROM subscriptions WHERE id = :s"), {"s": sub_id})
        market_id = db.scalar(select(Market.id).where(Market.code == "FR"))
        w = wallet_service.get_or_create_wallet(db, user_id, market_id, lock=True)
        wallet_service.grant(db, w, source="employer", amount=50, label="Employeur", origin_type="test")
    renew(client, sub_id)
    renew(client, sub_id)
    assert wallet(client, h)["available"] == 250  # 100 reportés + 100 du mois + 50 employeur intacts


def _admin_plans(client, admin):
    return client.get("/api/v1/admin/plans", headers=admin).json()


def _new_plan(client, admin, **over) -> dict:
    code = f"intense-{uuid.uuid4().hex[:6]}"
    body = {"code": code, "name": "Intense", "price_minor": 18000, "credits_per_period": 200, "is_active": True, **over}
    r = client.post("/api/v1/admin/plans", headers=admin, json=body)
    assert r.status_code == 201, r.text
    return next(p for p in r.json() if p["code"] == code)


def test_admin_manages_plans_and_customers_see_active_ones(client):
    admin = login(client, "admin@xpass.demo")
    plan = _new_plan(client, admin)
    assert plan["subscribers"] == 0 and plan["currency"] == "EUR"
    public = {p["code"] for p in client.get("/api/v1/subscription/plans").json()}
    assert plan["code"] in public
    body = {**{k: plan[k] for k in ("code", "name", "price_minor", "credits_per_period")}, "is_active": False}
    assert client.put(f"/api/v1/admin/plans/{plan['id']}", headers=admin, json=body).status_code == 200
    assert plan["code"] not in {p["code"] for p in client.get("/api/v1/subscription/plans").json()}
    # Réservé à l'administration.
    customer = login(client, "rh@xpass.demo")
    assert client.post("/api/v1/admin/plans", headers=customer, json=body).status_code == 403


def test_price_of_a_plan_in_use_cannot_change(client):
    admin = login(client, "admin@xpass.demo")
    subscribe(client)  # au moins un abonné à « essentiel »
    essentiel = next(p for p in _admin_plans(client, admin) if p["code"] == "essentiel")
    body = {k: essentiel[k] for k in ("code", "name", "credits_per_period", "is_active")}
    r = client.put(f"/api/v1/admin/plans/{essentiel['id']}", headers=admin, json={**body, "price_minor": 9000})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "plan_in_use"
    # Le nom reste modifiable.
    ok = client.put(f"/api/v1/admin/plans/{essentiel['id']}", headers=admin,
                    json={**body, "price_minor": essentiel["price_minor"], "name": "XPASS Essentiel"})
    assert ok.status_code == 200


def test_plan_change_applies_at_next_renewal(client):
    admin = login(client, "admin@xpass.demo")
    intense = _new_plan(client, admin)
    h, sub_id = subscribe(client)
    r = client.post("/api/v1/subscription/change-plan", headers=h, json={"plan_code": intense["code"]})
    assert r.status_code == 200, r.text
    assert r.json()["plan"]["code"] == "essentiel" and r.json()["pending_plan"]["code"] == intense["code"]
    assert wallet(client, h)["available"] == 100  # rien ne change pendant le mois en cours
    renew(client, sub_id, amount=intense["price_minor"])
    sub = client.get("/api/v1/subscription", headers=h).json()
    assert sub["plan"]["code"] == intense["code"] and sub["pending_plan"] is None
    assert wallet(client, h)["available"] == 300  # 100 reportés (plafond 200) + 200 de la formule Intense


def test_renewal_at_unexpected_amount_is_still_refused(client):
    h, sub_id = subscribe(client)
    renew(client, sub_id, amount=12345)
    assert wallet(client, h)["available"] == 100
