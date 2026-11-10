"""Ouvre une session Stripe Checkout pour le dernier compte client (paiement de test)."""
from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.identity.models import User
from app.modules.payments.models import LIVE_SUBSCRIPTION, Subscription, SubscriptionPlan
from app.modules.payments.service import market_by_code, start_checkout


def main() -> int:
    with SessionLocal() as db:
        live = select(Subscription.user_id).where(Subscription.status.in_(LIVE_SUBSCRIPTION))
        user = db.scalar(
            select(User)
            .where(User.deleted_at.is_(None), User.is_active.is_(True), User.id.not_in(live))
            .order_by(User.created_at.desc())
        )
        if user is None:
            print("NO_USER")
            return 1
        try:
            market = market_by_code(db, "FR")
            plan = db.scalar(
                select(SubscriptionPlan)
                .where(SubscriptionPlan.market_id == market.id, SubscriptionPlan.is_active.is_(True))
                .order_by(SubscriptionPlan.price_minor)
            )
            if plan is None:
                print("NO_PLAN")
                return 1
            _, url = start_checkout(db, user=user, market=market, plan_code=plan.code)
            db.commit()
        except Exception as exc:
            db.rollback()
            print(f"ERROR {type(exc).__name__}: {exc}")
            return 1
        print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
