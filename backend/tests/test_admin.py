"""Administration (lot 7) : décisions motivées et tracées, litiges et restitution, rapprochement."""
import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.db.session import SessionLocal
from app.modules.catalog.models import Location, Merchant
from app.modules.identity.models import Membership, User
from app.modules.settlement import service as settle
from tests.conftest import login
from tests.test_bookings import make_customer, wallet
from tests.test_payments import _event, post_webhook, process_all
from tests.test_redemption import confirmed_booking, new_operator, redeem


def _operator() -> str:
    email = f"op-{uuid.uuid4().hex[:8]}@xpass.demo"
    with SessionLocal() as db, db.begin():
        u = User(email=email, display_name="Opérateur", is_demo=True)
        db.add(u)
        db.flush()
        db.add(Membership(user_id=u.id, scope_type="platform", scope_id=None, role="platform_operator"))
    return email


def _pending_merchant() -> str:
    with SessionLocal() as db:
        return str(db.scalar(select(Merchant.id).where(Merchant.commercial_status == "pending_review").limit(1)))


def redeemed_booking(client, **credits) -> tuple[dict, dict]:
    h, b = confirmed_booking(client)
    p = client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
    assert redeem(client, login(client, new_operator()), {"qr": p["qr_payload"]}).status_code == 201
    return h, b


# ---------------------------------------------------------------- droits et audit


def test_access_and_admin_only_actions(client):
    admin, op = login(client, "admin@xpass.demo"), login(client, _operator())
    for who in ("partenaire@xpass.demo", "rh@xpass.demo"):
        assert client.get("/api/v1/admin/overview", headers=login(client, who)).status_code == 403
    assert client.get("/api/v1/admin/overview", headers=op).json()["is_admin"] is False
    assert client.get("/api/v1/admin/overview", headers=admin).json()["is_admin"] is True
    mid = _pending_merchant()
    r = client.post(f"/api/v1/admin/merchants/{mid}/decision", json={"decision": "approve", "reason": "Dossier complet"},
                    headers=op)
    assert r.status_code == 403


def test_merchant_decision_requires_reason_and_is_audited(client):
    admin = login(client, "admin@xpass.demo")
    mid = _pending_merchant()
    r = client.post(f"/api/v1/admin/merchants/{mid}/decision", json={"decision": "request_documents", "reason": ""},
                    headers=admin)
    assert r.json()["detail"]["code"] == "reason_required"
    r = client.post(f"/api/v1/admin/merchants/{mid}/decision",
                    json={"decision": "request_documents", "reason": "Extrait Kbis manquant"}, headers=admin)
    assert r.json() == {"commercial_status": "documents_missing"}
    detail = client.get(f"/api/v1/admin/merchants/{mid}", headers=admin).json()
    assert detail["commercial_status"] == "documents_missing"
    entry = detail["audit"][0]
    assert entry["action"] == "merchant.request_documents" and entry["reason"] == "Extrait Kbis manquant"
    assert entry["actor_name"] == "Admin Démo" and entry["details"] == {"from": "pending_review", "to": "documents_missing"}
    assert any(c["label"] == "Documents de l'entreprise" and c["ok"] is False for c in detail["checks"])
    client.post(f"/api/v1/admin/merchants/{mid}/decision", json={"decision": "reopen", "reason": "Remise en file"},
                headers=admin)


def test_audit_log_is_append_only():
    with SessionLocal() as db:
        with pytest.raises(DBAPIError, match="ajout seul"):
            db.execute(text("DELETE FROM audit_events WHERE id = (SELECT id FROM audit_events LIMIT 1)"))
        db.rollback()
        with pytest.raises(DBAPIError, match="ajout seul"):
            db.execute(text("UPDATE audit_events SET reason = 'x' WHERE id = (SELECT id FROM audit_events LIMIT 1)"))


