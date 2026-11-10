"""Réseau de commerçants : candidature (SIRET vérifié, adresse géocodée), photos, validation, lieux de démo.

Les services publics (annuaire, Base Adresse Nationale) sont simulés : aucun appel réseau pendant les tests.
"""
import io
import uuid

import pytest
from PIL import Image
from sqlalchemy import select

from app.core.security import issue_dev_token
from app.db.session import SessionLocal
from app.modules.catalog import photos
from app.modules.catalog.models import Location, Merchant
from app.modules.directory import service as directory
from app.modules.identity.models import Membership, User
from app.modules.notifications.service import build
from app.modules.platform.models import OutboxEvent
from tests.conftest import login

SIRET = "80345158100018"


def _company(siret=SIRET, active=True):
    return directory.Company(siret=siret, siren=siret[:9], legal_name="SALON LUMIERE SAS", trade_name="Salon Lumière",
                             active=active, address="5 RUE DE LA ROQUETTE 75011 PARIS", postal_code="75011",
                             city="PARIS", naf_code="96.02A", head_office=True)


def _place(score=0.95):
    return directory.Place(label="5 Rue de la Roquette 75011 Paris", latitude=48.8534, longitude=2.3711, score=score,
                           housenumber="5", street="Rue de la Roquette", postal_code="75011", city="Paris",
                           district="Paris 11e Arrondissement")


@pytest.fixture
def services(monkeypatch):
    state = {"company": _company(), "place": _place(), "down": False, "stored": []}

    def lookup(siret):
        if state["down"]:
            raise directory.ServiceUnavailable("hors service")
        c = state["company"]
        return None if c is None else directory.Company(**{**c.as_dict(), "siret": siret, "siren": siret[:9]})

    monkeypatch.setattr(directory, "lookup_siret", lookup)
    monkeypatch.setattr(directory, "geocode", lambda *a: state["place"])
    monkeypatch.setattr(photos, "store", lambda key, data: state["stored"].append((key, len(data))))
    return state


def real_user() -> tuple[dict, uuid.UUID]:
    """Compte réel (non démo) avec un jeton de test : la connexion de démonstration ne l'accepte pas."""
    with SessionLocal() as db, db.begin():
        u = User(email=f"gerant-{uuid.uuid4().hex[:8]}@exemple.fr", display_name="Gérant", is_demo=False)
        db.add(u)
        db.flush()
        uid = u.id
    token, _ = issue_dev_token(str(uid))
    return {"Authorization": f"Bearer {token}"}, uid


def _siret() -> str:
    """SIRET de test valide (clé de Luhn) et unique."""
    while True:
        base = f"{uuid.uuid4().int % 10**13:013d}"
        for k in range(10):
            s = base + str(k)
            if directory.siret_is_valid(s):
                return s


def application(**over) -> dict:
    return {"siret": _siret(), "display_name": "Salon Lumière", "contact_phone": "01 23 45 67 89",
            "location_name": "Salon Lumière Roquette", "subcategory_slug": "coiffure", "kind_label": "Salon de coiffure",
            "address_line": "5 rue de la Roquette", "postal_code": "75011", "city": "Paris",
            "description": "Coupes et couleurs sur rendez-vous.", **over}


def _png(side=800) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (side, side), (200, 120, 90)).save(buf, "PNG")
    return buf.getvalue()


def test_siret_validation():
    assert directory.siret_is_valid("80345158100018")
    assert directory.siret_is_valid("35600000000048")  # La Poste : règle particulière
    assert not directory.siret_is_valid("80345158100019")
    assert not directory.siret_is_valid("8034515810001")
    assert directory.street_from_label("DIRECTION GENERALE 9 RUE DU COLONEL PIERRE AVIA 75015 PARIS", "75015", "PARIS") == "9 RUE DU COLONEL PIERRE AVIA"
    assert directory.district_label("75011", "Paris") == "Paris 11e"
    assert directory.district_label("75001", "Paris") == "Paris 1er"
    assert directory.district_label("33000", "Bordeaux") == "Bordeaux"


