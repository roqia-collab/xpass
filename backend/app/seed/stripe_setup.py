"""Attache un tarif Stripe à chaque formule active. N'affiche jamais les clés."""
from __future__ import annotations

import os
import sys

import httpx
from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.payments.models import SubscriptionPlan

STRIPE = "https://api.stripe.com/v1"


def _post(key: str, path: str, data: dict) -> dict:
    r = httpx.post(f"{STRIPE}{path}", data=data, auth=(key, ""), timeout=20)
    if r.status_code >= 400:
        raise SystemExit(f"Stripe a refusé {path} ({r.status_code}).")
    return r.json()


def _get(key: str, path: str, params: dict | None = None) -> dict:
    r = httpx.get(f"{STRIPE}{path}", params=params, auth=(key, ""), timeout=20)
    if r.status_code >= 400:
        raise SystemExit(f"Stripe a refusé {path} ({r.status_code}).")
    return r.json()


def price_for(key: str, plan: SubscriptionPlan) -> str:
    if (plan.psp_price_id or "").startswith("price_"):
        got = _get(key, f"/prices/{plan.psp_price_id}")
        if got.get("id") == plan.psp_price_id and got.get("active"):
            return plan.psp_price_id
    for price in _get(key, "/prices", {"limit": 40, "active": "true"}).get("data") or []:
        if (price.get("metadata") or {}).get("xpass_code") == plan.code:
            return price["id"]
    product = _post(key, "/products", {
        "name": f"XPASS {plan.name}",
        "description": f"{plan.credits_per_period} crédits par mois",
        "metadata[xpass_code]": plan.code,
    })
    price = _post(key, "/prices", {
        "product": product["id"],
        "currency": (plan.currency or "EUR").lower(),
        "unit_amount": str(plan.price_minor),
        "recurring[interval]": "month",
        "nickname": plan.name,
        "metadata[xpass_code]": plan.code,
    })
    return price["id"]


def main() -> int:
    key = os.environ.get("PSP_SECRET_KEY") or ""
    if not key.startswith("sk_test_"):
        print("PSP_SECRET_KEY de test manquante.", file=sys.stderr)
        return 1
    attached: list[str] = []
    with SessionLocal() as db, db.begin():
        plans = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True))).all()
        if not plans:
            print("Aucune formule active.")
            return 1
        for plan in plans:
            plan.psp_price_id = price_for(key, plan)
            attached.append(f"{plan.code}={plan.psp_price_id}")
    print(" ".join(attached))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
