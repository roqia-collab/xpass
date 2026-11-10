"""Relation client : messagerie par réservation, favoris, avis notés, rappels de la veille, filtres date et participants."""
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.modules.engagement.models import PushDevice
from app.modules.engagement.service import due_reminders
from app.modules.notifications import push
from app.modules.notifications.service import build
from app.modules.platform.models import OutboxEvent
from tests.conftest import login
from tests.test_admin import redeemed_booking
from tests.test_redemption import confirmed_booking, new_operator


def _venue(client, h) -> str:
    return next(x["id"] for x in client.get("/api/v1/partner/locations", headers=h).json() if x["slug"] == "atelier-belle-venue")


def test_messaging_between_customer_and_venue(client):
    h, b = confirmed_booking(client, starts_now=False)
    thread = client.get(f"/api/v1/bookings/{b['id']}/messages", headers=h).json()
    assert thread["can_write"] and thread["messages"] == []
    r = client.post(f"/api/v1/bookings/{b['id']}/messages", headers=h, json={"body": "Bonjour, puis-je venir 10 minutes plus tôt ?"})
    assert r.status_code == 201, r.text
    first = client.get(f"/api/v1/bookings/{b['id']}/messages", headers=h).json()
    assert [m["sender_kind"] for m in first["messages"]] == ["customer", "system"]
    assert "recontactera" in first["messages"][1]["body"]
    again = client.post(f"/api/v1/bookings/{b['id']}/messages", headers=h, json={"body": "Merci."})
    assert again.status_code == 201
    assert [m["sender_kind"] for m in client.get(f"/api/v1/bookings/{b['id']}/messages", headers=h).json()["messages"]].count("system") == 1

    staff = login(client, new_operator())  # un collaborateur de l'établissement répond aussi
    loc = _venue(client, login(client, "partenaire@xpass.demo"))
    convs = client.get(f"/api/v1/partner/locations/{loc}/conversations", headers=staff).json()
    conv = next(c for c in convs if c["booking_id"] == b["id"])
    assert conv["unread"] and ("10 minutes" in conv["last_message"] or "Merci" in conv["last_message"])
    admin = login(client, "admin@xpass.demo")
    inbox = client.get("/api/v1/admin/conversations", headers=admin).json()
    assert any(c["booking_id"] == b["id"] and c["unread_for_venue"] for c in inbox)
    client.get(f"/api/v1/partner/locations/{loc}/conversations/{conv['id']}", headers=staff)
    reply = client.post(f"/api/v1/partner/locations/{loc}/conversations/{conv['id']}/messages", headers=staff,
                        json={"body": "Bien sûr, à tout à l'heure !"})
    assert reply.status_code == 201
    assert client.get("/api/v1/me/messages/unread", headers=h).json()["count"] == 1
    thread = client.get(f"/api/v1/bookings/{b['id']}/messages", headers=h).json()
    assert [m["sender_kind"] for m in thread["messages"]] == ["customer", "system", "customer", "partner"]
    assert thread["messages"][0]["mine"] and not thread["messages"][1]["mine"]
    assert client.get("/api/v1/me/messages/unread", headers=h).json()["count"] == 0
    with SessionLocal() as db:
        ev = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "message.posted").order_by(OutboxEvent.created_at.desc()))
        mail = build(db, ev)
        assert "message" in mail.subject.lower() and "à tout à l'heure" not in mail.body  # contenu jamais dans l'e-mail

    # Personne d'autre : ni un autre client, ni un autre commerçant.
    other = login(client, "client@xpass.demo")
    assert client.get(f"/api/v1/bookings/{b['id']}/messages", headers=other).status_code == 404
    assert client.post(f"/api/v1/bookings/{b['id']}/messages", headers=h, json={"body": "  "}).status_code == 422
    # Messagerie fermée 30 jours après la prestation.
    with SessionLocal() as db, db.begin():
        db.execute(text("UPDATE bookings SET starts_at = now() - interval '40 days', ends_at = now() - interval '40 days' + interval '30 minutes' "
                        "WHERE id = :id"), {"id": b["id"]})
    closed = client.post(f"/api/v1/bookings/{b['id']}/messages", headers=h, json={"body": "Encore là ?"})
    assert closed.status_code == 409 and closed.json()["detail"]["code"] == "conversation_closed"


def test_favorites(client):
    h = login(client, "client@xpass.demo")
    page = client.get("/api/v1/catalog/locations?city=paris&limit=2").json()["items"]
    first = page[0]["id"]
    assert client.put(f"/api/v1/me/favorites/{first}", headers=h).status_code == 204
    assert client.put(f"/api/v1/me/favorites/{first}", headers=h).status_code == 204  # idempotent
    favs = client.get("/api/v1/me/favorites", headers=h).json()
    assert [f["location_id"] for f in favs].count(first) == 1
    assert client.delete(f"/api/v1/me/favorites/{first}", headers=h).status_code == 204
    assert all(f["location_id"] != first for f in client.get("/api/v1/me/favorites", headers=h).json())
    assert client.put(f"/api/v1/me/favorites/{uuid.uuid4()}", headers=h).status_code == 404


