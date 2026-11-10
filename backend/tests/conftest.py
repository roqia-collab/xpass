"""Les tests tournent contre un VRAI PostgreSQL/PostGIS (base xpass_test).

Usage : docker compose exec api pytest
"""
import os

# Doit précéder tout import de l'application (moteur créé à l'import).
_base = os.environ.get("DATABASE_URL", "postgresql+psycopg://xpass:xpass_dev@localhost:5432/xpass")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", _base.rsplit("/", 1)[0] + "/xpass_test")
os.environ["APP_ENV"] = "test"
os.environ["AUTH_DEV_LOGIN_ENABLED"] = "true"
os.environ.setdefault("JWT_DEV_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
# Bac à sable de paiement : webhooks signés produits localement, aucun appel externe.
os.environ["PSP_PROVIDER"] = "sandbox"
os.environ["PSP_WEBHOOK_SECRET"] = "whsec_test_0123456789abcdef"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import demo  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "migrations"))
    cfg.attributes["database_url"] = os.environ["DATABASE_URL"]
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    with SessionLocal() as db, db.begin():
        demo.seed(db)
    yield


@pytest.fixture(autouse=True)
def _no_queue(monkeypatch):
    """Les tests traitent les webhooks explicitement (pas de worker Celery sur la base de test)."""
    from app.modules.payments import service

    monkeypatch.setattr(service, "enqueue", lambda event_id: None)


@pytest.fixture(autouse=True)
def _neutral_pricing(request, monkeypatch):
    """Prix de base par défaut : les montants des tests ne dépendent ni de l'heure ni du remplissage.
    Les tests marqués `dynamic_pricing` gardent les vraies règles (test_pricing.py)."""
    if request.node.get_closest_marker("dynamic_pricing"):
        return
    from app.modules.booking import pricing

    monkeypatch.setattr(pricing, "slot_price", lambda base, **_: pricing.SlotPrice(base, base, ()))


def pytest_configure(config):
    config.addinivalue_line("markers", "dynamic_pricing: garde les règles de prix variable")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def login(client: TestClient, email: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/dev/login", json={"email": email})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
