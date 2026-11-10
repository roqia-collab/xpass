"""Abonnements et webhooks du prestataire.

Chaîne d'un webhook : signature vérifiée -> persistance (dédupliquée par identifiant d'événement)
-> commit -> traitement dans une transaction séparée, rejouable (Celery + reprise périodique).
Une erreur de traitement laisse l'événement « non traité » avec son erreur ; il est retenté.
"""
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.catalog.models import Market
from app.modules.identity.models import User
from app.modules.payments.models import (
    LIVE_SUBSCRIPTION,
    Invoice,
    MoneyJournal,
    MoneyJournalLine,
    PaymentWebhookEvent,
    Subscription,
    SubscriptionPlan,
)
from app.modules.payments.provider import InvalidSignature, ProviderError, get_provider, verify_signature
from app.modules.platform.service import emit
from app.modules.wallet import service as wallet_service

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 10


class PaymentError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


class RetryLater(Exception):
    """Événement valide mais pas encore applicable (ex. reçu avant celui qui crée le lien)."""


class PaymentAnomaly(Exception):
    """Événement incohérent (montant, devise) : jamais appliqué automatiquement, à examiner."""


# ---------------------------------------------------------------- journal monétaire


def post_money(db: Session, *, kind: str, memo: str, ref_type: str, ref_id: uuid.UUID,
               lines: list[tuple[str, int, str, uuid.UUID | None]]) -> MoneyJournal:
    """Écriture équilibrée par devise (contrôlée par un trigger différé). Lignes nulles ignorées."""
    journal = MoneyJournal(id=uuid.uuid4(), kind=kind, memo=memo, ref_type=ref_type, ref_id=ref_id)
    db.add(journal)
    db.flush()
    for account, amount, currency, merchant_id in lines:
        if amount:
            db.add(MoneyJournalLine(journal_id=journal.id, account=account, amount_minor=amount,
                                    currency=currency, merchant_id=merchant_id))
    db.flush()
    return journal


# ---------------------------------------------------------------- réception


def receive_webhook(db: Session, *, provider: str, body: bytes, signature: str | None) -> PaymentWebhookEvent | None:
    """Vérifie, persiste et valide (commit). Retourne l'événement, ou None si déjà reçu."""
    settings = get_settings()
    if provider != settings.psp_provider:
        raise InvalidSignature("Prestataire inattendu.")
    # Deux endpoints possibles chez Stripe : compte plateforme et comptes connectés (Connect), chacun son secret.
    try:
        verify_signature(settings.psp_webhook_secret, signature, body)
    except InvalidSignature:
        if not settings.psp_connect_webhook_secret:
            raise
        verify_signature(settings.psp_connect_webhook_secret, signature, body)
    try:
        event = json.loads(body)
        event_id, event_type = str(event["id"]), str(event["type"])
        livemode = bool(event.get("livemode", False))
    except (ValueError, KeyError, TypeError):
        raise InvalidSignature("Corps illisible.") from None
    row_id = db.scalar(
        insert(PaymentWebhookEvent)
        .values(id=uuid.uuid4(), provider=provider, event_id=event_id, event_type=event_type,
                livemode=livemode, payload=event, attempts=0)
        .on_conflict_do_nothing(index_elements=["provider", "event_id"])
        .returning(PaymentWebhookEvent.id)
    )
    db.commit()
    if row_id is None:
        return None  # doublon : déjà persisté (et traité ou en file)
    return db.get(PaymentWebhookEvent, row_id)


def enqueue(event_id: uuid.UUID) -> None:
    """Traitement asynchrone ; si la file est indisponible, la reprise périodique s'en charge."""
    try:
        from app.workers.tasks import process_payment_event

        process_payment_event.delay(str(event_id))
    except Exception:  # noqa: BLE001
        log.warning("File indisponible : l'événement %s sera repris par la tâche périodique", event_id)


# ---------------------------------------------------------------- traitement


