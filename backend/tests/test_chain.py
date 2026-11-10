"""Admin crée un service RH, le RH crée un commerçant, le catalogue client le voit."""
import uuid

from sqlalchemy import select

from app.core.security import issue_dev_token
from app.db.session import SessionLocal
from app.modules.directory import service as directory
from app.modules.identity.models import User
from tests.conftest import login
from tests.test_employer import make_org


def _place():
    return directory.Place(
        label="5 Rue de la Roquette 75011 Paris", latitude=48.8534, longitude=2.3711, score=0.95,
        housenumber="5", street="Rue de la Roquette", postal_code="75011", city="Paris",
        district="Paris 11e Arrondissement",
    )


def test_admin_rh_merchant_reaches_the_client_catalog(client, monkeypatch):
    monkeypatch.setattr(directory, "geocode", lambda *a: _place())
    admin = login(client, "admin@xpass.demo")
    hr_email = f"rh-{uuid.uuid4().hex[:8]}@exemple.fr"
    created = client.post("/api/v1/admin/organizations", headers=admin, json={
        "name": f"Service {uuid.uuid4().hex[:6]}", "city_label": "Paris", "hr_email": hr_email,
    })
    assert created.status_code == 201, created.text
    org_id = created.json()["id"]

    with SessionLocal() as db:
        uid = db.scalar(select(User.id).where(User.email == hr_email))
    token, _ = issue_dev_token(str(uid))
    hr = {"Authorization": f"Bearer {token}"}

    venue = f"Lieu {uuid.uuid4().hex[:8]}"
    merchant = client.post("/api/v1/company/merchants", headers=hr, json={
        "display_name": f"Commerce {uuid.uuid4().hex[:6]}",
        "owner_email": f"gerant-{uuid.uuid4().hex[:8]}@exemple.fr",
        "location_name": venue,
        "subcategory_slug": "coiffure",
        "address_line": "5 rue de la Roquette",
        "postal_code": "75011",
        "city": "Paris",
        "description": "Coupe sur rendez-vous.",
        "price_credits": 8,
    })
    assert merchant.status_code == 201, merchant.text
    assert merchant.json()["venues"][0]["status"] == "published"
    assert merchant.json()["venues"][0]["name"] == venue

    listed = client.get("/api/v1/company/merchants", headers=hr)
    assert listed.status_code == 200
    assert any(v["name"] == venue for row in listed.json() for v in row["venues"])

    catalog = client.get("/api/v1/catalog/locations", params={"q": venue, "city": "paris"})
    assert catalog.status_code == 200, catalog.text
    assert any(item["name"] == venue for item in catalog.json()["items"])

    stranger = login(client, make_org()[1])
    assert all(v["name"] != venue for row in client.get("/api/v1/company/merchants", headers=stranger).json() for v in row["venues"])
    refused = client.post("/api/v1/company/merchants", headers=login(client, "partenaire@xpass.demo"), json={
        "display_name": "Hors service", "owner_email": "a@b.fr", "location_name": "Lieu refuse",
        "subcategory_slug": "coiffure", "address_line": "5 rue de la Roquette", "postal_code": "75011",
        "city": "Paris", "price_credits": 8,
    })
    assert refused.status_code == 403, refused.text

    orgs = client.get("/api/v1/admin/organizations", headers=admin).json()
    mine = next(o for o in orgs if o["id"] == org_id)
    assert any(v["name"] == venue for m in mine["merchants"] for v in m["venues"])
