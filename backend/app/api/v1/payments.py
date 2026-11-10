"""Abonnement client (maquette 15), webhooks du prestataire et page de paiement du bac à sable."""
import html
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentPrincipal, DbSession
from app.core.config import get_settings
from app.modules.payments import plans as plan_service
from app.modules.payments import service
from app.modules.payments.models import Invoice, Subscription, SubscriptionPlan
from app.modules.payments.provider import InvalidSignature, ProviderError, ProviderNotConfigured
from app.modules.platform.service import IdempotencyMismatch, run_idempotent

router = APIRouter(tags=["abonnement"])


class PlanOut(BaseModel):
    code: str
    name: str
    price_minor: int
    currency: str
    credits_per_period: int
    credit_validity_days: int | None
    is_demo: bool


class InvoiceOut(BaseModel):
    paid_at: datetime
    plan_name: str
    amount_minor: int
    currency: str
    credits: int
    livemode: bool


class SubscriptionOut(BaseModel):
    payments_enabled: bool
    # Bac à sable : aucun argent réel (affiché clairement dans l'application).
    sandbox: bool
    status: str | None
    plan: PlanOut | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    # Formule choisie pour le prochain renouvellement.
    pending_plan: PlanOut | None = None
    # Crédits d'abonnement disponibles et plafond reporté au prochain renouvellement (un mois de formule).
    subscription_credits: int = 0
    rollover_cap: int | None = None
    invoices: list[InvoiceOut]


class CheckoutIn(BaseModel):
    plan_code: str
    market: str = "FR"


class AutoRenewIn(BaseModel):
    enabled: bool
    market: str = "FR"


class ChangePlanIn(BaseModel):
    plan_code: str
    market: str = "FR"


def _http(exc: service.PaymentError) -> HTTPException:
    return HTTPException(exc.status, {"code": exc.code, "message": exc.message})


def _plan_out(p: SubscriptionPlan) -> PlanOut:
    return PlanOut(code=p.code, name=p.name, price_minor=p.price_minor, currency=p.currency,
                   credits_per_period=p.credits_per_period, credit_validity_days=p.credit_validity_days, is_demo=p.is_demo)


@router.get("/subscription/plans", response_model=list[PlanOut])
def plans(db: DbSession, market: str = "FR") -> list[PlanOut]:
    m = service.market_by_code(db, market)
    rows = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.market_id == m.id, SubscriptionPlan.is_active.is_(True))
                      .order_by(SubscriptionPlan.price_minor))
    return [_plan_out(p) for p in rows]


@router.get("/subscription", response_model=SubscriptionOut)
def my_subscription(principal: CurrentPrincipal, db: DbSession, market: str = "FR") -> SubscriptionOut:
    s = get_settings()
    m = service.market_by_code(db, market)
    sub = db.scalar(
        select(Subscription).where(Subscription.user_id == principal.user.id, Subscription.market_id == m.id,
                                   Subscription.status.in_(("active", "past_due")))
    )
    invoices = db.execute(
        select(Invoice, SubscriptionPlan.name)
        .join(Subscription, Subscription.id == Invoice.subscription_id)
        .join(SubscriptionPlan, SubscriptionPlan.id == Subscription.plan_id)
        .where(Invoice.user_id == principal.user.id, Subscription.market_id == m.id)
        .order_by(Invoice.paid_at.desc())
        .limit(12)
    ).all()
    return SubscriptionOut(
        payments_enabled=bool(s.psp_provider),
        sandbox=s.psp_provider == "sandbox",
        status=sub.status if sub else None,
        plan=_plan_out(sub.plan) if sub else None,
        current_period_end=sub.current_period_end if sub else None,
        cancel_at_period_end=sub.cancel_at_period_end if sub else False,
        pending_plan=_plan_out(sub.pending_plan) if sub and sub.pending_plan else None,
        subscription_credits=_subscription_credits(db, principal.user.id, m.id),
        rollover_cap=(sub.pending_plan or sub.plan).credits_per_period if sub else None,
        invoices=[InvoiceOut(paid_at=i.paid_at, plan_name=name, amount_minor=i.amount_minor, currency=i.currency,
                             credits=i.credits, livemode=i.livemode) for i, name in invoices],
    )


