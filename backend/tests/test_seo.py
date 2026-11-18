"""Rapports SEO : réception sécurisée, validation humaine, application, historique et retour arrière."""
import json
import uuid

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.ops.models import AuditEvent
from app.modules.seo import service as seo
from app.modules.seo.models import SeoPageOverride
from tests.conftest import login
from tests.test_admin import _operator

SECRET = "seo-test-secret-0123456789abcdef0123456789"
URL = "/api/v1/admin/seo/reports"


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setattr(get_settings(), "seo_report_webhook_secret", SECRET)
    seo.limiter.reset()
    yield
    seo.limiter.reset()


def _auth(token: str = SECRET) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _payload(**over) -> dict:
    rid = over.pop("reportId", f"rep-{uuid.uuid4().hex[:12]}")
    body = {
        "reportId": rid,
        "siteUrl": "https://xpass.fr",
        "createdAt": "2026-11-17T05:30:00Z",
        "summary": "Deux titres trop courts.",
        "overallScore": 72,
        "recommendations": [
            {"id": "r1", "priority": "high", "category": "title", "pageUrl": "https://xpass.fr/demande",
             "issue": "Titre trop court", "currentValue": "Demander un accès · XPASS",
             "suggestedValue": "Demander un accès XPASS pour votre entreprise", "reason": "Plus descriptif",
             "status": "open"},
            {"id": "r2", "priority": "low", "category": "sitemap", "pageUrl": "https://xpass.fr/",
             "issue": "Pas de sitemap", "currentValue": None, "suggestedValue": "/sitemap.xml", "reason": "Indexation"},
            {"id": "r3", "priority": "medium", "category": "meta_description",
             "pageUrl": "https://xpass.fr/devenir-partenaire", "issue": "Description absente",
             "currentValue": "", "suggestedValue": "Rejoignez le réseau XPASS.", "reason": "CTR"},
        ],
        "markdownReport": "# Rapport SEO\n\n- **Score** : 72\n\n<script>alert(1)</script>",
    }
    body.update(over)
    return body


def _send(client, body: dict, headers: dict | None = None):
    return client.post(URL, json=body, headers=_auth() if headers is None else headers)


def _report(client, admin) -> dict:
    created = _send(client, _payload())
    assert created.status_code == 201, created.text
    return client.get(f"{URL}/{created.json()['id']}", headers=admin).json()


def _reco(report: dict, ext: str) -> dict:
    return next(r for r in report["recommendations"] if r["external_id"] == ext)


# ---------------------------------------------------------------- réception


def test_valid_report_is_stored(client):
    body = _payload()
    r = _send(client, body)
    assert r.status_code == 201, r.text
    assert r.json()["recommendations"] == 3 and r.json()["status"] == "new"
    assert SECRET not in r.text
    admin = login(client, "admin@xpass.demo")
    detail = client.get(f"{URL}/{r.json()['id']}", headers=admin).json()
    assert detail["report_id"] == body["reportId"] and detail["overall_score"] == 72
    assert detail["markdown_report"] == body["markdownReport"]
    assert detail["source"]
    title = _reco(detail, "r1")
    assert title["page_path"] == "/demande" and title["field"] == "title" and title["applicable"] is True
    assert _reco(detail, "r2")["applicable"] is False


def test_refused_without_or_with_wrong_token(client):
    assert _send(client, _payload(), headers={}).status_code == 401
    r = _send(client, _payload(), headers=_auth("mauvais-jeton"))
    assert r.status_code == 401 and SECRET not in r.text


def test_disabled_without_secret(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "seo_report_webhook_secret", "")
    assert _send(client, _payload()).status_code == 503


def test_malformed_json_and_invalid_schema(client):
    r = client.post(URL, content=b"{pas du json", headers={**_auth(), "Content-Type": "application/json"})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "invalid_json"
    bad = _payload(overallScore=140)
    r = _send(client, bad)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_report"
    assert _send(client, {**_payload(), "inconnu": 1}).status_code == 422
    assert _send(client, _payload(createdAt="2026-11-17T05:30:00")).status_code == 422  # sans fuseau
    dup_ids = _payload()
    dup_ids["recommendations"][1]["id"] = "r1"
    assert _send(client, dup_ids).status_code == 422


def test_duplicate_report_refused(client):
    body = _payload()
    assert _send(client, body).status_code == 201
    r = _send(client, body)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "duplicate_report"


def test_size_limit(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "seo_report_max_bytes", 2_000)
    r = _send(client, _payload(markdownReport="x" * 5_000))
    assert r.status_code == 413


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "seo_report_rate_per_hour", 2)
    assert _send(client, _payload()).status_code == 201
    assert _send(client, _payload(), headers=_auth("faux")).status_code == 401
    assert _send(client, _payload()).status_code == 429


