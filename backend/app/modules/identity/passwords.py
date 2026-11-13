"""Mot de passe professionnel créé dans Keycloak. Il n'est jamais écrit en base ni dans un e-mail."""
import json
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import get_settings
from app.modules.ops.service import OpsError


def check_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < 8 or len(password) > 72:
        raise OpsError("weak_password", "Le mot de passe doit contenir entre 8 et 72 caractères.", 422)
    if password != password.strip():
        raise OpsError("weak_password", "Le mot de passe ne doit pas commencer ou finir par un espace.", 422)
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise OpsError("weak_password", "Le mot de passe doit contenir une lettre et un chiffre.", 422)
    return password


def _call(method: str, url: str, token: str | None = None, payload: dict | None = None, form: dict | None = None):
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.status, {k.lower(): v for k, v in res.headers.items()}, res.read()
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read()
    except urllib.error.URLError as exc:
        raise OpsError("identity_unreachable", "Le serveur d'identité ne répond pas.", 503) from exc


def set_login_password(*, email: str, password: str, display_name: str) -> None:
    """Crée le compte de connexion, ou remplace le mot de passe s'il existe déjà. Google reste possible."""
    password = check_password(password)
    email = email.strip().lower()
    settings = get_settings()
    if not settings.keycloak_admin_user or not settings.keycloak_admin_password:
        raise OpsError(
            "identity_unconfigured",
            "La création de mot de passe n'est pas encore branchée sur le serveur d'identité.",
            503,
        )
    base = settings.keycloak_internal_url.rstrip("/")
    realm = settings.keycloak_realm or "xpass"
    status, _, body = _call(
        "POST",
        f"{base}/realms/master/protocol/openid-connect/token",
        form={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": settings.keycloak_admin_user,
            "password": settings.keycloak_admin_password,
        },
    )
    if status != 200:
        raise OpsError("identity_unconfigured", "Le serveur d'identité a refusé la création du mot de passe.", 503)
    token = json.loads(body.decode() or "{}").get("access_token")
    if not token:
        raise OpsError("identity_unconfigured", "Le serveur d'identité a refusé la création du mot de passe.", 503)

    query = urllib.parse.urlencode({"email": email, "exact": "true"})
    status, _, body = _call("GET", f"{base}/admin/realms/{realm}/users?{query}", token)
    users = json.loads(body.decode() or "[]") if status == 200 else []
    user_id = users[0]["id"] if users else None
    if user_id is None:
        status, headers, _ = _call(
            "POST",
            f"{base}/admin/realms/{realm}/users",
            token,
            {
                "username": email,
                "email": email,
                "enabled": True,
                "emailVerified": True,
                "firstName": (display_name or email.split("@")[0])[:80],
                "requiredActions": [],
            },
        )
        if status == 201:
            user_id = (headers.get("location") or "").rstrip("/").split("/")[-1]
        elif status != 409:
            raise OpsError("identity_rejected", "Le compte de connexion n'a pas pu être créé.", 502)
        else:
            status, _, body = _call("GET", f"{base}/admin/realms/{realm}/users?{query}", token)
            found = json.loads(body.decode() or "[]") if status == 200 else []
            user_id = found[0]["id"] if found else None
    if not user_id:
        raise OpsError("identity_rejected", "Le compte de connexion n'a pas pu être créé.", 502)

    _call(
        "PUT",
        f"{base}/admin/realms/{realm}/users/{user_id}",
        token,
        {"enabled": True, "emailVerified": True, "requiredActions": []},
    )
    status, _, _ = _call(
        "PUT",
        f"{base}/admin/realms/{realm}/users/{user_id}/reset-password",
        token,
        {"type": "password", "value": password, "temporary": False},
    )
    if status not in (204, 200):
        raise OpsError(
            "weak_password",
            "Le serveur d'identité a refusé ce mot de passe. Choisissez-en un autre, avec une lettre et un chiffre.",
            422,
        )