def _subscription_credits(db, user_id, market_id) -> int:
    from app.modules.wallet.models import Wallet

    wallet_id = db.scalar(select(Wallet.id).where(Wallet.user_id == user_id, Wallet.market_id == market_id))
    return plan_service.subscription_credits_available(db, wallet_id, datetime.now(UTC)) if wallet_id else 0


@router.post("/subscription/checkout")
def checkout(
    body: CheckoutIn, principal: CurrentPrincipal, db: DbSession,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
):
    """Ouvre un paiement hébergé. Aucun crédit n'est attribué ici : seulement après le webhook « facture payée »."""

    def action():
        m = service.market_by_code(db, body.market)
        _, url = service.start_checkout(db, user=principal.user, market=m, plan_code=body.plan_code)
        return 201, {"checkout_url": url}

    try:
        result = run_idempotent(db, user_id=principal.user.id, scope="subscription.checkout", key=idempotency_key,
                                body=body.model_dump(), action=action)
    except IdempotencyMismatch as exc:
        db.rollback()
        raise HTTPException(422, {"code": "idempotency_mismatch", "message": "Clé déjà utilisée."}) from exc
    except service.PaymentError as exc:
        db.rollback()
        raise _http(exc) from exc
    except ProviderNotConfigured as exc:
        db.rollback()
        raise HTTPException(503, {"code": "payments_disabled", "message": str(exc)}) from exc
    except ProviderError as exc:
        db.rollback()
        raise HTTPException(502, {"code": "provider_error", "message": str(exc)}) from exc
    return JSONResponse(result.body, status_code=result.status)


@router.post("/subscription/auto-renew", response_model=SubscriptionOut)
def auto_renew(body: AutoRenewIn, principal: CurrentPrincipal, db: DbSession) -> SubscriptionOut:
    try:
        service.set_auto_renew(db, user_id=principal.user.id, market=service.market_by_code(db, body.market),
                               enabled=body.enabled)
        db.commit()
    except service.PaymentError as exc:
        db.rollback()
        raise _http(exc) from exc
    except (ProviderNotConfigured, ProviderError) as exc:
        db.rollback()
        raise HTTPException(502, {"code": "provider_error", "message": str(exc)}) from exc
    return my_subscription(principal, db, body.market)


@router.post("/subscription/change-plan", response_model=SubscriptionOut)
def change_plan(body: ChangePlanIn, principal: CurrentPrincipal, db: DbSession) -> SubscriptionOut:
    """Nouvelle formule au prochain renouvellement : le mois en cours reste inchangé (ni prorata, ni double facture)."""
    m = service.market_by_code(db, body.market)
    sub = service.live_subscription(db, principal.user.id, m.id, lock=True)
    try:
        if sub is None:
            raise plan_service.PlanError("no_subscription", "Aucun abonnement actif.", 404)
        plan_service.change_plan(db, sub=sub, plan_code=body.plan_code)
        db.commit()
    except plan_service.PlanError as exc:
        db.rollback()
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc
    except (ProviderNotConfigured, ProviderError) as exc:
        db.rollback()
        raise HTTPException(502, {"code": "provider_error", "message": str(exc)}) from exc
    return my_subscription(principal, db, body.market)


# ---------------------------------------------------------------- webhooks


@router.post("/payments/webhooks/{provider}", include_in_schema=False)
async def webhook(provider: str, request: Request, db: DbSession):
    """Signature vérifiée sur le corps BRUT, persistance, puis traitement asynchrone. 400 si invalide."""
    body = await request.body()
    signature = request.headers.get("stripe-signature") or request.headers.get("xpass-signature")
    try:
        event = service.receive_webhook(db, provider=provider, body=body, signature=signature)
    except InvalidSignature as exc:
        raise HTTPException(400, {"code": "invalid_signature", "message": str(exc)}) from exc
    if event is not None:
        service.enqueue(event.id)
    return {"received": True, "duplicate": event is None}


# ---------------------------------------------------------------- bac à sable (développement)


_PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Paiement de démonstration · XPASS</title>
<style>body{{font-family:system-ui,sans-serif;background:#FAF8F3;color:#121A35;margin:0;padding:24px;display:flex;justify-content:center}}
main{{max-width:420px;width:100%;background:#fff;border:1px solid #E6E1D6;border-radius:20px;padding:24px}}
.warn{{background:#FFE7E2;border-radius:12px;padding:12px;font-weight:600}}
button{{width:100%;padding:16px;border-radius:999px;border:0;font-size:17px;font-weight:600;margin-top:12px;cursor:pointer}}
.pay{{background:#FF674F;color:#fff}}.cancel{{background:#EEEBF8;color:#121A35}}</style></head>
<body><main><p class="warn">Bac à sable de développement : aucun argent n'est débité.</p>
<h1>{plan}</h1><p><strong>{price}</strong> / mois · {credits} crédits</p>
<p>Le paiement produit les mêmes webhooks signés qu'un vrai prestataire. Les crédits n'apparaissent
qu'après leur traitement par le serveur.</p>
<form method="post" action="/api/v1/payments/sandbox/checkout/{sid}/pay"><button class="pay">Payer (démonstration)</button></form>
<form method="get" action="{cancel}"><button class="cancel">Annuler</button></form></main></body></html>"""


def _sandbox_only():
    if get_settings().psp_provider != "sandbox":
        raise HTTPException(404, {"code": "not_found", "message": "Introuvable."})


_ONBOARDING_PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Compte de versement (démonstration) · XPASS</title>
<style>body{{font-family:system-ui,sans-serif;background:#FAF8F3;color:#121A35;margin:0;padding:24px;display:flex;justify-content:center}}
main{{max-width:460px;width:100%;background:#fff;border:1px solid #E6E1D6;border-radius:20px;padding:24px}}
.warn{{background:#FFE7E2;border-radius:12px;padding:12px;font-weight:600}}
button{{width:100%;padding:16px;border-radius:999px;border:0;font-size:17px;font-weight:600;margin-top:12px;cursor:pointer}}
.ok{{background:#C73E28;color:#fff}}.cancel{{background:#EEEBF8;color:#121A35}}</style></head>
<body><main><p class="warn">Bac à sable de développement : aucune donnée bancaire n'est demandée ni versée.</p>
<h1>Compte de versement</h1><p>Chez le vrai prestataire (Stripe), le commerçant saisit ici son identité, son entreprise
et son IBAN. En démonstration, la validation produit le même webhook signé <code>account.updated</code>.</p>
<form method="post" action="/api/v1/payments/sandbox/onboarding/{account}/complete">
<input type="hidden" name="retour" value="{retour}"><button class="ok">Valider le compte (démonstration)</button></form>
<form method="get" action="{retour_raw}"><button class="cancel">Revenir sans valider</button></form></main></body></html>"""


@router.get("/payments/sandbox/invoice/{invoice_id}", response_class=HTMLResponse, include_in_schema=False)
def sandbox_invoice_page(invoice_id: str, db: DbSession, retour: str = ""):
    _sandbox_only()
    import uuid as _uuid

    from app.modules.employer.models import EmployerInvoice

    inv = db.get(EmployerInvoice, _uuid.UUID(invoice_id))
    if inv is None or inv.status != "pending":
        raise HTTPException(404, {"code": "invoice_not_found", "message": "Facture introuvable ou déjà payée."})
    back = _portal_return(retour)
    price = f"{inv.amount_minor // 100},{inv.amount_minor % 100:02d} {'€' if inv.currency == 'EUR' else inv.currency}"
    return _INVOICE_PAGE.format(ref=html.escape(inv.reference), price=price, inv=html.escape(invoice_id),
                                retour=html.escape(back))


@router.post("/payments/sandbox/invoice/{invoice_id}/pay", include_in_schema=False)
async def sandbox_invoice_pay(invoice_id: str, request: Request, db: DbSession):
    _sandbox_only()
    form = await request.form()
    from app.modules.payments.models import PaymentWebhookEvent
    from app.modules.payments.provider import get_provider

    get_provider().emit("checkout.session.completed", {
        "id": f"cs_sbx_inv_{invoice_id.replace('-', '')}", "object": "checkout.session", "mode": "payment",
        "payment_status": "paid", "metadata": {"xpass_invoice_id": invoice_id}})
    for event_id in db.scalars(select(PaymentWebhookEvent.id).where(PaymentWebhookEvent.processed_at.is_(None))):
        service.enqueue(event_id)
    return RedirectResponse(f"{_portal_return(str(form.get('retour') or ''))}?paiement=retour", status_code=303)


_INVOICE_PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Paiement de facture (démonstration) · XPASS</title>
<style>body{{font-family:system-ui,sans-serif;background:#FAF8F3;color:#121A35;margin:0;padding:24px;display:flex;justify-content:center}}
main{{max-width:440px;width:100%;background:#fff;border:1px solid #E6E1D6;border-radius:20px;padding:24px}}
.warn{{background:#FFE7E2;border-radius:12px;padding:12px;font-weight:600}}
button{{width:100%;padding:16px;border-radius:999px;border:0;font-size:17px;font-weight:600;margin-top:12px;cursor:pointer}}
.ok{{background:#C73E28;color:#fff}}.cancel{{background:#EEEBF8;color:#121A35}}</style></head>
<body><main><p class="warn">Bac à sable de développement : aucun argent n'est débité.</p>
<h1>Facture {ref}</h1><p><strong>{price}</strong></p>
<p>Chez le vrai prestataire (Stripe), l'entreprise paie ici par carte ou prélèvement SEPA. En démonstration, le paiement
produit le même webhook signé ; la facture passe « payée » après son traitement.</p>
<form method="post" action="/api/v1/payments/sandbox/invoice/{inv}/pay"><input type="hidden" name="retour" value="{retour}">
<button class="ok">Payer (démonstration)</button></form>
<form method="get" action="{retour}"><button class="cancel">Annuler</button></form></main></body></html>"""


def _portal_return(url: str) -> str:
    base = get_settings().portals_public_url.rstrip("/")
    return url if url.startswith(base + "/") else f"{base}/partner/reglements"


@router.get("/payments/sandbox/onboarding/{account_id}", response_class=HTMLResponse, include_in_schema=False)
def sandbox_onboarding_page(account_id: str, retour: str = ""):
    _sandbox_only()
    back = _portal_return(retour)
    return _ONBOARDING_PAGE.format(account=html.escape(account_id), retour=html.escape(back), retour_raw=html.escape(back))


@router.post("/payments/sandbox/onboarding/{account_id}/complete", include_in_schema=False)
async def sandbox_onboarding_complete(account_id: str, request: Request, db: DbSession):
    _sandbox_only()
    form = await request.form()
    from app.modules.payments.models import PaymentWebhookEvent
    from app.modules.payments.provider import get_provider

    # Même chemin qu'un vrai prestataire : webhook signé, persisté puis traité.
    get_provider().emit("account.updated", {"id": account_id, "object": "account", "payouts_enabled": True,
                                            "charges_enabled": True, "requirements": {"currently_due": []}})
    for event_id in db.scalars(select(PaymentWebhookEvent.id).where(PaymentWebhookEvent.processed_at.is_(None))):
        service.enqueue(event_id)
    return RedirectResponse(_portal_return(str(form.get("retour") or "")), status_code=303)


@router.get("/payments/sandbox/checkout/{checkout_id}", response_class=HTMLResponse, include_in_schema=False)
def sandbox_checkout_page(checkout_id: str, db: DbSession):
    _sandbox_only()
    row = db.execute(
        select(Subscription, SubscriptionPlan).join(SubscriptionPlan, SubscriptionPlan.id == Subscription.plan_id)
        .where(Subscription.provider == "sandbox", Subscription.psp_checkout_id == checkout_id,
               Subscription.status == "incomplete")
    ).first()
    if row is None:
        raise HTTPException(404, {"code": "checkout_not_found", "message": "Session expirée ou déjà payée."})
    _, plan = row
    price = f"{plan.price_minor // 100},{plan.price_minor % 100:02d} {'€' if plan.currency == 'EUR' else plan.currency}"
    return _PAGE.format(plan=html.escape(plan.name), price=price, credits=plan.credits_per_period,
                        sid=html.escape(checkout_id), cancel=f"{get_settings().app_public_url}/#/abonnement")


@router.post("/payments/sandbox/checkout/{checkout_id}/pay", include_in_schema=False)
def sandbox_checkout_pay(checkout_id: str, db: DbSession):
    _sandbox_only()
    try:
        service.sandbox_pay(db, checkout_id=checkout_id)
    except service.PaymentError as exc:
        raise _http(exc) from exc
    # Les événements sont persistés ; leur traitement est asynchrone (comme en réel).
    from app.modules.payments.models import PaymentWebhookEvent

    for event_id in db.scalars(select(PaymentWebhookEvent.id).where(PaymentWebhookEvent.processed_at.is_(None))):
        service.enqueue(event_id)
    return RedirectResponse(f"{get_settings().app_public_url}/#/abonnement?retour=paiement", status_code=303)
