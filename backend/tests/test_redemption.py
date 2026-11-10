"""QR éphémère, scan sans effet, consommation atomique et unique."""
import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.main import app
from app.modules.catalog.models import Location
from app.modules.identity.models import Membership, User
from tests.conftest import login
from tests.test_bookings import COUPE, free_slot, hold, make_customer, post, wallet


def _location_id(slug: str = "atelier-belle-venue") -> str:
    with SessionLocal() as db:
        return str(db.scalar(select(Location.id).where(Location.slug == slug)))


def confirmed_booking(client, *, starts_now: bool = True) -> tuple[dict, dict]:
    """Réservation confirmée ; si `starts_now`, déplacée dans la fenêtre de consommation."""
    h = login(client, make_customer(personal=40))
    oid = COUPE()
    b = hold(client, h, oid, free_slot(client, oid)).json()
    post(client, h, f"/api/v1/bookings/{b['id']}/confirm")
    if starts_now:
        with SessionLocal() as db, db.begin():
            db.execute(
                text("UPDATE bookings SET starts_at = now() + interval '10 minutes', "
                     "ends_at = now() + interval '40 minutes' WHERE id = :id"),
                {"id": b["id"]},
            )
    return h, b


def new_operator(merchant_slug: str = "atelier-belle-venue") -> str:
    email = f"staff-{uuid.uuid4().hex[:8]}@xpass.demo"
    with SessionLocal() as db, db.begin():
        merchant_id = db.scalar(select(Location.merchant_id).where(Location.slug == merchant_slug))
        user = User(email=email, display_name="Opérateur Test", is_demo=True)
        db.add(user)
        db.flush()
        db.add(Membership(user_id=user.id, scope_type="merchant", scope_id=merchant_id, role="merchant_staff"))
    return email


def scan(client, partner, payload, path="/api/v1/partner/scan/preview", key=None):
    headers = {**partner, "Idempotency-Key": key or uuid.uuid4().hex}
    return client.post(path, json={"location_id": _location_id(), **payload}, headers=headers)


def redeem(client, partner, payload, key=None):
    return scan(client, partner, payload, path="/api/v1/partner/redemptions", key=key)


# ---------------------------------------------------------------- émission


def test_pass_only_for_confirmed_and_stored_as_hash(client):
    h = login(client, make_customer(personal=40))
    oid = COUPE()
    b = hold(client, h, oid, free_slot(client, oid)).json()
    assert client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).status_code == 409  # encore HELD
    post(client, h, f"/api/v1/bookings/{b['id']}/confirm")
    p = client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
    assert p["qr_payload"].startswith("XPASS1:") and p["expires_in"] == 60
    assert len(p["manual_code"]) == 9 and p["manual_code"][4] == "-"
    token = p["qr_payload"].removeprefix("XPASS1:")
    with SessionLocal() as db:
        stored = db.execute(text("SELECT token_hash FROM qr_tokens WHERE booking_id = :b"), {"b": b["id"]}).scalars().all()
    assert stored == [hashlib.sha256(token.encode()).hexdigest()]
    other = login(client, make_customer(personal=5))
    assert client.post(f"/api/v1/bookings/{b['id']}/pass", headers=other).status_code == 404


def test_renewed_pass_revokes_previous(client):
    h, b = confirmed_booking(client)
    old = client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
    client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h)
    partner = login(client, new_operator())
    r = scan(client, partner, {"qr": old["qr_payload"]})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "expired_code"


# ---------------------------------------------------------------- aperçu


def test_preview_has_no_financial_effect(client):
    h, b = confirmed_booking(client)
    p = client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
    partner = login(client, new_operator())
    r = scan(client, partner, {"qr": p["qr_payload"]})
    assert r.status_code == 200, r.text
    pv = r.json()
    assert pv["offer_title"] == "Coupe et coiffage" and pv["resource_name"] == "Sarah" and pv["total_credits"] == 18
    w = wallet(client, h)
    assert (w["reserved"], w["consumed"]) == (18, 0)
    assert client.get(f"/api/v1/bookings/{b['id']}", headers=h).json()["status"] == "confirmed"


def test_preview_rejects_outside_window(client):
    h, b = confirmed_booking(client, starts_now=False)  # dans plusieurs jours
    p = client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
    r = scan(client, login(client, new_operator()), {"qr": p["qr_payload"]})
    assert r.json()["detail"]["code"] == "outside_window"


def test_wrong_location_and_foreign_partner(client):
    h, b = confirmed_booking(client)
    p = client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
    other = login(client, new_operator("le-cercle"))
    r = client.post(
        "/api/v1/partner/scan/preview",
        json={"location_id": _location_id("le-cercle"), "qr": p["qr_payload"]},
        headers=other,
    )
    assert r.json()["detail"]["code"] == "wrong_location"
    # Un partenaire ne peut pas viser un établissement qui n'est pas le sien.
    assert scan(client, other, {"qr": p["qr_payload"]}).status_code == 403
    # Un client non plus.
    assert scan(client, h, {"qr": p["qr_payload"]}).status_code == 403


def test_expired_code_but_scanned_operator_can_still_confirm(client):
    h, b = confirmed_booking(client)
    p = client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
    op1, op2 = login(client, new_operator()), login(client, new_operator())
    assert scan(client, op1, {"qr": p["qr_payload"]}).status_code == 200
    with SessionLocal() as db, db.begin():
        db.execute(text("UPDATE qr_tokens SET expires_at = now() - interval '1 second' WHERE booking_id = :b"),
                   {"b": b["id"]})
    # Un autre opérateur ne peut plus l'utiliser ; celui qui a scanné peut confirmer.
    assert redeem(client, op2, {"qr": p["qr_payload"]}).json()["detail"]["code"] == "expired_code"
    assert redeem(client, op1, {"qr": p["qr_payload"]}).status_code == 201