def test_psp_status_is_separate_from_commercial_validation(client):
    admin = login(client, "admin@xpass.demo")
    with SessionLocal() as db, db.begin():
        m = db.scalar(select(Merchant).where(Merchant.psp_status != "verified").limit(1))
        mid, m.psp_account_id = m.id, f"acct_test_{uuid.uuid4().hex[:8]}"
        account = m.psp_account_id
    # Validation commerciale : ne change pas le statut PSP.
    client.post(f"/api/v1/admin/merchants/{mid}/decision", json={"decision": "approve", "reason": "Dossier complet"},
                headers=admin)
    assert client.get(f"/api/v1/admin/merchants/{mid}", headers=admin).json()["psp_status"] != "verified"
    # Le prestataire signale le compte vérifié par webhook signé.
    post_webhook(client, _event("account.updated", {"id": account, "charges_enabled": True, "payouts_enabled": True}))
    process_all()
    detail = client.get(f"/api/v1/admin/merchants/{mid}", headers=admin).json()
    assert detail["psp_status"] == "verified" and detail["audit"][0]["actor_kind"] == "system"


def test_moderation_hides_location_from_catalog(client):
    admin = login(client, _operator())
    with SessionLocal() as db:
        loc_id = db.scalar(select(Location.id).where(Location.slug == "le-cercle"))
    assert client.get("/api/v1/catalog/locations/le-cercle").status_code == 200
    r = client.post(f"/api/v1/admin/locations/{loc_id}/moderation", json={"publish": False, "reason": "Photos non conformes"},
                    headers=admin)
    assert r.json() == {"status": "hidden"}
    assert client.get("/api/v1/catalog/locations/le-cercle").status_code == 404
    client.post(f"/api/v1/admin/locations/{loc_id}/moderation", json={"publish": True, "reason": "Photos corrigées"},
                headers=admin)
    assert client.get("/api/v1/catalog/locations/le-cercle").status_code == 200


# ---------------------------------------------------------------- litiges


def test_customer_dispute_rules(client):
    h, b = confirmed_booking(client, starts_now=False)
    r = client.post(f"/api/v1/bookings/{b['id']}/disputes", json={"reason": "Prestation non conforme à l'annonce"}, headers=h)
    assert r.json()["detail"]["code"] == "not_disputable"  # pas encore utilisée
    h, b = redeemed_booking(client)
    assert client.post(f"/api/v1/bookings/{b['id']}/disputes", json={"reason": "court"}, headers=h).status_code == 422
    other = login(client, make_customer())
    assert client.post(f"/api/v1/bookings/{b['id']}/disputes", json={"reason": "Je réclame pour un autre"},
                       headers=other).status_code == 404
    r = client.post(f"/api/v1/bookings/{b['id']}/disputes", json={"reason": "Contenu différent de l'annonce"}, headers=h)
    assert r.status_code == 201 and r.json()["reference"].startswith("L-") and r.json()["status"] == "open"
    again = client.post(f"/api/v1/bookings/{b['id']}/disputes", json={"reason": "Deuxième réclamation"}, headers=h)
    assert again.json()["detail"]["code"] == "already_open"


def test_refund_restores_credits_by_source_and_adjusts_partner(client):
    h, b = redeemed_booking(client)
    before = wallet(client, h)
    d = client.post(f"/api/v1/bookings/{b['id']}/disputes", json={"reason": "Atelier différent de l'annonce"}, headers=h).json()
    op = login(client, _operator())
    did = next(x["id"] for x in client.get("/api/v1/admin/disputes", headers=op).json() if x["reference"] == d["reference"])
    detail = client.get(f"/api/v1/admin/disputes/{did}", headers=op).json()
    assert detail["funding"] == {"personal": 18} and detail["payable_net_minor"] == 1620
    assert client.post(f"/api/v1/admin/disputes/{did}/update",
                       json={"status": "in_review", "notes": "Client joint", "reason": "Prise en charge"},
                       headers=op).json() == {"status": "in_review"}
    too_high = client.post(f"/api/v1/admin/disputes/{did}/refund",
                           json={"partner_adjustment_minor": 1700, "reason": "Restitution complète"}, headers=op)
    assert too_high.json()["detail"]["code"] == "adjustment_too_high"
    r = client.post(f"/api/v1/admin/disputes/{did}/refund", json={"partner_adjustment_minor": 1500,
                                                                  "reason": "Contenu non conforme confirmé"}, headers=op)
    assert r.json() == {"status": "resolved_refund", "credits_restored": 18}
    after = wallet(client, h)
    assert after["by_source"]["personal"]["available"] == before["by_source"]["personal"]["available"] + 18
    # Rejouer la restitution est refusé : le litige est clos.
    assert client.post(f"/api/v1/admin/disputes/{did}/refund", json={"reason": "Encore une fois"}, headers=op).status_code == 409
    with SessionLocal() as db:
        adj = db.execute(text("SELECT amount_minor, label FROM partner_adjustments WHERE label = :l"),
                         {"l": f"Litige {d['reference']}"}).one()
    assert adj == (-1500, f"Litige {d['reference']}")
    timeline = client.get(f"/api/v1/admin/disputes/{did}", headers=op).json()["timeline"]
    assert [t["action"] for t in timeline] == ["dispute.opened", "dispute.updated", "dispute.refunded"]
    mine = client.get(f"/api/v1/bookings/{b['id']}/disputes", headers=h).json()
    assert mine[0]["status"] == "resolved_refund" and mine[0]["credits_restored"] == 18 and "operator_notes" not in mine[0]
    assert client.post(f"/api/v1/bookings/{b['id']}/disputes", json={"reason": "Une nouvelle réclamation"},
                       headers=h).json()["detail"]["code"] == "already_refunded"