def process_event(db: Session, event_id: uuid.UUID, now: datetime | None = None) -> str | None:
    """Traite un événement une seule fois (verrou de ligne). Retourne l'issue, ou None si déjà traité."""
    now = now or datetime.now(UTC)
    row = db.scalar(
        select(PaymentWebhookEvent).where(PaymentWebhookEvent.id == event_id).with_for_update(skip_locked=True)
    )
    if row is None or row.processed_at is not None:
        db.rollback()
        return None
    row.attempts += 1
    attempts = row.attempts
    handler = HANDLERS.get(row.event_type)
    try:
        with db.begin_nested():
            outcome = "ignored" if handler is None else handler(db, row.payload["data"]["object"], row, now)
        row.processed_at = now
        row.outcome = outcome
        row.last_error = None
        db.commit()
        return outcome
    except (RetryLater, PaymentAnomaly, PaymentError) as exc:
        db.rollback()
        # L'événement reste non traité, avec son erreur, pour être retenté ou examiné (lot 7).
        db.execute(
            PaymentWebhookEvent.__table__.update()
            .where(PaymentWebhookEvent.id == event_id)
            # Une anomalie n'est pas retentée automatiquement : elle attend un examen humain.
            .values(attempts=MAX_ATTEMPTS if isinstance(exc, PaymentAnomaly) else attempts,
                    last_error=f"{type(exc).__name__}: {exc}")
        )
        db.commit()
        log.warning("Événement %s non appliqué : %s", event_id, exc)
        return None


def process_pending(db: Session, limit: int = 50) -> int:
    ids = db.scalars(
        select(PaymentWebhookEvent.id)
        .where(PaymentWebhookEvent.processed_at.is_(None), PaymentWebhookEvent.attempts < MAX_ATTEMPTS)
        .order_by(PaymentWebhookEvent.received_at)
        .limit(limit)
    ).all()
    db.rollback()
    return sum(1 for i in ids if process_event(db, i))


def _ts(value) -> datetime | None:
    return datetime.fromtimestamp(int(value), UTC) if value else None


def _metadata_ref(obj: dict) -> str | None:
    """Référence XPASS portée par l'objet (différents emplacements selon la version d'API Stripe)."""
    for meta in (
        obj.get("metadata"),
        (obj.get("subscription_details") or {}).get("metadata"),
        ((obj.get("parent") or {}).get("subscription_details") or {}).get("metadata"),
    ):
        if meta and meta.get("xpass_subscription_id"):
            return meta["xpass_subscription_id"]
    return obj.get("client_reference_id")


def _psp_subscription_id(obj: dict) -> str | None:
    sub = obj.get("subscription") or ((obj.get("parent") or {}).get("subscription_details") or {}).get("subscription")
    return sub if isinstance(sub, str) else (sub or {}).get("id")


def _find_subscription(db: Session, provider: str, obj: dict, *, psp_id: str | None) -> Subscription:
    sub = None
    if psp_id:
        sub = db.scalar(select(Subscription).where(Subscription.provider == provider,
                                                   Subscription.psp_subscription_id == psp_id).with_for_update())
    ref = _metadata_ref(obj)
    if sub is None and ref:
        try:
            sub = db.scalar(select(Subscription).where(Subscription.id == uuid.UUID(ref)).with_for_update())
        except ValueError:
            sub = None
    if sub is None:
        raise RetryLater("Abonnement inconnu pour cet événement.")
    if sub.provider != provider:
        raise PaymentAnomaly("Prestataire différent de celui de l'abonnement.")
    if psp_id and sub.psp_subscription_id and sub.psp_subscription_id != psp_id:
        raise PaymentAnomaly("Identifiant d'abonnement prestataire incohérent.")
    if psp_id and not sub.psp_subscription_id:
        sub.psp_subscription_id = psp_id
    return sub


def _invoice_paid(db, obj, event, now) -> str:
    """Facture entreprise réglée par carte (immédiat) ou prélèvement SEPA (après encaissement)."""
    from app.modules.employer import service as employer
    from app.modules.ops.service import audit

    invoice_id = (obj.get("metadata") or {}).get("xpass_invoice_id")
    if obj.get("payment_status") != "paid":
        return "awaiting_payment"  # SEPA : l'événement async_payment_succeeded suivra
    try:
        invoice = employer.confirm_payment(db, uuid.UUID(invoice_id), by=None, now=now)
    except employer.EmployerError as exc:
        return f"ignored:{exc.code}"
    audit(db, actor_kind="system", actor_user_id=None, action="employer_invoice.paid_online",
          object_type="employer_invoice", object_id=invoice.id, object_label=invoice.reference,
          details={"provider": event.provider, "amount_minor": invoice.amount_minor, "currency": invoice.currency})
    return "applied"


