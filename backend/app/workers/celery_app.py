"""Celery : worker et planificateur.

Tâches planifiées : expiration des réserves HELD (5 min), diffusion de l'outbox,
expiration des lots de crédits,
reprise des webhooks de paiement, cycle de règlement partenaires.
PostgreSQL reste la source de vérité ; Redis ne sert que de file.
"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery = Celery("xpass", broker=settings.redis_url, backend=settings.redis_url, include=["app.workers.tasks"])
celery.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    beat_schedule={
        "heartbeat": {"task": "xpass.heartbeat", "schedule": 300.0},
        "expire-holds": {"task": "xpass.expire_holds", "schedule": 20.0},
        "dispatch-outbox": {"task": "xpass.dispatch_outbox", "schedule": 10.0},
        "expire-credit-lots": {"task": "xpass.expire_credit_lots", "schedule": 3600.0},
        "payment-events": {"task": "xpass.process_pending_payment_events", "schedule": 30.0},
        "settlement-cycle": {"task": "xpass.settlement_cycle", "schedule": 3600.0},
        "employer-allocations": {"task": "xpass.employer_allocations", "schedule": 3600.0},
        "booking-reminders": {"task": "xpass.booking_reminders", "schedule": 900.0},
        "no-shows": {"task": "xpass.mark_no_shows", "schedule": 900.0},
    },
)
app = celery

from app.core.monitoring import init_monitoring  # noqa: E402

init_monitoring()
