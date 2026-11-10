import logging
import socket

import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import engine

settings = get_settings()
logging.basicConfig(level=logging.INFO)

from app.core.monitoring import init_monitoring  # noqa: E402

init_monitoring()

app = FastAPI(
    title="XPASS API",
    version="0.1.0",
    description="API REST XPASS. Lot 1 : catalogue, établissements, identité, lecture portails.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # En développement, autorise aussi Flutter web servi sur un port local aléatoire.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+" if settings.app_env == "development" else None,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

app.include_router(api_router)


@app.get("/health", tags=["santé"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/health/ready", tags=["santé"])
def ready() -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        with engine.connect() as conn:
            checks["postgis"] = conn.execute(text("SELECT postgis_lib_version()")).scalar_one()
    except Exception as exc:  # noqa: BLE001
        checks["postgres"] = f"erreur: {exc.__class__.__name__}"
    try:
        redis.Redis.from_url(settings.redis_url, socket_timeout=2).ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"erreur: {exc.__class__.__name__}"
    brokers = settings.kafka_bootstrap_servers.strip()
    if brokers:
        hostport = brokers.split(",")[0].strip()
        host, _, port = hostport.partition(":")
        try:
            with socket.create_connection((host, int(port or 9092)), timeout=1):
                checks["kafka"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["kafka"] = f"erreur: {exc.__class__.__name__}"
    ok = "postgis" in checks and checks["redis"] == "ok" and checks.get("kafka", "ok") == "ok"
    return JSONResponse({"status": "ok" if ok else "degraded", "checks": checks}, status_code=200 if ok else 503)