def test_rate_limit_falls_back_without_redis(monkeypatch):
    limiter = seo.RateLimiter()

    def broken():
        raise ConnectionError("redis indisponible")

    monkeypatch.setattr(limiter, "_redis", broken)
    assert limiter.allow("x", 2) and limiter.allow("x", 2)
    assert limiter.allow("x", 2) is False


# ---------------------------------------------------------------- permissions et affichage


def test_admin_only(client):
    _send(client, _payload())
    for who in ("partenaire@xpass.demo", "rh@xpass.demo"):
        assert client.get(URL, headers=login(client, who)).status_code == 403
    assert client.get(URL, headers=login(client, _operator())).status_code == 403  # opérateur : pas admin
    assert client.get(URL).status_code == 401
    # Le secret du webhook ne donne pas accès à la consultation.
    assert client.get(URL, headers=_auth()).status_code == 401


def test_list_and_filters(client):
    admin = login(client, "admin@xpass.demo")
    body = _payload(createdAt="2026-10-02T06:00:00+02:00")
    _send(client, body)
    rows = client.get(URL, params={"date_from": "2026-10-02", "date_to": "2026-10-02"}, headers=admin).json()
    assert [row["report_id"] for row in rows] == [body["reportId"]]
    assert rows[0]["recommendation_count"] == 3 and rows[0]["status"] == "new"
    assert all(row["status"] == "new" for row in client.get(URL, params={"status": "new"}, headers=admin).json())
    assert client.get(URL, params={"status": "bidon"}, headers=admin).status_code == 422


def test_markdown_download(client):
    admin = login(client, "admin@xpass.demo")
    created = _send(client, _payload(createdAt="2026-11-16T23:30:00Z")).json()  # 17/11 à Paris
    r = client.get(f"{URL}/{created['id']}/markdown", headers=admin)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert 'filename="rapport-seo-xpass-2026-11-17.md"' in r.headers["content-disposition"]
    assert r.text.startswith("# Rapport SEO")
    assert client.get(f"{URL}/{created['id']}/markdown", headers=login(client, "rh@xpass.demo")).status_code == 403


# ---------------------------------------------------------------- validation, rejet, application, historique


def test_validate_reject_and_report_status(client):
    admin = login(client, "admin@xpass.demo")
    report = _report(client, admin)
    base = "/api/v1/admin/seo/recommendations"
    r2 = _reco(report, "r2")
    assert client.post(f"{base}/{r2['id']}/reject", json={"note": "non"}, headers=admin).status_code == 422
    assert client.post(f"{base}/{r2['id']}/reject", json={"note": "Sitemap traité à part"}, headers=admin).status_code == 200
    assert client.get(f"{URL}/{report['id']}", headers=admin).json()["status"] == "in_review"
    r1 = _reco(report, "r1")
    assert client.post(f"{base}/{r1['id']}/validate", json={}, headers=admin).status_code == 200
    r3 = _reco(report, "r3")
    edited = client.post(f"{base}/{r3['id']}/validate", json={"value": "Devenez partenaire XPASS à Paris."}, headers=admin)
    assert edited.status_code == 200
    detail = client.get(f"{URL}/{report['id']}", headers=admin).json()
    assert detail["status"] == "validated"
    assert _reco(detail, "r3")["proposed_value"] == "Devenez partenaire XPASS à Paris."
    assert _reco(detail, "r1")["decided_by_name"]
    # Une valeur modifiée invalide est refusée dès la validation.
    bad = client.post(f"{base}/{r3['id']}/validate", json={"value": "ligne 1\nligne 2"}, headers=admin)
    assert bad.status_code == 422
    with SessionLocal() as db:
        actions = set(db.scalars(select(AuditEvent.action).where(AuditEvent.object_type == "seo_recommendation")))
    assert {"seo.validate", "seo.reject"} <= actions