# ---------------------------------------------------------------- consommation


def test_redeem_is_atomic_and_complete(client):
    h, b = confirmed_booking(client)
    p = client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
    partner = login(client, "partenaire@xpass.demo")
    r = redeem(client, partner, {"code": p["manual_code"].lower()})  # saisie manuelle, casse indifférente
    assert r.status_code == 201, r.text
    ref = r.json()["receipt_reference"]
    assert ref.startswith("XP-") and r.json()["credits"] == 18

    w = wallet(client, h)
    assert (w["available"], w["reserved"], w["consumed"]) == (22, 0, 18)
    booking = client.get(f"/api/v1/bookings/{b['id']}", headers=h).json()
    assert booking["status"] == "redeemed" and booking["receipt_reference"] == ref
    receipt = client.get(f"/api/v1/bookings/{b['id']}/receipt", headers=h).json()
    assert receipt["credits_total"] == 18 and receipt["funding"] == [{"source": "personal", "credits": 18}]
    with SessionLocal() as db:
        payable = db.execute(text("SELECT kind, credits, status, amount_minor, commission_minor, currency "
                                  "FROM partner_payables WHERE booking_id = :b"), {"b": b["id"]}).one()
        # Barème de démonstration : 1,00 € par crédit, commission 10 %.
        assert tuple(payable) == ("redemption", 18, "valued", 1800, 180, "EUR")
        assert db.scalar(text("SELECT count(*) FROM outbox_events WHERE aggregate_id = :b AND event_type = 'booking.redeemed'"),
                         {"b": b["id"]}) == 1
        assert db.scalar(text("SELECT method FROM redemptions WHERE booking_id = :b"), {"b": b["id"]}) == "code"
    past = client.get("/api/v1/bookings", headers=h, params={"scope": "past"}).json()
    assert b["id"] in [i["id"] for i in past["items"]]
    visits = client.get("/api/v1/partner/redemptions", headers=partner, params={"location_id": _location_id()}).json()
    assert b["id"] in [v["booking_id"] for v in visits]


def test_double_redeem_is_refused_and_replay_is_safe(client):
    h, b = confirmed_booking(client)
    p = client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
    partner = login(client, new_operator())
    key = uuid.uuid4().hex
    first = redeem(client, partner, {"qr": p["qr_payload"]}, key=key)
    replay = redeem(client, partner, {"qr": p["qr_payload"]}, key=key)
    assert first.status_code == replay.status_code == 201
    assert replay.headers.get("Idempotent-Replayed") == "true"
    second = redeem(client, partner, {"qr": p["qr_payload"]})
    assert second.status_code == 409 and second.json()["detail"]["code"] == "already_redeemed"
    assert wallet(client, h)["consumed"] == 18


def test_concurrent_redeems_consume_once():
    with TestClient(app) as c:
        h, b = confirmed_booking(c)
        p = c.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
        operators = [login(c, new_operator()) for _ in range(5)]
    barrier = Barrier(5)

    def attempt(i):
        barrier.wait()
        with TestClient(app) as c:
            return redeem(c, operators[i], {"qr": p["qr_payload"]}).status_code

    with ThreadPoolExecutor(5) as pool:
        codes = list(pool.map(attempt, range(5)))
    assert codes.count(201) == 1, codes
    with TestClient(app) as c:
        assert wallet(c, h)["consumed"] == 18
    with SessionLocal() as db:
        assert db.scalar(text("SELECT count(*) FROM receipts WHERE booking_id = :b"), {"b": b["id"]}) == 1
        assert db.scalar(text("SELECT count(*) FROM partner_payables WHERE booking_id = :b"), {"b": b["id"]}) == 1


def test_brute_force_on_manual_codes_is_limited(client):
    partner = login(client, new_operator())
    codes = [redeem(client, partner, {"code": f"AAAA-{i:04d}"}).status_code for i in range(20)]
    assert set(codes) == {404}
    assert scan(client, partner, {"code": "ZZZZ-ZZZZ"}).status_code == 429


def test_late_cancellation_creates_partner_payable(client):
    h, b = confirmed_booking(client, starts_now=False)
    with SessionLocal() as db, db.begin():
        db.execute(text("UPDATE bookings SET free_cancellation_until = now() - interval '1 minute' WHERE id = :id"),
                   {"id": b["id"]})
    post(client, h, f"/api/v1/bookings/{b['id']}/cancel")
    with SessionLocal() as db:
        assert db.execute(text("SELECT kind, credits FROM partner_payables WHERE booking_id = :b"),
                          {"b": b["id"]}).one() == ("late_cancellation", 9)


# ---------------------------------------------------------------- agenda


def test_ics_contains_event_but_never_the_token(client):
    h, b = confirmed_booking(client, starts_now=False)
    p = client.post(f"/api/v1/bookings/{b['id']}/pass", headers=h).json()
    r = client.get(f"/api/v1/bookings/{b['id']}/calendar.ics", headers=h)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
    body = r.text
    assert "BEGIN:VEVENT" in body and "DTSTART:" in body and "TRIGGER:-PT1H" in body
    assert "12 rue Oberkampf" in body
    token = p["qr_payload"].removeprefix("XPASS1:")
    assert token not in body and p["manual_code"] not in body and "XPASS1" not in body
