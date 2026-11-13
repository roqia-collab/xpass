from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = "postgresql+psycopg://xpass:xpass_dev@localhost:5432/xpass"
    redis_url: str = "redis://localhost:6379/0"
    # Vide = l'outbox n'écrit pas sur Kafka (tests, poste sans broker).
    kafka_bootstrap_servers: str = ""
    cors_origins: str = "http://localhost:3000"

    # Authentification
    auth_dev_login_enabled: bool = False
    jwt_dev_secret: str = ""
    jwt_dev_ttl_minutes: int = 120
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    # Création des mots de passe professionnels (réseau interne Docker, jamais public).
    keycloak_internal_url: str = "http://keycloak:8080"
    keycloak_admin_user: str = ""
    keycloak_admin_password: str = ""
    keycloak_realm: str = "xpass"

    # Stockage objet (compatible S3)
    s3_endpoint: str = "http://localhost:8333"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    s3_public_bucket: str = "xpass-public"
    s3_private_bucket: str = "xpass-private"

    # E-mails transactionnels (SMTP). Vide = aucun e-mail envoyé.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    mail_from: str = "XPASS <no-reply@xpass.local>"

    # Suivi des erreurs (Sentry). Vide = désactivé.
    sentry_dsn: str = ""

    # Notifications sur téléphone : compte de service Firebase (JSON). Vide = aucune notification envoyée.
    fcm_service_account_file: str = ""

    # Services publics (gratuits, sans clé) : annuaire des entreprises et Base Adresse Nationale.
    sirene_api_url: str = "https://recherche-entreprises.api.gouv.fr"
    geocoder_url: str = "https://data.geopf.fr/geocodage"

    # Prestataire de paiement. "sandbox" = bac à sable local SANS argent (refusé en production).
    psp_provider: Literal["", "stripe", "sandbox"] = ""
    psp_secret_key: str = ""
    psp_webhook_secret: str = ""
    # Stripe Connect : secret de l'endpoint « événements des comptes connectés » (account.updated).
    psp_connect_webhook_secret: str = ""
    # Adresses publiques pour les retours du paiement hébergé.
    api_public_url: str = "http://localhost:8000"
    app_public_url: str = "http://localhost:5173"
    portals_public_url: str = "http://localhost:3000"

    @model_validator(mode="after")
    def _refuse_unsafe_production(self) -> "Settings":
        if self.app_env == "production" and self.auth_dev_login_enabled:
            raise ValueError("AUTH_DEV_LOGIN_ENABLED est interdit lorsque APP_ENV=production.")
        if self.app_env == "production" and self.psp_provider == "sandbox":
            raise ValueError("PSP_PROVIDER=sandbox est interdit lorsque APP_ENV=production.")
        if self.psp_provider and len(self.psp_webhook_secret) < 16:
            raise ValueError("PSP_WEBHOOK_SECRET est obligatoire dès qu'un prestataire est configuré.")
        if self.psp_provider == "stripe" and not self.psp_secret_key:
            raise ValueError("PSP_SECRET_KEY est obligatoire avec PSP_PROVIDER=stripe.")
        if self.auth_dev_login_enabled and len(self.jwt_dev_secret) < 32:
            raise ValueError("JWT_DEV_SECRET doit contenir au moins 32 caractères.")
        return self

    @property
    def dev_login_available(self) -> bool:
        return self.auth_dev_login_enabled and self.app_env in ("development", "test")

    @property
    def oidc_configured(self) -> bool:
        return bool(self.oidc_issuer and self.oidc_audience and self.oidc_jwks_url)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