def _on_invoice_checkout_async(db, obj, event, now):
    if (obj.get("metadata") or {}).get("xpass_invoice_id"):
        return _invoice_paid(db, obj, event, now)
    return "ignored"


def _on_checkout_completed(db, obj, event, now):
    if (obj.get("metadata") or {}).get("xpass_invoice_id"):
        return _invoice_paid(db, obj, event, now)
    sub = _find_subscription(db, event.provider, obj, psp_id=_psp_subscription_id(obj))
    sub.psp_customer_id = obj.get("customer") or sub.psp_customer_id
    return "applied"


def _invoice_price_id(obj: dict) -> str | None:
    line = ((obj.get("lines") or {}).get("data") or [{}])[0]
    price = line.get("price") or ((line.get("pricing") or {}).get("price_details") or {}).get("price")
    return price if isinstance(price, str) else (price or {}).get("id")


def _on_invoice_paid(db, obj, event, now):
    from app.modules.payments import plans

    sub = _find_subscription(db, event.provider, obj, psp_id=_psp_subscription_id(obj))
    amount = int(obj.get("amount_paid", -1))
    currency = str(obj.get("currency", "")).upper()
    plan = plans.plan_for_invoice(db, sub, amount=amount, currency=currency, price_id=_invoice_price_id(obj))
    # Contrôle serveur : on n'attribue que si le montant et la devise correspondent à la formule.
    if currency != plan.currency or amount != plan.price_minor:
        raise PaymentAnomaly(f"Montant {amount} {currency} différent de la formule ({plan.price_minor} {plan.currency}).")
    if event.livemode is False and get_settings().app_env == "production" and event.provider != "sandbox":
        raise PaymentAnomaly("Événement de test reçu en production.")

    lines = ((obj.get("lines") or {}).get("data") or [{}])
    period = lines[0].get("period") or {}
    psp_invoice_id = str(obj["id"])
    invoice_id = db.scalar(
        insert(Invoice)
        .values(
            id=uuid.uuid4(), user_id=sub.user_id, subscription_id=sub.id, provider=event.provider,
            psp_invoice_id=psp_invoice_id, amount_minor=amount, currency=currency, credits=plan.credits_per_period,
            period_start=_ts(period.get("start")), period_end=_ts(period.get("end")), status="paid",
            livemode=event.livemode, paid_at=_ts((obj.get("status_transitions") or {}).get("paid_at")) or now,
        )
        .on_conflict_do_nothing(index_elements=["provider", "psp_invoice_id"])
        .returning(Invoice.id)
    )
    if invoice_id is None:
        return "ignored"  # facture déjà enregistrée (autre événement pour la même facture)

    wallet = wallet_service.get_or_create_wallet(db, sub.user_id, sub.market_id, lock=True)
    # Report plafonné : au plus un mois de la formule reste disponible avant l'attribution du nouveau mois.
    plans.cap_subscription_credits(db, wallet, cap=plan.credits_per_period, now=now,
                                   memo="Crédits non reportés (report limité à un mois de formule)")
    wallet_service.grant(
        db, wallet, source="personal", amount=plan.credits_per_period,
        label=f"Abonnement {plan.name}", origin_type=plans.SUBSCRIPTION_ORIGIN,
        origin_ref=f"{event.provider}:{psp_invoice_id}",
        expires_at=now + timedelta(days=plan.credit_validity_days) if plan.credit_validity_days else None,
    )
    post_money(db, kind="invoice_paid", memo=f"Facture {psp_invoice_id}", ref_type="invoice", ref_id=invoice_id,
               lines=[("psp_cash", amount, currency, None), ("customer_deferred", -amount, currency, None)])
    sub.status = "active"
    if period.get("start"):
        sub.current_period_start, sub.current_period_end = _ts(period["start"]), _ts(period.get("end"))
    emit(db, "subscription", sub.id, "subscription.invoice_paid",
         {"invoice_id": str(invoice_id), "credits": plan.credits_per_period})
    return "applied"


def _on_invoice_failed(db, obj, event, now):
    sub = _find_subscription(db, event.provider, obj, psp_id=_psp_subscription_id(obj))
    if sub.status == "active":
        sub.status = "past_due"
    return "applied"