def test_apply_history_and_revert(client):
    admin = login(client, "admin@xpass.demo")
    base = "/api/v1/admin/seo/recommendations"
    report = _report(client, admin)
    r1 = _reco(report, "r1")
    # Rien n'est appliqué sans validation, ni sans confirmation explicite.
    assert client.post(f"{base}/{r1['id']}/apply", json={"confirm": True}, headers=admin).status_code == 409
    client.post(f"{base}/{r1['id']}/validate", json={}, headers=admin)
    assert client.post(f"{base}/{r1['id']}/apply", json={}, headers=admin).status_code == 422
    assert client.post(f"{base}/{r1['id']}/apply", json={"confirm": False}, headers=admin).status_code == 422
    assert client.post(f"{base}/{r1['id']}/apply", json={"confirm": True},
                       headers=login(client, _operator())).status_code == 403

    with SessionLocal() as db:
        before = {(o.page_path, o.field): o.value for o in db.scalars(select(SeoPageOverride))}
    applied = client.post(f"{base}/{r1['id']}/apply", json={"confirm": True}, headers=admin)
    assert applied.status_code == 200, applied.text
    public = client.get("/api/v1/seo/pages", params={"path": "/demande"}).json()
    assert public["values"]["title"] == r1["suggested_value"]
    # Seule la page choisie a changé.
    with SessionLocal() as db:
        after = {(o.page_path, o.field): o.value for o in db.scalars(select(SeoPageOverride))}
    assert {k: v for k, v in after.items() if before.get(k) != v} == {("/demande", "title"): r1["suggested_value"]}

    detail = client.get(f"{URL}/{report['id']}", headers=admin).json()
    reco = _reco(detail, "r1")
    assert reco["status"] == "applied" and reco["applied_by_name"] and reco["applied_at"]
    assert reco["live_value"] == r1["suggested_value"]

    history = client.get("/api/v1/admin/seo/history", params={"path": "/demande"}, headers=admin).json()
    change = history[0]
    assert change["field"] == "title" and change["new_value"] == r1["suggested_value"]
    assert change["old_value"] == before.get(("/demande", "title")) and change["revertible"] is True
    assert change["applied_by_name"]

    r = client.post(f"/api/v1/admin/seo/changes/{change['id']}/revert", json={"confirm": True}, headers=admin)
    assert r.status_code == 200
    restored = client.get("/api/v1/seo/pages", params={"path": "/demande"}).json()["values"].get("title")
    assert restored == before.get(("/demande", "title"))
    again = client.post(f"/api/v1/admin/seo/changes/{change['id']}/revert", json={"confirm": True}, headers=admin)
    assert again.status_code == 409
    history = client.get("/api/v1/admin/seo/history", params={"path": "/demande"}, headers=admin).json()
    assert history[0]["reverted_at"] and history[0]["reverted_by_name"] and history[0]["revertible"] is False
    assert _reco(client.get(f"{URL}/{report['id']}", headers=admin).json(), "r1")["status"] == "reverted"


def test_not_applicable_is_refused_and_error_recorded(client):
    admin = login(client, "admin@xpass.demo")
    base = "/api/v1/admin/seo/recommendations"
    report = _report(client, admin)
    r2 = _reco(report, "r2")  # sitemap : application manuelle
    client.post(f"{base}/{r2['id']}/validate", json={}, headers=admin)
    r = client.post(f"{base}/{r2['id']}/apply", json={"confirm": True}, headers=admin)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "not_applicable"
    assert _reco(client.get(f"{URL}/{report['id']}", headers=admin).json(), "r2")["last_error"]


def test_only_latest_change_can_be_reverted(client):
    admin = login(client, "admin@xpass.demo")
    base = "/api/v1/admin/seo/recommendations"
    ids = []
    for value in ("Devenir partenaire XPASS — première", "Devenir partenaire XPASS — seconde"):
        body = _payload()
        body["recommendations"] = [{"id": "t", "priority": "high", "category": "title",
                                    "pageUrl": "https://www.xpass.fr/devenir-partenaire/", "issue": "Titre",
                                    "suggestedValue": value}]
        created = _send(client, body).json()
        reco = client.get(f"{URL}/{created['id']}", headers=admin).json()["recommendations"][0]
        client.post(f"{base}/{reco['id']}/validate", json={}, headers=admin)
        assert client.post(f"{base}/{reco['id']}/apply", json={"confirm": True}, headers=admin).status_code == 200
        ids.append(reco["id"])
    history = client.get("/api/v1/admin/seo/history", params={"path": "/devenir-partenaire"}, headers=admin).json()
    newest, older = history[0], history[1]
    assert newest["old_value"] == older["new_value"]
    assert client.post(f"/api/v1/admin/seo/changes/{older['id']}/revert", json={"confirm": True},
                       headers=admin).status_code == 409
    assert client.post(f"/api/v1/admin/seo/changes/{newest['id']}/revert", json={"confirm": True},
                       headers=admin).status_code == 200
    title = client.get("/api/v1/seo/pages", params={"path": "/devenir-partenaire"}).json()["values"]["title"]
    assert title == older["new_value"]


def test_value_validation():
    assert seo.clean_value("robots", "Index, Follow") == "index, follow"
    assert json.loads(seo.clean_value("json_ld", '{"@type": "Organization"}')) == {"@type": "Organization"}
    for field, value in (("canonical", "https://evil.example/"), ("canonical", "http://xpass.fr/"),
                         ("robots", "index, hack"), ("json_ld", "{oops"), ("json_ld", "42"),
                         ("twitter_card", "player"), ("title", "x" * 200)):
        with pytest.raises(seo.SeoError):
            seo.clean_value(field, value)
    assert seo.page_path("https://xpass.fr/legal/cgu/?utm=1") == "/legal/cgu"
    assert seo.page_path("https://autre-site.fr/") is None


def test_public_pages_endpoint_hides_unknown_paths(client):
    assert client.get("/api/v1/seo/pages", params={"path": "/admin"}).json()["values"] == {}