def test_reject_dispute(client):
    h, b = redeemed_booking(client)
    client.post(f"/api/v1/bookings/{b['id']}/disputes", json={"reason": "Je n'ai pas aimé du tout"}, headers=h)
    op = login(client, _operator())
    did = client.get("/api/v1/admin/disputes", headers=op).json()[0]["id"]
    assert client.post(f"/api/v1/admin/disputes/{did}/reject", json={"reason": "Prestation conforme"},
                       headers=op).json() == {"status": "resolved_rejected"}
    assert client.post(f"/api/v1/admin/disputes/{did}/reject", json={"reason": "Encore"}, headers=op).status_code in (409, 422)


# ---------------------------------------------------------------- rapprochement


def test_reconciliation_queue_and_actions(client):
    admin = login(client, "admin@xpass.demo")
    with SessionLocal() as db:
        merchant_id = db.scalar(select(Location.merchant_id).where(Location.slug == "atelier-belle-venue"))
    with SessionLocal() as db, db.begin():
        settle.create_adjustment(db, merchant_id=merchant_id, amount_minor=700, label="Complément test", created_by=None)
    with SessionLocal() as db, db.begin():
        payout = next(p for p in settle.build_payouts(db, datetime.now(UTC) + timedelta(days=21)) if p.merchant_id == merchant_id)
        pid, net = payout.id, payout.net_minor
        db.execute(text("UPDATE partner_payouts SET status = 'in_transit', provider = 'sandbox', psp_transfer_id = :t "
                        "WHERE id = :p"), {"t": f"tr_r_{pid.hex[:8]}", "p": pid})
    post_webhook(client, _event("transfer.created", {"id": f"tr_r_{pid.hex[:8]}", "amount": net - 50, "currency": "eur",
                                                     "metadata": {"xpass_payout_id": str(pid)}}))
    bad = _event("invoice.paid", {"id": f"in_admin_{uuid.uuid4().hex[:8]}", "subscription": "sub_inconnu",
                                  "amount_paid": 1, "currency": "eur"})
    post_webhook(client, bad)
    process_all()
    rec = client.get("/api/v1/admin/reconciliation", headers=admin).json()
    assert any(p["id"] == str(pid) and p["confirmed_minor"] == net - 50 for p in rec["payouts"])
    ev = next(e for e in rec["events"] if e["event_id"] == json.loads(bad)["id"])
    assert "RetryLater" in ev["last_error"]
    assert client.get("/api/v1/admin/overview", headers=admin).json()["reconciliation_issues"] >= 2
    # Mauvaise action dans l'état courant.
    assert client.post(f"/api/v1/admin/payouts/{pid}/retry", json={"reason": "Nouvel essai"}, headers=admin).status_code == 409
    assert client.post(f"/api/v1/admin/payouts/{pid}/close", json={"reason": "Frais bancaires confirmés"},
                       headers=admin).status_code == 200
    assert client.post(f"/api/v1/admin/payment-events/{ev['id']}/dismiss", json={"reason": "Événement de test"},
                       headers=admin).status_code == 200
    audit = client.get("/api/v1/admin/audit", headers=admin).json()
    actions = [a["action"] for a in audit[:5]]
    assert "payment_event.dismiss" in actions and "payout.close" in actions and "payout.mismatch" in [a["action"] for a in audit]