def _on_subscription_updated(db, obj, event, now):
    sub = _find_subscription(db, event.provider, obj, psp_id=obj.get("id"))
    item = (((obj.get("items") or {}).get("data")) or [{}])[0]
    start = obj.get("current_period_start") or item.get("current_period_start")
    end = obj.get("current_period_end") or item.get("current_period_end")
    if start:
        sub.current_period_start, sub.current_period_end = _ts(start), _ts(end)
    sub.cancel_at_period_end = bool(obj.get("cancel_at_period_end", sub.cancel_at_period_end))
    status = obj.get("status")
    if status in ("active", "trialing"):
        # Le passage d'« incomplet » à « actif » se fait uniquement sur facture payée.
        if sub.status == "past_due":
            sub.status = "active"
    elif status in ("past_due", "unpaid"):
        sub.status = "past_due"
    elif status in ("canceled", "incomplete_expired"):
        if sub.status != "canceled":
            _end_subscription_credits(db, sub, now)
        sub.status, sub.canceled_at = "canceled", now
    return "applied"


def _end_subscription_credits(db, sub, now) -> None:
    """Fin d'abonnement : les crédits d'abonnement disponibles expirent (les réservations en cours restent honorées)."""
    from app.modules.payments import plans

    wallet = wallet_service.get_or_create_wallet(db, sub.user_id, sub.market_id, lock=True)
    plans.cap_subscription_credits(db, wallet, cap=0, now=now, memo="Fin d'abonnement")


def _on_subscription_deleted(db, obj, event, now):
    sub = _find_subscription(db, event.provider, obj, psp_id=obj.get("id"))
    if sub.status != "canceled":
        _end_subscription_credits(db, sub, now)
    sub.status, sub.canceled_at, sub.cancel_at_period_end = "canceled", now, False
    sub.pending_plan_id = None
    return "applied"


def _on_transfer(db, obj, event, now):
    from app.modules.settlement.service import confirm_transfer

    return confirm_transfer(db, provider=event.provider, obj=obj, now=now)


def _on_transfer_reversed(db, obj, event, now):
    from app.modules.settlement.service import reverse_transfer

    return reverse_transfer(db, provider=event.provider, obj=obj)


def _on_account_updated(db, obj, event, now):
    from app.modules.ops.service import apply_psp_account_update

    return apply_psp_account_update(db, provider=event.provider, obj=obj)


HANDLERS = {
    "account.updated": _on_account_updated,
    "checkout.session.completed": _on_checkout_completed,
    "checkout.session.async_payment_succeeded": _on_invoice_checkout_async,
    "invoice.paid": _on_invoice_paid,
    "invoice.payment_succeeded": _on_invoice_paid,
    "invoice.payment_failed": _on_invoice_failed,
    "customer.subscription.updated": _on_subscription_updated,
    "customer.subscription.deleted": _on_subscription_deleted,
    "transfer.created": _on_transfer,
    "transfer.reversed": _on_transfer_reversed,
}


# ---------------------------------------------------------------- commandes client


def market_by_code(db: Session, code: str) -> Market:
    market = db.scalar(select(Market).where(Market.code == code))
    if market is None:
        raise PaymentError("market_not_found", "Marché inconnu.", 404)
    return market


def live_subscription(db: Session, user_id: uuid.UUID, market_id: uuid.UUID, *, lock: bool = False) -> Subscription | None:
    stmt = select(Subscription).where(
        Subscription.user_id == user_id, Subscription.market_id == market_id, Subscription.status.in_(LIVE_SUBSCRIPTION)
    )
    return db.scalar(stmt.with_for_update() if lock else stmt)


def subscription_on_provider(sub: Subscription, provider) -> bool:
    """Faux si l'abonnement local n'est pas géré par le prestataire actuel (ex. reliquat bac à sable)."""
    if sub.provider != provider.name:
        return False
    sid = sub.psp_subscription_id or ""
    return not (provider.name == "stripe" and sid.startswith("sub_sbx_"))


def _expire_live(db: Session, sub: Subscription, *, cancel_at_provider: bool) -> None:
    if cancel_at_provider:
        sid = sub.psp_subscription_id or ""
        if sid.startswith("sub_") and not sid.startswith("sub_sbx_"):
            try:
                get_provider().cancel_subscription(sid)
            except ProviderError as exc:
                log.warning("Annulation prestataire ignorée pour %s : %s", sid, exc)
    sub.status = "expired"
    sub.pending_plan_id = None
    db.flush()