def test_application_creates_pending_partner_and_draft_location(client, services):
    h, uid = real_user()
    body = application()
    preview = client.get(f"/api/v1/partners/siret/{body['siret']}", headers=h)
    assert preview.status_code == 200 and preview.json()["legal_name"] == "SALON LUMIERE SAS"

    r = client.post("/api/v1/partners/applications", headers=h, json=body)
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["company_check"] == "verified" and "Roquette" in out["address_label"]

    with SessionLocal() as db:
        merchant = db.get(Merchant, uuid.UUID(out["merchant_id"]))
        loc = db.get(Location, uuid.UUID(out["location_id"]))
        assert merchant.commercial_status == "pending_review" and not merchant.is_demo
        assert merchant.legal_name == "SALON LUMIERE SAS" and merchant.siret == body["siret"]
        assert loc.status == "draft" and loc.district_label == "Paris 11e" and loc.geocode_score == 0.95
        assert db.scalar(select(Membership.role).where(Membership.user_id == uid, Membership.scope_id == merchant.id)) == "merchant_owner"
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "merchant.applied",
                                                    OutboxEvent.aggregate_id == merchant.id))
        mail = build(db, event)
        assert "candidature" in mail.subject and "http" not in mail.body

    # Invisible des clients tant que XPASS n'a pas validé et publié.
    slugs = [x["slug"] for x in client.get("/api/v1/catalog/locations?city=paris&limit=50").json()["items"]]
    assert all(s != loc.slug for s in slugs)

    # Le responsable accède à son portail et ajoute une photo (réencodée en JPEG).
    assert client.get(f"/api/v1/partner/locations/{loc.id}/manage", headers=h).status_code == 200
    up = client.post(f"/api/v1/partner/locations/{loc.id}/cover", headers=h,
                     files={"file": ("salon.png", _png(), "image/png")})
    assert up.status_code == 200, up.text
    assert up.json()["image_key"].startswith(f"merchants/{merchant.id}/") and services["stored"]
    bad = client.post(f"/api/v1/partner/locations/{loc.id}/cover", headers=h,
                      files={"file": ("notes.txt", b"pas une image", "text/plain")})
    assert bad.status_code == 422
    small = client.post(f"/api/v1/partner/locations/{loc.id}/cover", headers=h,
                        files={"file": ("mini.png", _png(100), "image/png")})
    assert small.status_code == 422

    # Validation par l'administration puis publication : le lieu apparaît.
    admin = login(client, "admin@xpass.demo")
    detail = client.get(f"/api/v1/admin/merchants/{merchant.id}", headers=admin).json()
    assert detail["siret"] == body["siret"]
    assert detail["checks"][0]["ok"] and "actif" in detail["checks"][0]["detail"]
    assert client.post(f"/api/v1/admin/merchants/{merchant.id}/decision", headers=admin,
                       json={"decision": "approve", "reason": "SIRET et adresse vérifiés"}).status_code == 200
    assert client.post(f"/api/v1/admin/locations/{loc.id}/moderation", headers=admin,
                       json={"publish": True, "reason": "Fiche complète"}).status_code == 200
    slugs = [x["slug"] for x in client.get("/api/v1/catalog/locations?city=paris&limit=50").json()["items"]]
    assert loc.slug in slugs

    # Un second dossier n'est pas accepté tant que… ici le premier est validé : nouvelle candidature possible,
    # mais pas avec le même SIRET.
    dup = client.post("/api/v1/partners/applications", headers=h, json={**application(), "siret": body["siret"]})
    assert dup.status_code == 409


def test_application_rules(client, services):
    h, _ = real_user()
    assert client.post("/api/v1/partners/applications", headers=h,
                       json=application(siret="80345158100019")).status_code == 422  # clé invalide
    services["company"] = None
    r = client.post("/api/v1/partners/applications", headers=h, json=application())
    assert r.status_code == 422 and r.json()["detail"]["code"] == "siret_not_found"
    services["company"] = _company(active=False)
    assert client.post("/api/v1/partners/applications", headers=h, json=application()).json()["detail"]["code"] == "siret_closed"
    services["company"] = _company()
    services["place"] = None
    assert client.post("/api/v1/partners/applications", headers=h, json=application()).json()["detail"]["code"] == "address_not_found"
    services["place"] = _place()

    # Annuaire indisponible : candidature acceptée, mais marquée « à vérifier » (jamais « vérifiée »).
    services["down"] = True
    r = client.post("/api/v1/partners/applications", headers=h, json=application())
    assert r.status_code == 201 and r.json()["company_check"] == "unavailable"
    detail = client.get(f"/api/v1/admin/merchants/{r.json()['merchant_id']}", headers=login(client, "admin@xpass.demo")).json()
    assert detail["checks"][0]["ok"] is False and "à vérifier" in detail["checks"][0]["detail"]

    # Un dossier à la fois ; un compte de démonstration ne peut pas candidater.
    again = client.post("/api/v1/partners/applications", headers=h, json=application())
    assert again.status_code == 409 and again.json()["detail"]["code"] == "application_pending"
    demo = client.post("/api/v1/partners/applications", headers=login(client, "client@xpass.demo"), json=application())
    assert demo.status_code == 403


def test_demo_locations_can_be_hidden_and_shown(client):
    admin = login(client, "admin@xpass.demo")
    before = client.get("/api/v1/catalog/locations?city=paris&limit=50").json()["total"]
    r = client.post("/api/v1/admin/demo-locations", headers=admin, json={"visible": False, "reason": "Vrais partenaires en ligne"})
    assert r.status_code == 200 and r.json()["changed"] > 0
    with SessionLocal() as db:
        assert db.scalar(select(Location.id).where(Location.is_demo.is_(True), Location.status == "published")) is None
    assert client.get("/api/v1/catalog/locations?city=paris&limit=50").json()["total"] < before
    assert client.get("/api/v1/admin/overview", headers=admin).json()["demo_locations"].get("hidden", 0) > 0
    assert client.post("/api/v1/admin/demo-locations", headers=admin,
                       json={"visible": True, "reason": "Réaffichage pour la démonstration"}).json()["changed"] > 0
    assert client.get("/api/v1/catalog/locations?city=paris&limit=50").json()["total"] == before
    assert client.post("/api/v1/admin/demo-locations", headers=login(client, "partenaire@xpass.demo"),
                       json={"visible": False, "reason": "tentative"}).status_code == 403
