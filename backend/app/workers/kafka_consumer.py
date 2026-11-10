"""Lit ``xpass.events`` et journalise chaque message.

Les e-mails et notifications partent toujours depuis l'outbox. Ce processus
tient le groupe ``xpass-platform`` : c'est le point d'accroche des services
qui réagissent au flux (sans renvoyer les e-mails).
"""
from __future__ import annotations

import logging
import signal

from app.core.config import get_settings
from app.core.kafka_bus import TOPIC

log = logging.getLogger(__name__)


def main() -> None:
    servers = get_settings().kafka_bootstrap_servers.strip()
    if not servers:
        raise SystemExit("KAFKA_BOOTSTRAP_SERVERS est vide")
    from kafka import KafkaConsumer

    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=[s.strip() for s in servers.split(",") if s.strip()],
        group_id="xpass-platform",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda b: b.decode() if b else "",
    )
    running = True

    def stop(*_args: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log.info("écoute %s via %s", TOPIC, servers)
    while running:
        for records in consumer.poll(timeout_ms=1000).values():
            for message in records:
                log.info("reçu %s", (message.value or "")[:300])
    consumer.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