def start_checkout(db: Session, *, user: User, market: Market, plan_code: str) -> tuple[Subscription, str]:
    plan = db.scalar(select(SubscriptionPlan).where(
        SubscriptionPlan.market_id == market.id, SubscriptionPlan.code == plan_code, SubscriptionPlan.is_active.is_(True)))
    if plan is None:
        raise PaymentError("plan_not_found", "Formule introuvable.", 404)
    if plan.currency != market.currency:
        raise PaymentError("currency_mismatch", "Devise incohérente avec le marché.", 409)
    provider = get_provider()
    existing = live_subscription(db, user.id, market.id, lock=True)
    if existing is not None:
        on_provider = subscription_on_provider(existing, provider)
        if existing.status == "incomplete" or not on_provider:
            # Session abandonnée, ou reliquat d'un autre prestataire : on ouvre un vrai paiement.
            _expire_live(db, existing, cancel_at_provider=False)
        elif existing.plan_id == plan.id:
            raise PaymentError("already_subscribed", "Vous avez déjà un abonnement en cours.", 409)
        else:
            # Autre formule : on clôture l'abonnement actuel pour encaisser le nouveau maintenant.
            _expire_live(db, existing, cancel_at_provider=True)
    sub = Subscription(id=uuid.uuid4(), user_id=user.id, market_id=market.id, plan_id=plan.id,
                       provider=provider.name, status="incomplete")
    db.add(sub)
    db.flush()
    checkout = provider.create_checkout(
        subscription_id=sub.id, price_id=plan.psp_price_id, customer_email=user.email,
        amount_minor=plan.price_minor, currency=plan.currency, plan_name=plan.name,
    )
    sub.psp_checkout_id = checkout.id
    db.flush()
    return sub, checkout.url


def set_auto_renew(db: Session, *, user_id: uuid.UUID, market: Market, enabled: bool) -> Subscription:
    sub = live_subscription(db, user_id, market.id, lock=True)
    if sub is None or sub.status == "incomplete" or not sub.psp_subscription_id:
        raise PaymentError("no_subscription", "Aucun abonnement actif.", 404)
    get_provider().set_cancel_at_period_end(sub.psp_subscription_id, not enabled)
    # Réponse synchrone du prestataire (pas un retour navigateur) ; le webhook confirmera aussi.
    sub.cancel_at_period_end = not enabled
    db.flush()
    return sub


# ---------------------------------------------------------------- bac à sable


def sandbox_pay(db: Session, *, checkout_id: str, now: datetime | None = None) -> Subscription:
    """Bac à sable : produit les webhooks signés qu'enverrait le prestataire après un paiement réussi."""
    from app.modules.payments.provider import SandboxProvider

    provider = get_provider()
    if not isinstance(provider, SandboxProvider):
        raise PaymentError("not_sandbox", "Bac à sable désactivé.", 404)
    sub = db.scalar(select(Subscription).where(Subscription.provider == "sandbox",
                                               Subscription.psp_checkout_id == checkout_id))
    if sub is None or sub.status != "incomplete":
        raise PaymentError("checkout_not_found", "Session de paiement introuvable ou déjà utilisée.", 404)
    plan = db.get(SubscriptionPlan, sub.plan_id)
    now = now or datetime.now(UTC)
    psp_sub = f"sub_sbx_{uuid.uuid4().hex[:16]}"
    db.rollback()
    provider.emit("checkout.session.completed", {
        "id": checkout_id, "object": "checkout.session", "client_reference_id": str(sub.id),
        "customer": f"cus_sbx_{sub.user_id.hex[:12]}", "subscription": psp_sub,
        "metadata": {"xpass_subscription_id": str(sub.id)},
    })
    sandbox_invoice(provider, sub_id=sub.id, psp_sub=psp_sub, plan=plan, start=now)
    return sub


def sandbox_invoice(provider, *, sub_id: uuid.UUID, psp_sub: str, plan: SubscriptionPlan, start: datetime) -> None:
    end = start + timedelta(days=30)
    provider.emit("invoice.paid", {
        "id": f"in_sbx_{uuid.uuid4().hex[:16]}", "object": "invoice", "subscription": psp_sub,
        "amount_paid": plan.price_minor, "currency": plan.currency.lower(),
        "subscription_details": {"metadata": {"xpass_subscription_id": str(sub_id)}},
        "status_transitions": {"paid_at": int(start.timestamp())},
        "lines": {"data": [{"period": {"start": int(start.timestamp()), "end": int(end.timestamp())}}]},
    })
