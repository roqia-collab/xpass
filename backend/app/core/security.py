"""Vérification des jetons d'accès.

- Production : jetons OIDC vérifiés via le JWKS du fournisseur configuré.
- Développement : jetons HS256 émis par /api/v1/auth/dev/login, acceptés uniquement
  si `Settings.dev_login_available` est vrai.
"""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt

from app.core.config import Settings, get_settings

DEV_ISSUER = "xpass-dev"
API_AUDIENCE = "xpass-api"


class InvalidToken(Exception):
    pass


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    issuer: str
    is_dev: bool
    email: str | None = None
    email_verified: bool = False
    name: str | None = None


def issue_dev_token(user_id: str, settings: Settings | None = None) -> tuple[str, int]:
    settings = settings or get_settings()
    if not settings.dev_login_available:
        raise RuntimeError("La connexion de développement est désactivée.")
    ttl = settings.jwt_dev_ttl_minutes * 60
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": user_id, "iss": DEV_ISSUER, "aud": API_AUDIENCE, "iat": now, "exp": now + timedelta(seconds=ttl)},
        settings.jwt_dev_secret,
        algorithm="HS256",
    )
    return token, ttl


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True)


def verify_token(token: str, settings: Settings | None = None) -> TokenClaims:
    settings = settings or get_settings()
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError as exc:
        raise InvalidToken("Jeton illisible.") from exc

    try:
        if unverified.get("iss") == DEV_ISSUER:
            if not settings.dev_login_available:
                raise InvalidToken("Jetons de développement refusés dans cet environnement.")
            claims = jwt.decode(token, settings.jwt_dev_secret, algorithms=["HS256"], audience=API_AUDIENCE)
            return TokenClaims(subject=claims["sub"], issuer=DEV_ISSUER, is_dev=True)

        if not settings.oidc_configured:
            raise InvalidToken("Aucun fournisseur OIDC n'est configuré.")
        key = _jwks_client(settings.oidc_jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
        )
        return TokenClaims(
            subject=claims["sub"],
            issuer=settings.oidc_issuer,
            is_dev=False,
            email=(claims.get("email") or "").strip().lower() or None,
            email_verified=bool(claims.get("email_verified")),
            name=claims.get("name") or claims.get("given_name"),
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken("Jeton invalide ou expiré.") from exc
