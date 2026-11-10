import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import InvalidToken, issue_dev_token, verify_token
from tests.conftest import login


def test_me_requires_token(client):
    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer abc"}).status_code == 401


def test_dev_login_only_for_demo_accounts(client):
    r = client.post("/api/v1/auth/dev/login", json={"email": "inconnu@example.com"})
    assert r.status_code == 401


def test_me_returns_memberships(client):
    r = client.get("/api/v1/me", headers=login(client, "partenaire@xpass.demo"))
    assert r.status_code == 200
    m = r.json()["memberships"][0]
    assert m["role"] == "merchant_owner" and m["scope_name"] == "Atelier Belle venue"


def test_partner_sees_only_own_locations(client):
    r = client.get("/api/v1/partner/locations", headers=login(client, "partenaire@xpass.demo"))
    assert r.status_code == 200
    assert [loc["slug"] for loc in r.json()] == ["atelier-belle-venue"]


def test_role_isolation(client):
    partner = login(client, "partenaire@xpass.demo")
    hr = login(client, "rh@xpass.demo")
    admin = login(client, "admin@xpass.demo")
    assert client.get("/api/v1/admin/merchants", headers=partner).status_code == 403
    assert client.get("/api/v1/admin/merchants", headers=hr).status_code == 403
    assert client.get("/api/v1/partner/locations", headers=hr).status_code == 403
    assert client.get("/api/v1/company/organization", headers=partner).status_code == 403
    assert client.get("/api/v1/company/organization", headers=hr).json()["name"] == "Entreprise Démo Horizon"


def test_admin_lists_pending_merchants(client):
    r = client.get("/api/v1/admin/merchants", headers=login(client, "admin@xpass.demo"), params={"status": "pending_review"})
    body = r.json()
    assert body["by_commercial_status"]["pending_review"] == 2
    assert {m["commercial_status"] for m in body["items"]} == {"pending_review"}
    # Statut commercial et statut PSP sont distincts
    assert any(m["psp_status"] == "pending" for m in body["items"])


def test_production_refuses_dev_login():
    with pytest.raises(ValidationError):
        Settings(app_env="production", auth_dev_login_enabled=True, jwt_dev_secret="x" * 40)


def test_dev_token_rejected_when_dev_login_disabled():
    enabled = Settings(app_env="test", auth_dev_login_enabled=True, jwt_dev_secret="s" * 40)
    token, _ = issue_dev_token("00000000-0000-0000-0000-000000000001", enabled)
    disabled = Settings(app_env="production", auth_dev_login_enabled=False, jwt_dev_secret="s" * 40, psp_provider="")
    with pytest.raises(InvalidToken):
        verify_token(token, disabled)
