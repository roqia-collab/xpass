import logging
from datetime import UTC, datetime

from sqlalchemy import text

from app.db.session import SessionLocal, engine
from app.workers.celery_app import celery

log = logging.getLogger(__name__)


@celery.task(name="xpass.heartbeat")
def heartbeat() -> str:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    log.info("heartbeat ok")
    return "ok"


@celery.task(name="xpass.expire_holds")
def expire_holds() -> int:
    """Libère capacité et crédits des réserves HELD de plus de 5 minutes."""
    from app.modules.booking.service import expire_due_holds

    with SessionLocal() as db, db.begin():
        n = expire_due_holds(db, datetime.now(UTC))
    if n:
        log.info("%s réserve(s) expirée(s)", n)
    return n


@celery.task(name="xpass.mark_no_shows")
def mark_no_shows() -> int:
    """Réservations non présentées (fenêtre du QR close) : crédits consommés, partenaire payé."""
    from app.modules.booking.service import mark_no_shows as run

    with SessionLocal() as db, db.begin():
        n = run(db, datetime.now(UTC))
    if n:
        log.info("%s absence(s) enregistrée(s)", n)
    return n


@celery.task(name="xpass.expire_credit_lots")
def expire_credit_lots() -> int:
    from app.modules.wallet.service import expire_lots

    with SessionLocal() as db, db.begin():
        return expire_lots(db, datetime.now(UTC))


@celery.task(name="xpass.dispatch_outbox")
def dispatch_outbox(batch: int = 100) -> int:
    """Diffuse les événements de l'outbox après commit : Kafka (si configuré), puis e-mails.

    Rejouable : un événement en échec reste en file avec son erreur et est retenté (10 fois au plus).
    """
    from sqlalchemy import select

    from app.modules.notifications.service import MAX_ATTEMPTS, deliver
    from app.modules.platform.models import OutboxEvent

    sent = 0
    with SessionLocal() as db:
        ids = db.scalars(
            select(OutboxEvent.id)
            .where(OutboxEvent.published_at.is_(None), OutboxEvent.attempts < MAX_ATTEMPTS)
            .order_by(OutboxEvent.created_at)
            .limit(batch)
        ).all()
    for event_id in ids:
        with SessionLocal() as db, db.begin():
            e = db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id).with_for_update(skip_locked=True))
            if e is None or e.published_at is not None:
                continue
            e.attempts += 1
            try:
                from app.core.kafka_bus import publish_outbox

                publish_outbox(e)
                deliver(db, e)
                e.published_at, e.last_error = datetime.now(UTC), None
                sent += 1
            except Exception as exc:  # noqa: BLE001 — SMTP indisponible, etc. : retenté plus tard
                e.last_error = f"{type(exc).__name__}: {exc}"[:500]
                log.warning("outbox %s non diffusé : %s", e.id, exc)
    return sent


@celery.task(name="xpass.process_payment_event", autoretry_for=(), acks_late=True)
def process_payment_event(event_id: str) -> str | None:
    import uuid

    from app.modules.payments.service import process_event

    with SessionLocal() as db:
        return process_event(db, uuid.UUID(event_id))


@celery.task(name="xpass.process_pending_payment_events")
def process_pending_payment_events() -> int:
    """Reprise : événements non traités (file indisponible, ordre d'arrivée, erreur passagère)."""
    from app.modules.payments.service import process_pending

    with SessionLocal() as db:
        return process_pending(db)


@celery.task(name="xpass.settlement_cycle")
def settlement_cycle() -> dict:
    """Valorise les dettes en attente, constitue les versements de la semaine fermée, puis demande
    les transferts au prestataire (après commit)."""
    from app.modules.payments.provider import ProviderNotConfigured, get_provider
    from app.modules.settlement import service

    with SessionLocal() as db, db.begin():
        valued = service.value_pending(db)
        built = len(service.build_payouts(db))
    sent = 0
    try:
        provider = get_provider()
    except ProviderNotConfigured:
        provider = None
    if provider is not None:
        with SessionLocal() as db:
            sent = service.execute_pending(db, provider)
    return {"valued": valued, "payouts": built, "transfers": sent}


@celery.task(name="xpass.employer_allocations")
def employer_allocations() -> int:
    """Attribue les crédits du mois en cours aux salariés actifs (idempotent : un par salarié et par mois)."""
    from app.modules.employer.service import allocate_all

    with SessionLocal() as db, db.begin():
        return allocate_all(db)


@celery.task(name="xpass.booking_reminders")
def booking_reminders() -> int:
    """Rappel « la veille » (24 h avant) des réservations confirmées : e-mail et notification, une seule fois."""
    from app.modules.engagement.service import due_reminders

    with SessionLocal() as db, db.begin():
        return due_reminders(db)
