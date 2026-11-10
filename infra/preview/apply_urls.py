"""Ajoute les URL publiques de test aux clients Keycloak, sans retirer localhost."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

SITE = os.environ["PREVIEW_SITE_URL"].rstrip("/")
APP = os.environ["PREVIEW_APP_URL"].rstrip("/")
AUTH = os.environ["PREVIEW_AUTH_URL"].rstrip("/")
USER = os.environ.get("KC_USER", "admin")
PASSWORD = os.environ["KC_PASS"]
BASE = os.environ.get("KC_BASE", "http://keycloak:8080")


def call(method: str, path: str, data=None, token: str | None = None, form: bool = False):
    url = path if path.startswith("http") else f"{BASE}{path}"
    headers: dict[str, str] = {}
    body = None
    if form:
        body = urllib.parse.urlencode(data or {}).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as res:
        raw = res.read()
        return json.loads(raw) if raw else None


token = call(
    "POST",
    f"{BASE}/realms/master/protocol/openid-connect/token",
    {"grant_type": "password", "client_id": "admin-cli", "username": USER, "password": PASSWORD},
    form=True,
)["access_token"]


def representation(client_id: str) -> dict:
    found = next(c for c in call("GET", "/admin/realms/xpass/clients", token=token) if c["clientId"] == client_id)
    return call("GET", f"/admin/realms/xpass/clients/{found['id']}", token=token)


def merge(client_id: str, extra_redirects: list[str], extra_origins: list[str], extra_logout: list[str], base_url: str | None = None) -> None:
    full = representation(client_id)
    full["redirectUris"] = list(dict.fromkeys((full.get("redirectUris") or []) + extra_redirects))
    full["webOrigins"] = list(dict.fromkeys((full.get("webOrigins") or []) + extra_origins))
    attrs = dict(full.get("attributes") or {})
    existing = [part for part in (attrs.get("post.logout.redirect.uris") or "").split("##") if part]
    attrs["post.logout.redirect.uris"] = "##".join(dict.fromkeys(existing + extra_logout))
    full["attributes"] = attrs
    if base_url:
        full["baseUrl"] = base_url
    call("PUT", f"/admin/realms/xpass/clients/{full['id']}", data=full, token=token)


merge(
    "xpass-portals",
    [f"{SITE}/auth/callback"],
    [SITE],
    [f"{SITE}/login"],
    f"{SITE}/",
)
merge(
    "xpass-mobile",
    [f"{APP}/", f"{APP}", f"{APP}/*"],
    [SITE],
    [f"{APP}/", f"{APP}/*"],
)
print("OK")
print(f"GOOGLE_REDIRECT={AUTH}/realms/xpass/broker/google/endpoint")
