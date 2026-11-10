"""Plusieurs établissements par commerçant ; modification du nom, de l'activité et de l'adresse validée par XPASS."""
import uuid

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.catalog.models import Location
from app.modules.notifications.service import build
from app.modules.platform.models import OutboxEvent
from tests.conftest import login
from tests.test_partners import _place, application, real_user, services  # noqa: F401 (fixture)


def _partner(client) -> tuple[dict, str]:
    h, _ = real_user()
    r = client.post("/api/v1/partners/applications", headers=h, json=application())
    assert r.status_code == 201, r.text
    return h, r.json()["location_id"]


def _new_location(**over) -> dict:
    return {"location_name": "Salon Lumière Bastille", "subcategory_slug": "coiffure", "kind_label": "Salon de coiffure",
            "address_line": "5 rue de la Roquette", "postal_code": "75011", "city": "Paris", "description": "", **over}


def test_owner_adds_second_location(client, services):
    h, first = _partner(client)
    r = client.post(f"/api/v1/partner/locations/{first}/siblings", headers=h, json=_new_location())
    assert r.status_code == 201, r.text
    locations = client.get("/api/v1/partner/locations", headers=h).json()
    assert len(locations) == 2 and {x["status"] for x in locations} == {"draft"}
    services["place"] = None
    bad = client.post(f"/api/v1/partner/locations/{first}/siblings", headers=h, json=_new_location(location_name="Autre"))
    assert bad.status_code == 422 and bad.json()["detail"]["code"] == "address_not_found"
    # Un autre compte ne peut pas ajouter d'établissement à ce commerçant.
    other, _ = real_user()
    assert client.post(f"/api/v1/partner/locations/{first}/siblings", headers=other, json=_new_location()).status_code == 403


def test_change_request_applied_after_validation(client, services):
    h, loc = _partner(client)
    services["place"] = _place()
    services["place"].label, services["place"].latitude = "20 Rue Oberkampf 75011 Paris", 48.8650
    services["place"].housenumber, services["place"].street = "20", "Rue Oberkampf"
    body = {"name": "Salon Lumière Oberkampf", "address_line": "20 rue Oberkampf", "postal_code": "75011", "city": "Paris"}
    r = client.post(f"/api/v1/partner/locations/{loc}/change-requests", headers=h, json=body)
    assert r.status_code == 201, r.text
    assert set(r.json()["changes"]) == {"name", "address"}
    # Une demande à la fois ; la fiche ne change pas avant validation.
    assert client.post(f"/api/v1/partner/locations/{loc}/change-requests", headers=h, json=body).status_code == 409
    with SessionLocal() as db:
        assert db.get(Location, uuid.UUID(loc)).name == "Salon Lumière Roquette"

    admin = login(client, "admin@xpass.demo")
    pending = client.get("/api/v1/admin/change-requests", headers=admin).json()
    req = next(x for x in pending if x["location_id"] == loc)
    assert client.post(f"/api/v1/admin/change-requests/{req['id']}/decision", headers=admin,
                       json={"approve": True, "reason": "Nouvelle adresse vérifiée"}).status_code == 200
    with SessionLocal() as db:
        location = db.get(Location, uuid.UUID(loc))
        assert location.name == "Salon Lumière Oberkampf" and location.address_line == "20 Rue Oberkampf"
        assert location.geocode_label == "20 Rue Oberkampf 75011 Paris"
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "location.change_decided",
                                                    OutboxEvent.aggregate_id == uuid.UUID(req["id"])))
        assert "acceptée" in build(db, event).subject
    # Déjà traitée ; nouvelle demande refusée par XPASS avec motif.
    assert client.post(f"/api/v1/admin/change-requests/{req['id']}/decision", headers=admin,
                       json={"approve": False, "reason": "doublon"}).status_code == 409
    r2 = client.post(f"/api/v1/partner/locations/{loc}/change-requests", headers=h, json={"kind_label": "Barbier"})
    assert client.post(f"/api/v1/admin/change-requests/{r2.json()['id']}/decision", headers=admin,
                       json={"approve": False, "reason": "Activité non conforme"}).status_code == 200
    history = client.get(f"/api/v1/partner/locations/{loc}/change-requests", headers=h).json()
    assert history[0]["status"] == "rejected" and history[0]["decision_reason"] == "Activité non conforme"
    # Sans changement réel : refus explicite.
    same = client.post(f"/api/v1/partner/locations/{loc}/change-requests", headers=h, json={"name": "Salon Lumière Oberkampf"})
    assert same.status_code == 422 and same.json()["detail"]["code"] == "no_change"
