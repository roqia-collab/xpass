import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.core import kafka_bus


def test_event_record_keeps_the_outbox_identity():
    event_id = uuid.uuid4()
    event = SimpleNamespace(
        id=event_id,
        event_type="booking.confirmed",
        aggregate_type="booking",
        aggregate_id=uuid.uuid4(),
        payload={"credits": 4},
        created_at=datetime(2026, 11, 10, tzinfo=UTC),
    )
    body = kafka_bus.event_record(event)
    assert body["id"] == str(event_id)
    assert body["event_type"] == "booking.confirmed"
    assert body["payload"] == {"credits": 4}


def test_publish_is_skipped_when_kafka_is_not_configured(monkeypatch):
    monkeypatch.setattr(
        kafka_bus,
        "get_settings",
        lambda: SimpleNamespace(kafka_bootstrap_servers=""),
    )
    kafka_bus.publish_outbox(SimpleNamespace())
