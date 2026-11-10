"""Suivi des erreurs (Sentry), activé seulement si SENTRY_DSN est renseigné.

Aucune donnée personnelle n'est envoyée : send_default_pii=False, corps de requêtes non transmis.
"""
from app.core.config import get_settings


def init_monitoring() -> bool:
    s = get_settings()
    if not s.sentry_dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(dsn=s.sentry_dsn, environment=s.app_env, send_default_pii=False, max_request_body_size="never",
                    traces_sample_rate=0.0)
    return True