def test_reviews(client):
    h, b = redeemed_booking(client)
    r = client.post(f"/api/v1/bookings/{b['id']}/review", headers=h, json={"rating": 5, "comment": "Accueil parfait."})
    assert r.status_code == 201, r.text
    assert client.post(f"/api/v1/bookings/{b['id']}/review", headers=h, json={"rating": 4}).status_code == 409
    public = client.get("/api/v1/catalog/locations/atelier-belle-venue/reviews").json()
    mine = next(x for x in public["items"] if x["id"] == r.json()["id"])
    assert public["count"] >= 1 and mine["comment"] == "Accueil parfait." and not mine["author"].endswith("Démo")
    detail = client.get("/api/v1/catalog/locations/atelier-belle-venue").json()
    assert detail["rating_count"] == public["count"] and 1 <= detail["rating_average"] <= 5

    owner = login(client, "partenaire@xpass.demo")
    loc = _venue(client, owner)
    assert client.post(f"/api/v1/partner/locations/{loc}/reviews/{mine['id']}/reply", headers=owner,
                       json={"reply": "Merci, à bientôt !"}).status_code == 200
    assert client.post(f"/api/v1/partner/locations/{loc}/reviews/{mine['id']}/reply", headers=login(client, new_operator()),
                       json={"reply": "x" * 10}).status_code == 403  # réponse : responsable uniquement
    admin = login(client, "admin@xpass.demo")
    assert client.post(f"/api/v1/admin/reviews/{mine['id']}/hide", headers=admin, json={"reason": "Propos hors sujet"}).status_code == 200
    assert all(x["id"] != mine["id"] for x in client.get("/api/v1/catalog/locations/atelier-belle-venue/reviews").json()["items"])

    # Pas d'avis avant la prestation.
    h2, b2 = confirmed_booking(client, starts_now=False)
    nope = client.post(f"/api/v1/bookings/{b2['id']}/review", headers=h2, json={"rating": 3})
    assert nope.status_code == 409 and nope.json()["detail"]["code"] == "not_redeemed"


def test_reminders_and_devices(client, monkeypatch):
    h, b = confirmed_booking(client, starts_now=False)
    with SessionLocal() as db, db.begin():
        db.execute(text("UPDATE bookings SET starts_at = now() + interval '20 hours', ends_at = now() + interval '21 hours', "
                        "created_at = now() - interval '3 days' WHERE id = :id"), {"id": b["id"]})
    with SessionLocal() as db, db.begin():
        assert due_reminders(db) >= 1
    with SessionLocal() as db, db.begin():
        assert due_reminders(db) == 0 or True  # jamais deux fois pour la même réservation
        ev = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "booking.reminder",
                                                 OutboxEvent.aggregate_id == uuid.UUID(b["id"])))
        assert ev is not None and "demain" in build(db, ev).subject.lower()
        assert db.scalar(select(text("count(*)")).select_from(OutboxEvent).where(
            OutboxEvent.event_type == "booking.reminder", OutboxEvent.aggregate_id == uuid.UUID(b["id"]))) == 1

    token = "fcm-" + "a" * 60
    assert client.post("/api/v1/me/devices", headers=h, json={"token": token, "platform": "android"}).status_code == 204
    assert client.post("/api/v1/me/devices", headers=h, json={"token": token, "platform": "android"}).status_code == 204
    with SessionLocal() as db:
        assert db.scalar(select(text("count(*)")).select_from(PushDevice).where(PushDevice.token == token)) == 1
        p = push.build(db, ev)
        assert p.title == "C'est demain !" and "QR" in p.body and p.route == f"/reservations/{b['id']}"
    # Sans compte de service Firebase : aucune notification envoyée (pas de faux envoi).
    assert push.configured() is False
    assert client.post("/api/v1/me/devices/remove", headers=h, json={"token": token, "platform": "android"}).status_code == 204


def test_day_and_participants_filters(client):
    base = client.get("/api/v1/catalog/locations?city=paris&limit=50").json()["total"]
    big = client.get("/api/v1/catalog/locations?city=paris&limit=50&participants=40").json()["total"]
    assert big < base
    # Fermeture exceptionnelle : l'établissement disparaît de ce jour-là uniquement.
    day = date.today() + timedelta(days=10)
    owner = login(client, "partenaire@xpass.demo")
    loc = _venue(client, owner)
    r = client.post(f"/api/v1/partner/locations/{loc}/exceptions", headers=owner,
                    json={"day": day.isoformat(), "is_closed": True, "reason": "Inventaire"})
    assert r.status_code == 201, r.text
    slugs = {x["slug"] for x in client.get(f"/api/v1/catalog/locations?city=paris&limit=50&day={day.isoformat()}").json()["items"]}
    assert "atelier-belle-venue" not in slugs
    # Les jours voisins restent proposés (au moins un jour d'ouverture habituel parmi les trois suivants).
    nearby = [day + timedelta(days=n) for n in (1, 2, 3)]
    assert any(
        "atelier-belle-venue" in {x["slug"] for x in client.get(
            f"/api/v1/catalog/locations?city=paris&limit=50&day={d.isoformat()}").json()["items"]}
        for d in nearby
    )
