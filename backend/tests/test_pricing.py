"""Prix variable par créneau, annulation tardive à moitié rendue et absences (no-show)."""
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from app.db.session import SessionLocal
from app.modules.booking import pricing
from app.modules.booking import service as booking_service
from tests.conftest import login
from tests.test_bookings import COUPE, free_slot, hold, make_customer, post, wallet
from tests.test_redemption import _location_id, confirmed_booking

pytestmark = pytest.mark.dynamic_pricing

PARIS = ZoneInfo("Europe/Paris")
NOW = datetime(2026, 11, 2, 9, 0, tzinfo=PARIS)  # lundi matin


def at(day: int, hour: int) -> datetime:
    return datetime(2026, 11, day, hour, 0, tzinfo=PARIS)


# ---------------------------------------------------------------- règles


def test_off_peak_with_low_fill_keeps_base_price():
    p = pricing.slot_price(18, starts_at=at(4, 10), tz=PARIS, now=NOW, fill=0.2)
    assert (p.credits, p.adjustments) == (18, ())


def test_weekday_evening_and_weekend_are_peak():
    assert pricing.slot_price(18, starts_at=at(4, 19), tz=PARIS, now=NOW, fill=0).adjustments == ("peak",)
    assert pricing.slot_price(18, starts_at=at(4, 21), tz=PARIS, now=NOW, fill=0).adjustments == ()
    assert pricing.slot_price(18, starts_at=at(7, 10), tz=PARIS, now=NOW, fill=0).adjustments == ("peak",)  # samedi
    # 18 × 1,2 = 21,6 → 22 crédits
    assert pricing.slot_price(18, starts_at=at(4, 19), tz=PARIS, now=NOW, fill=0).credits == 22


def test_high_demand_adds_up_with_peak():
    p = pricing.slot_price(10, starts_at=at(4, 19), tz=PARIS, now=NOW, fill=0.75)
    assert (p.credits, p.adjustments) == (14, ("peak", "demand"))


def test_last_minute_discount_only_when_soon_and_empty():
    soon = NOW + timedelta(hours=3)
    assert pricing.slot_price(10, starts_at=soon, tz=PARIS, now=NOW, fill=0.1).adjustments == ("last_minute",)
    assert pricing.slot_price(10, starts_at=soon, tz=PARIS, now=NOW, fill=0.1).credits == 8
    assert pricing.slot_price(10, starts_at=soon, tz=PARIS, now=NOW, fill=0.5).adjustments == ()
    assert pricing.slot_price(10, starts_at=NOW + timedelta(hours=7), tz=PARIS, now=NOW, fill=0.1).adjustments == ()


def test_price_is_never_below_one_credit():
    assert pricing.slot_price(1, starts_at=NOW + timedelta(hours=1), tz=PARIS, now=NOW, fill=0).credits == 1


def test_late_refund_is_half_rounded_down():
    assert [pricing.late_cancellation_refund(n) for n in (1, 9, 18)] == [0, 4, 9]


# ---------------------------------------------------------------- API


@pytest.mark.dynamic_pricing
def test_slots_carry_their_price_and_hold_freezes_it(client):
    h = login(client, make_customer(personal=100))
    oid = COUPE()
    slot = free_slot(client, oid)
    assert slot["price_credits"] >= 1 and set(slot["price_adjustments"]) <= set(pricing.ADJUSTMENTS)
    b = hold(client, h, oid, slot, expected_price_credits=slot["price_credits"], party_size=1)
    assert b.status_code == 201, b.text
    assert b.json()["price_credits_per_person"] == slot["price_credits"]
    assert b.json()["total_credits"] == slot["price_credits"]
    assert b.json()["price_adjustments"] == slot["price_adjustments"]


@pytest.mark.dynamic_pricing
def test_hold_refused_when_displayed_price_changed(client):
    h = login(client, make_customer(personal=100))
    oid = COUPE()
    slot = free_slot(client, oid)
    r = hold(client, h, oid, slot, expected_price_credits=slot["price_credits"] + 5)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "price_changed"
    assert r.json()["detail"]["price_credits"] == slot["price_credits"]
    assert wallet(client, h)["reserved"] == 0


# ---------------------------------------------------------------- absences


def test_no_show_consumes_credits_and_pays_partner(client):
    h, b = confirmed_booking(client, starts_now=False)
    with SessionLocal() as db, db.begin():
        db.execute(text("UPDATE bookings SET starts_at = now() - interval '5 hours', "
                        "ends_at = now() - interval '4 hours' WHERE id = :id"), {"id": b["id"]})
    with SessionLocal() as db, db.begin():
        assert booking_service.mark_no_shows(db, datetime.now(UTC)) >= 1
    assert client.get(f"/api/v1/bookings/{b['id']}", headers=h).json()["status"] == "no_show"
    w = wallet(client, h)
    assert (w["reserved"], w["consumed"]) == (0, b["total_credits"])
    with SessionLocal() as db:
        assert db.execute(text("SELECT kind, credits FROM partner_payables WHERE booking_id = :b"),
                          {"b": b["id"]}).one() == ("no_show", b["total_credits"])
    # Côté commerçant : l'absence apparaît dans les statistiques et le planning garde le prix payé.
    owner = login(client, "partenaire@xpass.demo")
    stats = client.get(f"/api/v1/partner/locations/{_location_id()}/stats?days=30", headers=owner).json()
    assert stats["no_shows"] >= 1
    rows = client.get("/api/v1/partner/bookings", headers=owner).json()
    row = next(r for r in rows if r["id"] == b["id"])
    assert row["status"] == "no_show" and row["price_credits_per_person"] == b["price_credits_per_person"]


def test_booking_still_redeemable_is_not_a_no_show(client):
    h, b = confirmed_booking(client, starts_now=False)
    with SessionLocal() as db, db.begin():
        db.execute(text("UPDATE bookings SET starts_at = now() - interval '90 minutes', "
                        "ends_at = now() - interval '60 minutes' WHERE id = :id"), {"id": b["id"]})
        booking_service.mark_no_shows(db, datetime.now(UTC))
    assert client.get(f"/api/v1/bookings/{b['id']}", headers=h).json()["status"] == "confirmed"
    # Nettoyage : annulation impossible (commencée), on laisse la réservation passée.
    post(client, h, f"/api/v1/bookings/{b['id']}/cancel")
