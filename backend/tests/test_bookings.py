"""Réservation transactionnelle : contre un vrai PostgreSQL, y compris en concurrence."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.db.session import SessionLocal
from app.main import app
from app.modules.booking import service as booking_service
from app.modules.catalog.models import Location, Market, Offer, OfferVersion, Resource
from app.modules.identity.models import User
from app.modules.wallet import service as wallet_service
from app.modules.wallet.models import CreditJournal, CreditJournalLine, CreditLotBalance
from tests.conftest import login


# ---------------------------------------------------------------- utilitaires


def make_customer(**credits: int) -> str:
    """Crée un client de démo avec des lots (personal=…, employer=…, promotional=…)."""
    email = f"client-{uuid.uuid4().hex[:10]}@xpass.demo"
    with SessionLocal() as db, db.begin():
        user = User(email=email, display_name="Client Test", is_demo=True)
        db.add(user)
        db.flush()
        market_id = db.scalar(select(Market.id).where(Market.code == "FR"))
        wallet = wallet_service.get_or_create_wallet(db, user.id, market_id, lock=True)
        for source, amount in credits.items():
            wallet_service.grant(db, wallet, source=source, amount=amount, label=f"Test {source}", origin_type="test")
    return email


def offer_id(slug: str, title: str | None = None) -> str:
    with SessionLocal() as db:
        stmt = (
            select(Offer.id)
            .join(Location, Location.id == Offer.location_id)
            .join(OfferVersion, OfferVersion.id == Offer.current_version_id)
            .where(Location.slug == slug)
        )
        if title:
            stmt = stmt.where(OfferVersion.title == title)
        return str(db.scalars(stmt.order_by(Offer.sort_order)).first())


_used: set[tuple[str, str]] = set()


def free_slot(client: TestClient, oid: str) -> dict:
    """Premier créneau libre jamais utilisé par un autre test (évite les interférences)."""
    days = client.get(f"/api/v1/catalog/offers/{oid}/availability").json()["days"]
    for d in days[2:]:
        if not d["open"]:
            continue
        av = client.get(f"/api/v1/catalog/offers/{oid}/availability", params={"date": d["date"]}).json()
        for s in av["slots"]:
            if s["available"] and (oid, s["starts_at"]) not in _used:
                _used.add((oid, s["starts_at"]))
                return s
    raise AssertionError("aucun créneau libre")


def hold(client, headers, oid, slot, key=None, **extra):
    return client.post(
        "/api/v1/bookings",
        json={"offer_id": oid, "starts_at": slot["starts_at"], **extra},
        headers={**headers, "Idempotency-Key": key or uuid.uuid4().hex},
    )


def post(client, headers, path, key=None):
    return client.post(path, headers={**headers, "Idempotency-Key": key or uuid.uuid4().hex})


def wallet(client, headers) -> dict:
    return client.get("/api/v1/wallet", headers=headers).json()


COUPE = lambda: offer_id("atelier-belle-venue", "Coupe et coiffage")  # noqa: E731  (Sarah uniquement)
CERAMIQUE = lambda: offer_id("atelier-ceramique")  # noqa: E731  (capacité 8)


# ---------------------------------------------------------------- parcours nominal


def test_availability_lists_resources_and_slots(client):
    av = client.get(f"/api/v1/catalog/offers/{COUPE()}/availability").json()
    assert av["timezone"] == "Europe/Paris"
    assert [r["name"] for r in av["resources"]] == ["Sarah"]
    assert len(av["days"]) == 14


def test_hold_confirm_and_list(client):
    h = login(client, make_customer(personal=50, employer=70, promotional=20))
    oid = COUPE()
    slot = free_slot(client, oid)

    r = hold(client, h, oid, slot)
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["status"] == "held" and b["resource_name"] == "Sarah"
    assert 280 <= b["hold_seconds_remaining"] <= 300
    # Promotionnel consommé en priorité (18 sur 20).
    assert b["funding"] == [{"source": "promotional", "credits": 18}]
    w = wallet(client, h)
    assert (w["available"], w["reserved"]) == (122, 18)

    # Le créneau n'est plus proposé.
    day = slot["starts_at"][:10]
    av = client.get(f"/api/v1/catalog/offers/{oid}/availability", params={"date": day}).json()
    assert not next(s for s in av["slots"] if s["starts_at"] == slot["starts_at"])["available"]

    c = post(client, h, f"/api/v1/bookings/{b['id']}/confirm")
    assert c.status_code == 200 and c.json()["status"] == "confirmed"
    listing = client.get("/api/v1/bookings", headers=h, params={"scope": "upcoming"}).json()
    assert [i["id"] for i in listing["items"]] == [b["id"]]
    assert listing["counts"]["upcoming"] == 1
    # Confirmer reste réservé (non consommé) : la consommation arrive avec le QR (lot 3).
    assert wallet(client, h)["reserved"] == 18


def test_bookings_require_auth_and_ownership(client):
    oid = COUPE()
    slot = free_slot(client, oid)
    assert hold(client, {}, oid, slot).status_code == 401
    owner = login(client, make_customer(personal=40))
    other = login(client, make_customer(personal=40))
    b = hold(client, owner, oid, slot).json()
    assert client.get(f"/api/v1/bookings/{b['id']}", headers=other).status_code == 404
    assert post(client, other, f"/api/v1/bookings/{b['id']}/cancel").status_code == 404


def test_external_ticket_is_not_bookable(client):
    h = login(client, make_customer(personal=40))
    oid = offer_id("cine-villette")
    r = hold(client, h, oid, {"starts_at": (datetime.now(UTC) + timedelta(days=3)).isoformat()})
    assert r.status_code == 422


def test_invalid_slot_rejected(client):
    h = login(client, make_customer(personal=40))
    oid = COUPE()
    slot = free_slot(client, oid)
    off_grid = (datetime.fromisoformat(slot["starts_at"]) + timedelta(minutes=7)).isoformat()
    assert hold(client, h, oid, {"starts_at": off_grid}).json()["detail"]["code"] == "invalid_slot"


# ---------------------------------------------------------------- crédits


def test_insufficient_credits_reserves_nothing(client):
    h = login(client, make_customer(personal=10))
    oid = COUPE()
    slot = free_slot(client, oid)
    r = hold(client, h, oid, slot)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "insufficient_credits"
    assert r.json()["detail"]["available"] == 10
    assert wallet(client, h)["available"] == 10
    # La capacité n'a pas été prise.
    day = slot["starts_at"][:10]
    av = client.get(f"/api/v1/catalog/offers/{oid}/availability", params={"date": day}).json()
    assert next(s for s in av["slots"] if s["starts_at"] == slot["starts_at"])["available"]


def test_free_cancellation_releases_credits(client):
    h = login(client, make_customer(personal=40))
    oid = COUPE()
    b = hold(client, h, oid, free_slot(client, oid)).json()
    post(client, h, f"/api/v1/bookings/{b['id']}/confirm")
    r = post(client, h, f"/api/v1/bookings/{b['id']}/cancel")
    assert r.json()["status"] == "cancelled" and r.json()["late_cancellation"] is False
    w = wallet(client, h)
    assert (w["available"], w["reserved"], w["consumed"]) == (40, 0, 0)
    # Double annulation : sans effet.
    assert post(client, h, f"/api/v1/bookings/{b['id']}/cancel").json()["status"] == "cancelled"
    assert wallet(client, h)["available"] == 40


def test_late_cancellation_returns_half(client):
    h = login(client, make_customer(personal=40))
    oid = COUPE()
    b = hold(client, h, oid, free_slot(client, oid)).json()
    post(client, h, f"/api/v1/bookings/{b['id']}/confirm")
    with SessionLocal() as db, db.begin():
        db.execute(
            text("UPDATE bookings SET free_cancellation_until = now() - interval '1 minute' WHERE id = :id"),
            {"id": b["id"]},
        )
    r = post(client, h, f"/api/v1/bookings/{b['id']}/cancel")
    assert r.json()["late_cancellation"] is True
    w = wallet(client, h)
    # Moitié rendue (9), moitié consommée et versée au partenaire (9).
    assert (w["available"], w["reserved"], w["consumed"]) == (31, 0, 9)
    assert r.json()["refunded_credits"] == 9


def test_expired_hold_cannot_be_confirmed_and_frees_everything(client):
    h = login(client, make_customer(personal=40))
    oid = COUPE()
    slot = free_slot(client, oid)
    b = hold(client, h, oid, slot).json()
    with SessionLocal() as db, db.begin():
        db.execute(
            text("UPDATE bookings SET hold_expires_at = now() - interval '1 second' WHERE id = :id"), {"id": b["id"]}
        )
    r = post(client, h, f"/api/v1/bookings/{b['id']}/confirm")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "hold_expired"
    assert client.get(f"/api/v1/bookings/{b['id']}", headers=h).json()["status"] == "expired"
    assert wallet(client, h)["available"] == 40
    # Le créneau est de nouveau réservable par quelqu'un d'autre.
    other = login(client, make_customer(personal=40))
    assert hold(client, other, oid, slot).status_code == 201


def test_expire_job_releases_due_holds(client):
    h = login(client, make_customer(personal=40))
    oid = CERAMIQUE()
    b = hold(client, h, oid, free_slot(client, oid)).json()
    with SessionLocal() as db, db.begin():
        db.execute(text("UPDATE bookings SET hold_expires_at = now() - interval '1 second' WHERE id = :id"),
                   {"id": b["id"]})
    with SessionLocal() as db, db.begin():
        assert booking_service.expire_due_holds(db) >= 1
    assert wallet(client, h)["available"] == 40
    with SessionLocal() as db:
        reserved = db.scalar(text("SELECT reserved FROM session_inventories i JOIN bookings b ON b.inventory_id = i.id "
                                  "WHERE b.id = :id"), {"id": b["id"]})
    assert reserved == 0


# ---------------------------------------------------------------- idempotence


def test_idempotency_replay_mismatch_and_duplicate_effect(client):
    h = login(client, make_customer(personal=100))
    oid = COUPE()
    slot = free_slot(client, oid)
    key = uuid.uuid4().hex
    first = hold(client, h, oid, slot, key=key)
    again = hold(client, h, oid, slot, key=key)
    assert first.status_code == again.status_code == 201
    assert again.headers.get("Idempotent-Replayed") == "true"
    assert first.json()["id"] == again.json()["id"]
    # Même clé, autre corps : refus.
    other_slot = free_slot(client, oid)
    assert hold(client, h, oid, other_slot, key=key).status_code == 422
    # Autre clé, même effet métier : refus (pas de seconde réservation).
    dup = hold(client, h, oid, slot)
    assert dup.status_code == 409 and dup.json()["detail"]["code"] == "duplicate_booking"
    assert wallet(client, h)["reserved"] == 18


def test_idempotency_key_is_required(client):
    h = login(client, make_customer(personal=40))
    oid = COUPE()
    r = client.post("/api/v1/bookings", json={"offer_id": oid, "starts_at": free_slot(client, oid)["starts_at"]},
                    headers=h)
    assert r.status_code == 422


# ---------------------------------------------------------------- concurrence


def _race(n: int, fn):
    barrier = Barrier(n)

    def run(i):
        barrier.wait()
        return fn(i)

    with ThreadPoolExecutor(n) as pool:
        return list(pool.map(run, range(n)))


def test_exclusive_resource_has_a_single_winner():
    oid = COUPE()
    with TestClient(app) as c:
        slot = free_slot(c, oid)
        customers = [login(c, make_customer(personal=40)) for _ in range(8)]

    def attempt(i):
        with TestClient(app) as c:
            return hold(c, customers[i], oid, slot).status_code

    codes = _race(8, attempt)
    assert codes.count(201) == 1, codes
    assert set(codes) <= {201, 409}
    with TestClient(app) as c:
        reserved = sorted(wallet(c, h)["reserved"] for h in customers)
    assert reserved == [0] * 7 + [18]


def test_collective_capacity_is_never_exceeded():
    oid = CERAMIQUE()  # capacité 8
    with TestClient(app) as c:
        slot = free_slot(c, oid)
        customers = [login(c, make_customer(personal=40)) for _ in range(12)]

    def attempt(i):
        with TestClient(app) as c:
            r = hold(c, customers[i], oid, slot)
            return r.status_code, (r.json().get("detail") or {}).get("code") if r.status_code != 201 else None

    results = _race(12, attempt)
    assert sum(1 for s, _ in results if s == 201) == 8, results
    assert {code for s, code in results if s != 201} == {"slot_full"}
    with SessionLocal() as db:
        assert db.scalar(
            text("SELECT reserved FROM session_inventories WHERE offer_id = :o AND starts_at = :s"),
            {"o": oid, "s": slot["starts_at"]},
        ) == 8


def test_parallel_holds_never_overdraw_a_wallet():
    oid = COUPE()
    with TestClient(app) as c:
        h = login(c, make_customer(personal=20))  # une seule réservation de 18 possible
        slots = [free_slot(c, oid) for _ in range(5)]

    def attempt(i):
        with TestClient(app) as c:
            return hold(c, h, oid, slots[i]).status_code

    codes = _race(5, attempt)
    assert codes.count(201) == 1, codes
    with TestClient(app) as c:
        w = wallet(c, h)
    assert (w["available"], w["reserved"]) == (2, 18)


# ---------------------------------------------------------------- journal


def test_unbalanced_journal_is_rejected_at_commit():
    with SessionLocal() as db:
        lot_id, wallet_id = db.execute(text("SELECT id, wallet_id FROM credit_lots LIMIT 1")).one()
        j = CreditJournal(wallet_id=wallet_id, kind="adjustment", memo="test déséquilibré")
        db.add(j)
        db.flush()
        db.add(CreditJournalLine(journal_id=j.id, lot_id=lot_id, account="available", amount=5))
        db.add(CreditJournalLine(journal_id=j.id, lot_id=lot_id, account="issuance", amount=-4))
        db.flush()  # pas encore d'erreur : le contrôle est différé
        with pytest.raises(DBAPIError, match="déséquilibrée"):
            db.commit()


def test_journal_is_append_only():
    with SessionLocal() as db:
        with pytest.raises(DBAPIError, match="ajout seul"):
            db.execute(text("UPDATE credit_journal_lines SET amount = amount WHERE id = (SELECT id FROM credit_journal_lines LIMIT 1)"))
        db.rollback()
        with pytest.raises(DBAPIError, match="ajout seul"):
            db.execute(text("DELETE FROM credit_journals WHERE id = (SELECT id FROM credit_journals LIMIT 1)"))
        db.rollback()


def test_projections_match_rebuild_from_journal():
    with SessionLocal() as db:
        rebuilt = wallet_service.rebuild_balances(db)
        for bal in db.scalars(select(CreditLotBalance)):
            expected = rebuilt.get(bal.lot_id, {"available": 0, "reserved": 0, "consumed": 0, "expired": 0})
            assert (bal.available, bal.reserved, bal.consumed, bal.expired) == (
                expected["available"], expected["reserved"], expected["consumed"], expected["expired"],
            ), bal.lot_id
        # Toutes les écritures sont équilibrées.
        assert db.scalar(text(
            "SELECT count(*) FROM (SELECT journal_id FROM credit_journal_lines GROUP BY journal_id "
            "HAVING sum(amount) <> 0) x"
        )) == 0


# ---------------------------------------------------------------- partenaire


def test_external_block_prevents_booking(client):
    oid = COUPE()
    slot = free_slot(client, oid)
    start = datetime.fromisoformat(slot["starts_at"])
    with SessionLocal() as db, db.begin():
        loc_id, res_id = db.execute(
            select(Location.id, Resource.id)
            .join(Resource, Resource.location_id == Location.id)
            .where(Location.slug == "atelier-belle-venue", Resource.name == "Sarah")
        ).one()
        booking_service.block_resource(
            db, location_id=loc_id, resource_id=res_id, start=start, end=start + timedelta(minutes=30),
            reason="Réservation téléphonique", created_by=None,
        )
    h = login(client, make_customer(personal=40))
    r = hold(client, h, oid, slot)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "slot_unavailable"


def test_partner_sees_bookings_of_the_day(client):
    h = login(client, make_customer(personal=40))
    oid = COUPE()
    slot = free_slot(client, oid)
    b = hold(client, h, oid, slot).json()
    post(client, h, f"/api/v1/bookings/{b['id']}/confirm")
    partner = login(client, "partenaire@xpass.demo")
    day = b["local_start"][:10]
    rows = client.get("/api/v1/partner/bookings", headers=partner, params={"date": day}).json()
    mine = [r for r in rows if r["id"] == b["id"]]
    assert mine and mine[0]["resource_name"] == "Sarah" and mine[0]["status"] == "confirmed"
    assert client.get("/api/v1/partner/bookings", headers=h).status_code == 403
