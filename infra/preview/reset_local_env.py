"""Réécrit .env à partir des valeurs saines du conteneur API, en local.

Ne rien afficher : les valeurs restent dans le fichier.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEYS = [
    "APP_ENV",
    "AUTH_DEV_LOGIN_ENABLED",
    "JWT_DEV_SECRET",
    "POSTGRES_PASSWORD",
    "S3_ENDPOINT",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "S3_PUBLIC_BUCKET",
    "S3_PRIVATE_BUCKET",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_STARTTLS",
    "MAIL_FROM",
    "MAPS_API_KEY",
    "OIDC_AUDIENCE",
    "PSP_PROVIDER",
    "PSP_SECRET_KEY",
    "PSP_PUBLISHABLE_KEY",
    "PSP_WEBHOOK_SECRET",
    "PSP_CONNECT_WEBHOOK_SECRET",
    "PSP_PRICE_ESSENTIEL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
]

LOCAL = {
    "MEDIA_BASE_URL": "http://localhost:3080/xpass-public",
    "CORS_ORIGINS": "http://localhost:3000,http://localhost:3080,http://localhost:5173,http://localhost:5174",
    "OIDC_ISSUER": "http://localhost:8080/realms/xpass",
    "OIDC_JWKS_URL": "http://keycloak:8080/realms/xpass/protocol/openid-connect/certs",
    "API_PUBLIC_URL": "http://localhost:3080",
    "APP_PUBLIC_URL": "http://localhost:3080/client",
    "PORTALS_PUBLIC_URL": "http://localhost:3080",
    "PREVIEW_AUTH_URL": "http://localhost:8080",
    "PREVIEW_SITE_URL": "http://localhost:3080",
    "PREVIEW_APP_URL": "http://localhost:3080/client",
}

code = (
    "import json,os,sys; keys=sys.argv[1].split();"
    "json.dump({k: os.environ.get(k, '') for k in keys}, sys.stdout)"
)
raw = subprocess.check_output(
    ["docker", "exec", "xpass-api-1", "python", "-c", code, " ".join(KEYS)],
    text=True,
)
values = json.loads(raw)
values.update(LOCAL)
order = [
    "APP_ENV",
    "AUTH_DEV_LOGIN_ENABLED",
    "JWT_DEV_SECRET",
    "POSTGRES_PASSWORD",
    "S3_ENDPOINT",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "S3_PUBLIC_BUCKET",
    "S3_PRIVATE_BUCKET",
    "MEDIA_BASE_URL",
    "CORS_ORIGINS",
    "OIDC_ISSUER",
    "OIDC_AUDIENCE",
    "OIDC_JWKS_URL",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_STARTTLS",
    "MAIL_FROM",
    "MAPS_API_KEY",
    "PSP_PROVIDER",
    "PSP_SECRET_KEY",
    "PSP_PUBLISHABLE_KEY",
    "PSP_WEBHOOK_SECRET",
    "PSP_CONNECT_WEBHOOK_SECRET",
    "PSP_PRICE_ESSENTIEL",
    "API_PUBLIC_URL",
    "APP_PUBLIC_URL",
    "PORTALS_PUBLIC_URL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "PREVIEW_AUTH_URL",
    "PREVIEW_SITE_URL",
    "PREVIEW_APP_URL",
]
text = "\n".join(f"{key}={values.get(key, '')}" for key in order) + "\n"
target = ROOT / ".env"
target.write_text(text, encoding="utf-8")
print(f"wrote {target.name} keys={len(order)} bytes={target.stat().st_size}")
