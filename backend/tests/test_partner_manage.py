"""Gestion de l'établissement par le commerçant (lot 5)."""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.modules.catalog.models import Location
from tests.conftest import login
from tests.test_bookings import free_slot, hold, make_customer, post


def _loc() -> str:
    with SessionLocal() as db:
        return str(db.scalar(select(Location.id).where(Location.slug == "atelier-belle-venue")))


def _base() -> str:
    return f"/api/v1/partner/locations/{_loc()}"


def _owner(client):
    return login(client, "partenaire@xpass.demo")


def _staff(client):
    from tests.test_redemption import new_operator

    return login(client, new_operator())


def _manage(client, h) -> dict:
    r = client.get(f"{_base()}/manage", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _new_resource(client, h, name: str) -> str:
    assert client.post(f"{_base()}/resources", json={"name": name, "role_label": "Coiffeuse"}, headers=h).status_code == 201
    return next(r["id"] for r in _manage(client, h)["resources"] if r["name"] == name)


def _new_offer(client, h, title: str, resource_id: str, publish=True) -> dict:
    body = {"booking_mode": "resource_slot", "title": title, "summary": "Test", "duration_min": 30, "price_credits": 12,
            "resource_ids": [resource_id], "publish": publish}
    r = client.post(f"{_base()}/offers", json=body, headers=h)
    assert r.status_code == 201, r.text
    return next(o for o in _manage(client, h)["offers"] if o["current"]["title"] == title)


# ---------------------------------------------------------------- droits


def test_rights_owner_edits_staff_reads_others_refused(client):
    owner, staff, customer = _owner(client), _staff(client), login(client, make_customer())
    assert _manage(client, owner)["can_edit"] is True
    assert _manage(client, staff)["can_edit"] is False
    assert client.get(f"{_base()}/manage", headers=customer).status_code == 403
    r = client.post(f"{_base()}/resources", json={"name": "X", "role_label": "Y"}, headers=staff)
    assert r.status_code == 403 and "responsable" in r.json()["detail"]["message"]
    rh = login(client, "rh@xpass.demo")
    assert client.patch(_base(), json={"description": "pirate"}, headers=rh).status_code == 403
    with SessionLocal() as db:
        other = db.scalar(select(Location.id).where(Location.slug == "le-cercle"))
    assert client.get(f"/api/v1/partner/locations/{other}/manage", headers=owner).status_code == 403


# ---------------------------------------------------------------- prestations


def test_offer_lifecycle_and_versioning_keeps_booked_price(client):
    owner = _owner(client)
    rid = _new_resource(client, owner, f"Inès {uuid.uuid4().hex[:4]}")
    title = f"Brushing test {uuid.uuid4().hex[:4]}"
    offer = _new_offer(client, owner, title, rid)
    assert offer["is_active"] and offer["current"]["version"] == 1 and offer["resource_ids"] == [rid]

    # Publiée : visible et réservable au prix de la version 1.
    detail = client.get("/api/v1/catalog/locations/atelier-belle-venue").json()
    assert any(o["id"] == offer["id"] for o in detail["offers"])
    customer = login(client, make_customer(personal=50))
    b = hold(client, customer, offer["id"], free_slot(client, offer["id"])).json()
    post(client, customer, f"/api/v1/bookings/{b['id']}/confirm")

    # Nouvelle version : nouveau prix pour les prochaines réservations, l'ancienne réservation est intacte.
    body = {**{k: offer["current"][k] for k in ("title", "summary", "duration_min", "participants_min",
                                                 "participants_max", "capacity", "free_cancellation_hours")},
            "price_credits": 20, "resource_ids": [rid]}
    assert client.put(f"{_base()}/offers/{offer['id']}", json=body, headers=owner).status_code == 200
    updated = next(o for o in _manage(client, owner)["offers"] if o["id"] == offer["id"])
    assert updated["current"]["version"] == 2 and updated["current"]["price_credits"] == 20
    assert updated["versions_count"] == 2
    booked = client.get(f"/api/v1/bookings/{b['id']}", headers=customer).json()
    assert booked["total_credits"] == 12 and booked["price_credits_per_person"] == 12

    # La ressource a une réservation à venir : impossible de la désactiver.
    r = client.put(f"{_base()}/resources/{rid}", json={"name": "Inès", "role_label": "Coiffeuse", "active": False},
                   headers=owner)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "has_future_bookings"

    # Dépublier retire la prestation du catalogue sans toucher aux réservations.
    assert client.post(f"{_base()}/offers/{offer['id']}/active", json={"active": False}, headers=owner).status_code == 200
    detail = client.get("/api/v1/catalog/locations/atelier-belle-venue").json()
    assert all(o["id"] != offer["id"] for o in detail["offers"])
    assert client.get(f"/api/v1/bookings/{b['id']}", headers=customer).json()["status"] == "confirmed"


def test_offer_validation(client):
    owner = _owner(client)
    base = {"title": "Sans ressource", "duration_min": 30, "price_credits": 10}
    r = client.post(f"{_base()}/offers", json={**base, "booking_mode": "resource_slot", "resource_ids": []}, headers=owner)
    assert r.json()["detail"]["code"] == "resource_required"
    r = client.post(f"{_base()}/offers", json={**base, "booking_mode": "capacity_session"}, headers=owner)
    assert r.json()["detail"]["code"] == "capacity_required"
    r = client.post(f"{_base()}/offers", json={**base, "duration_min": 20, "booking_mode": "capacity_session",
                                               "capacity": 5}, headers=owner)
    assert r.json()["detail"]["code"] == "invalid_duration"
    r = client.post(f"{_base()}/offers", json={**base, "booking_mode": "external_ticket"}, headers=owner)
    assert r.status_code == 422
    r = client.post(f"{_base()}/offers", json={**base, "booking_mode": "resource_slot",
                                               "resource_ids": [str(uuid.uuid4())]}, headers=owner)
    assert r.json()["detail"]["code"] == "invalid_resource"


def test_deactivating_last_resource_unpublishes_offer(client):
    owner = _owner(client)
    rid = _new_resource(client, owner, f"Maya {uuid.uuid4().hex[:4]}")
    offer = _new_offer(client, owner, f"Soin test {uuid.uuid4().hex[:4]}", rid)
    r = client.put(f"{_base()}/resources/{rid}", json={"name": "Maya", "role_label": "Esthéticienne", "active": False},
                   headers=owner)
    assert r.status_code == 200
    data = _manage(client, owner)
    assert next(o for o in data["offers"] if o["id"] == offer["id"])["is_active"] is False
    assert next(x for x in data["resources"] if x["id"] == rid)["is_active"] is False
    r = client.post(f"{_base()}/offers/{offer['id']}/active", json={"active": True}, headers=owner)
    assert r.json()["detail"]["code"] == "resource_required"


# ---------------------------------------------------------------- horaires et fermetures


def test_hours_replace_validates_and_reports_impact(client):
    owner = _owner(client)
    original = _manage(client, owner)["hours"]
    bad = [{"weekday": 0, "opens_at": "09:00", "closes_at": "13:00"}, {"weekday": 0, "opens_at": "12:00", "closes_at": "18:00"}]
    assert client.put(f"{_base()}/hours", json=bad, headers=owner).json()["detail"]["code"] == "overlapping_hours"
    assert client.put(f"{_base()}/hours", json=[{"weekday": 1, "opens_at": "18:00", "closes_at": "09:00"}],
                      headers=owner).json()["detail"]["code"] == "invalid_hours"
    # Ouverture réduite au mardi matin : les réservations à venir ailleurs sont signalées, pas annulées.
    with SessionLocal() as db:
        active_before = db.scalar(text("SELECT count(*) FROM bookings WHERE status IN ('held','confirmed')"))
    r = client.put(f"{_base()}/hours", json=[{"weekday": 1, "opens_at": "09:00", "closes_at": "10:00"}], headers=owner)
    assert r.status_code == 200 and r.json()["bookings_outside_hours"] >= 1
    with SessionLocal() as db:
        assert db.scalar(text("SELECT count(*) FROM bookings WHERE status IN ('held','confirmed')")) == active_before
    # Restauration.
    assert client.put(f"{_base()}/hours", json=original, headers=owner).status_code == 200
    assert _manage(client, owner)["hours"] == original


def test_exceptional_closure_removes_slots(client):
    owner = _owner(client)
    offer_id = next(o["id"] for o in _manage(client, owner)["offers"] if o["current"]["title"] == "Coupe et coiffage")
    days = client.get(f"/api/v1/catalog/offers/{offer_id}/availability").json()["days"]
    day = [d["date"] for d in days if d["open"]][-1]
    r = client.post(f"{_base()}/exceptions", json={"day": day, "is_closed": True, "reason": "Inventaire"}, headers=owner)
    assert r.status_code == 201
    assert client.post(f"{_base()}/exceptions", json={"day": day}, headers=owner).json()["detail"]["code"] == "duplicate_day"
    av = client.get(f"/api/v1/catalog/offers/{offer_id}/availability", params={"date": day}).json()
    assert av["slots"] == [] and not next(d for d in av["days"] if d["date"] == day)["open"]
    exc = next(e for e in _manage(client, owner)["exceptions"] if e["day"] == day)
    assert exc["reason"] == "Inventaire"
    assert client.delete(f"{_base()}/exceptions/{exc['id']}", headers=owner).status_code == 200
    av = client.get(f"/api/v1/catalog/offers/{offer_id}/availability", params={"date": day}).json()
    assert av["slots"]
    past = (datetime.now(UTC) - timedelta(days=2)).date().isoformat()
    assert client.post(f"{_base()}/exceptions", json={"day": past}, headers=owner).json()["detail"]["code"] == "past_day"


# ---------------------------------------------------------------- blocages


def test_staff_can_block_and_unblock_a_slot(client):
    staff, owner = _staff(client), _owner(client)
    data = _manage(client, owner)
    lina = next(r["id"] for r in data["resources"] if r["name"] == "Lina")
    start = (datetime.now(UTC) + timedelta(days=21)).replace(hour=12, minute=0, second=0, microsecond=0, tzinfo=None)
    body = {"resource_id": lina, "local_start": start.isoformat(), "local_end": (start + timedelta(hours=1)).isoformat(),
            "reason": "Rendez-vous téléphonique"}
    assert client.post(f"{_base()}/blocks", json=body, headers=staff).status_code == 201
    overlap = client.post(f"{_base()}/blocks", json={**body, "local_start": (start + timedelta(minutes=30)).isoformat(),
                                                     "local_end": (start + timedelta(hours=2)).isoformat()}, headers=staff)
    assert overlap.status_code == 409 and overlap.json()["detail"]["code"] == "overlap"
    blocks = client.get(f"{_base()}/blocks", params={"start": start.date().isoformat()}, headers=staff).json()
    block = next(b for b in blocks if b["reason"] == "Rendez-vous téléphonique")
    assert block["local_start"] == start.isoformat(timespec="minutes") and block["resource_name"] == "Lina"
    assert client.delete(f"{_base()}/blocks/{block['id']}", headers=staff).status_code == 200
    assert client.post(f"{_base()}/blocks", json=body, headers=staff).status_code == 201  # la plage est libérée
    again = client.get(f"{_base()}/blocks", params={"start": start.date().isoformat()}, headers=staff).json()
    client.delete(f"{_base()}/blocks/{next(b['id'] for b in again if b['reason'] == body['reason'])}", headers=staff)


def test_location_update_and_review_url(client):
    owner = _owner(client)
    before = _manage(client, owner)
    r = client.patch(_base(), json={"description": before["description"], "review_url": "http://exemple.fr"}, headers=owner)
    assert r.json()["detail"]["code"] == "invalid_review_url"
    payload = {"description": before["description"], "access_info": "Métro Parmentier", "meeting_point": None,
               "wheelchair_accessible": True, "review_url": "https://g.page/r/exemple/review"}
    assert client.patch(_base(), json=payload, headers=owner).status_code == 200
    after = _manage(client, owner)
    assert after["review_url"] == "https://g.page/r/exemple/review" and after["wheelchair_accessible"] is True
    client.patch(_base(), json={"description": before["description"], "access_info": before["access_info"],
                                "meeting_point": before["meeting_point"],
                                "wheelchair_accessible": before["wheelchair_accessible"],
                                "review_url": before["review_url"]}, headers=owner)


def test_week_planning(client):
    owner = _owner(client)
    monday = datetime.now(UTC).date()
    r = client.get("/api/v1/partner/bookings", params={"date": monday.isoformat(), "days": 7}, headers=owner)
    assert r.status_code == 200
    for b in r.json():
        assert monday.isoformat() <= b["local_start"][:10] < (monday + timedelta(days=7)).isoformat()
