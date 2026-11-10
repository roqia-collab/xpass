"""Formules d'abonnement : gestion par l'administration, changement de formule, report plafonné des crédits.

Report : à chaque facture d'abonnement payée, les crédits d'abonnement encore disponibles sont reportés jusqu'à
l'équivalent d'un mois de la formule payée ; le surplus expire (les plus anciens d'abord). À la fin de l'abonnement,
les crédits d'abonnement disponibles expirent. Les crédits employeur et promotionnels ne sont jamais concernés,
et les crédits déjà réservés pour une prestation restent honorés.
"""
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalog.models import Market
from app.modules.ops.service import audit
from app.modules.payments.models import Subscription, SubscriptionPlan
from app.modules.wallet import service as wallet_service
from app.modules.wallet.models import CreditLot, CreditLotBalance, Wallet

SUBSCRIPTION_ORIGIN = "subscription_invoice"


class PlanError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


# ---------------------------------------------------------------- report plafonné


def cap_subscription_credits(db: Session, wallet: Wallet, *, cap: int, now: datetime, memo: str) -> int:
    """Ramène les crédits d'abonnement disponibles à `cap` au plus ; renvoie le nombre de crédits expirés.
    Le portefeuille DOIT être verrouillé par l'appelant."""
    rows = db.execute(
        select(CreditLot.id, CreditLotBalance.available)
        .join(CreditLotBalance, CreditLotBalance.lot_id == CreditLot.id)
        .where(
            CreditLot.wallet_id == wallet.id,
            CreditLot.origin_type == SUBSCRIPTION_ORIGIN,
            CreditLotBalance.available > 0,
            (CreditLot.expires_at.is_(None)) | (CreditLot.expires_at > now),
        )
        .order_by(CreditLot.created_at)
    ).all()
    excess = sum(available for _, available in rows) - cap
    moves = []
    for lot_id, available in rows:
        if excess <= 0:
            break
        take = min(available, excess)
        moves.append((lot_id, take))
        excess -= take
    wallet_service.expire_amounts(db, wallet.id, moves, memo=memo)
    return sum(amount for _, amount in moves)


def subscription_credits_available(db: Session, wallet_id: uuid.UUID, now: datetime) -> int:
    return int(db.scalar(
        select(func.coalesce(func.sum(CreditLotBalance.available), 0))
        .join(CreditLot, CreditLot.id == CreditLotBalance.lot_id)
        .where(CreditLot.wallet_id == wallet_id, CreditLot.origin_type == SUBSCRIPTION_ORIGIN,
               (CreditLot.expires_at.is_(None)) | (CreditLot.expires_at > now))
    ))


# ---------------------------------------------------------------- changement de formule


def change_plan(db: Session, *, sub: Subscription, plan_code: str) -> SubscriptionPlan:
    """Programme la nouvelle formule pour le prochain renouvellement (pas de prorata, pas de double facture)."""
    from app.modules.payments.service import get_provider, subscription_on_provider

    if sub.status != "active" or not sub.psp_subscription_id:
        raise PlanError("no_subscription", "Aucun abonnement actif.", 404)
    provider = get_provider()
    if not subscription_on_provider(sub, provider):
        raise PlanError("needs_checkout", "Paiement requis pour cette formule.", 409)
    plan = db.scalar(select(SubscriptionPlan).where(
        SubscriptionPlan.market_id == sub.market_id, SubscriptionPlan.code == plan_code, SubscriptionPlan.is_active.is_(True)))
    if plan is None:
        raise PlanError("plan_not_found", "Formule introuvable.", 404)
    current = db.get(SubscriptionPlan, sub.plan_id)
    if plan.id == sub.plan_id:
        sub.pending_plan_id = None  # retour à la formule actuelle : annule un changement programmé
        db.flush()
        return plan
    if plan.currency != current.currency:
        raise PlanError("currency_mismatch", "Devise incohérente avec l'abonnement.")
    provider.change_subscription_price(sub.psp_subscription_id, plan.psp_price_id)
    sub.pending_plan_id = plan.id
    db.flush()
    return plan


def plan_for_invoice(db: Session, sub: Subscription, *, amount: int, currency: str, price_id: str | None) -> SubscriptionPlan:
    """Formule réellement facturée : la formule programmée si la facture lui correspond, sinon la formule actuelle."""
    if sub.pending_plan_id:
        pending = db.get(SubscriptionPlan, sub.pending_plan_id)
        matches_price = price_id is not None and pending.psp_price_id == price_id
        if matches_price or (price_id is None and (amount, currency) == (pending.price_minor, pending.currency)):
            sub.plan_id, sub.pending_plan_id = pending.id, None
            return pending
    return db.get(SubscriptionPlan, sub.plan_id)


# ---------------------------------------------------------------- administration


def _subscribers(db: Session, plan_id: uuid.UUID) -> int:
    return int(db.scalar(select(func.count()).select_from(Subscription).where(
        (Subscription.plan_id == plan_id) | (Subscription.pending_plan_id == plan_id))))


def list_plans(db: Session, market_code: str) -> list[tuple[SubscriptionPlan, int]]:
    market = db.scalar(select(Market).where(Market.code == market_code))
    if market is None:
        raise PlanError("market_not_found", "Marché inconnu.", 404)
    plans = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.market_id == market.id)
                       .order_by(SubscriptionPlan.price_minor)).all()
    return [(p, _subscribers(db, p.id)) for p in plans]


def save_plan(db: Session, *, market_code: str, plan_id: uuid.UUID | None, data: dict, by: uuid.UUID) -> SubscriptionPlan:
    """Crée ou modifie une formule. Prix, devise et tarif prestataire sont figés dès qu'un abonné l'utilise :
    le prestataire facture ce tarif, il faut alors créer une nouvelle formule."""
    market = db.scalar(select(Market).where(Market.code == market_code))
    if market is None:
        raise PlanError("market_not_found", "Marché inconnu.", 404)
    if plan_id is None:
        if db.scalar(select(SubscriptionPlan.id).where(SubscriptionPlan.market_id == market.id,
                                                       SubscriptionPlan.code == data["code"])):
            raise PlanError("duplicate_code", "Ce code de formule existe déjà.")
        plan = SubscriptionPlan(id=uuid.uuid4(), market_id=market.id, currency=market.currency, code=data["code"],
                                is_demo=False)
        db.add(plan)
        action = "plan.created"
    else:
        plan = db.get(SubscriptionPlan, plan_id)
        if plan is None or plan.market_id != market.id:
            raise PlanError("plan_not_found", "Formule introuvable.", 404)
        locked = _subscribers(db, plan.id) > 0
        if locked and (data["price_minor"] != plan.price_minor or (data.get("psp_price_id") or None) != plan.psp_price_id):
            raise PlanError("plan_in_use", "Des abonnés utilisent cette formule : son prix et son tarif ne peuvent plus "
                                           "changer. Créez une nouvelle formule.")
        action = "plan.updated"
    plan.name = data["name"]
    plan.price_minor = data["price_minor"]
    plan.credits_per_period = data["credits_per_period"]
    plan.credit_validity_days = data.get("credit_validity_days")
    plan.psp_price_id = data.get("psp_price_id") or None
    plan.is_active = data["is_active"]
    db.flush()
    audit(db, actor_kind="operator", actor_user_id=by, action=action, object_type="subscription_plan",
          object_id=plan.id, object_label=plan.name,
          details={"price_minor": plan.price_minor, "credits_per_period": plan.credits_per_period,
                   "is_active": plan.is_active})
    return plan
