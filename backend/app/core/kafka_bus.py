"""Bus d'événements Kafka.

L'outbox PostgreSQL reste la source de vérité. Après commit, le worker publie
chaque événement sur le topic ``xpass.events`` (clé = id, pour que les
consommateurs ignorent un doublon). Sans ``KAFKA_BOOTSTRAP_SERVERS``, la
publication est ignorée : les tests et un poste sans broker continuent.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings

log = logging.getLogger(__name__)

TOPIC = "xpass.events"
_producer: Any = None


def event_record(event: Any) -> dict:
    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": str(event.aggregate_id),
        "payload": event.payload,
        "created_at": event.created_at.isoformat() if event.created_at is not None else None,
    }


def publish_outbox(event: Any) -> None:
    """Envoie l'événement. Lève si le broker est configuré et injoignable."""
    servers = get_settings().kafka_bootstrap_servers.strip()
    if not servers:
        return
    producer = _client(servers)
    body = event_record(event)
    future = producer.send(TOPIC, key=body["id"].encode(), value=body)
    future.get(timeout=8)
    log.info("kafka %s publié (%s)", event.event_type, event.id)


def _client(servers: str) -> Any:
    global _producer
    if _producer is None:
        from kafka import KafkaProducer

        _producer = KafkaProducer(
            bootstrap_servers=[s.strip() for s in servers.split(",") if s.strip()],
            value_serializer=lambda v: json.dumps(v, default=str).encode(),
            key_serializer=lambda k: k if isinstance(k, bytes) else str(k).encode(),
            acks="all",
            retries=2,
            request_timeout_ms=8000,
            api_version_auto_timeout_ms=8000,
        )
    return _producer


def reset_client() -> None:
    """Ferme le producteur (tests)."""
    global _producer
    if _producer is not None:
        _producer.close(timeout=2)
        _producer = None
