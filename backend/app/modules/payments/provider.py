"""Adaptateurs du prestataire de paiement (PSP).

- `StripeProvider` : appels REST Stripe (Checkout en mode abonnement, comptes et transferts Connect).
- `SandboxProvider` : bac à sable LOCAL, sans argent, interdit en production. Il produit des
  webhooks au format Stripe, signés avec le même secret, qui passent par la même vérification,
  la même persistance et le même traitement que les vrais.

Les crédits ne sont JAMAIS attribués par ces appels : uniquement par le traitement d'un webhook signé.
"""
import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import get_settings

SIGNATURE_TOLERANCE_S = 300


class ProviderNotConfigured(Exception):
    pass


class ProviderError(Exception):
    pass


class InvalidSignature(Exception):
    pass


@dataclass(frozen=True)
class Checkout:
    id: str
    url: str


class PaymentProvider(Protocol):
    name: str

    def create_checkout(self, *, subscription_id: uuid.UUID, price_id: str | None, customer_email: str,
                        amount_minor: int, currency: str, plan_name: str) -> Checkout: ...

    def set_cancel_at_period_end(self, psp_subscription_id: str, cancel: bool) -> None: ...

    # Nouvelle formule au prochain renouvellement, sans prorata.
    def change_subscription_price(self, psp_subscription_id: str, price_id: str | None) -> None: ...

    # Annulation immédiate chez le prestataire (changement de formule payé maintenant).
    def cancel_subscription(self, psp_subscription_id: str) -> None: ...

    def create_transfer(self, *, payout_id: uuid.UUID, amount_minor: int, currency: str, destination: str) -> str: ...

    # Facture entreprise : page de paiement hébergée (carte ou prélèvement SEPA).
    def create_invoice_checkout(self, *, invoice_id: uuid.UUID, reference: str, amount_minor: int, currency: str,
                                customer_email: str, return_url: str) -> Checkout: ...

    # Connect : compte de versement du commerçant (identité et IBAN saisis chez le prestataire, jamais chez XPASS).
    def create_connected_account(self, *, merchant_id: uuid.UUID, email: str, country: str, business_name: str) -> str: ...

    def onboarding_link(self, *, account_id: str, refresh_url: str, return_url: str) -> str: ...

    def dashboard_link(self, account_id: str) -> str | None: ...

    def retrieve_account(self, account_id: str) -> dict | None: ...


# ---------------------------------------------------------------- signature (schéma Stripe)


def sign(secret: str, body: bytes, timestamp: int | None = None) -> str:
    t = int(time.time()) if timestamp is None else timestamp
    mac = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={t},v1={mac}"


def verify_signature(secret: str, header: str | None, body: bytes, now: float | None = None) -> None:
    """En-tête `t=...,v1=...` : HMAC-SHA256 de « t.corps », comparaison à temps constant, fraîcheur 5 min."""
    if not header or not secret:
        raise InvalidSignature("Signature absente.")
    parts: dict[str, list[str]] = {}
    for item in header.split(","):
        k, _, v = item.strip().partition("=")
        parts.setdefault(k, []).append(v)
    try:
        t = int(parts["t"][0])
    except (KeyError, ValueError):
        raise InvalidSignature("Horodatage invalide.") from None
    if abs((now or time.time()) - t) > SIGNATURE_TOLERANCE_S:
        raise InvalidSignature("Signature périmée.")
    expected = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, v) for v in parts.get("v1", [])):
        raise InvalidSignature("Signature invalide.")


# ---------------------------------------------------------------- Stripe


class StripeProvider:
    name = "stripe"
    base = "https://api.stripe.com/v1"

    def __init__(self, secret_key: str):
        self._key = secret_key

    @staticmethod
    def _raise(response: httpx.Response) -> None:
        detail = ""
        try:
            detail = str((response.json().get("error") or {}).get("message") or "").strip()
        except ValueError:
            detail = ""
        raise ProviderError(detail or f"Refus du prestataire ({response.status_code}).")

    def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            r = httpx.get(f"{self.base}{path}", params=params, auth=(self._key, ""), timeout=15)
        except httpx.HTTPError as exc:
            raise ProviderError("Prestataire de paiement injoignable.") from exc
        if r.status_code >= 400:
            self._raise(r)
        return r.json()

    def _post(self, path: str, data: dict, idempotency_key: str) -> dict:
        try:
            r = httpx.post(
                f"{self.base}{path}",
                data=data,
                auth=(self._key, ""),
                headers={"Idempotency-Key": idempotency_key},
                timeout=15,
            )
        except httpx.HTTPError as exc:
            raise ProviderError("Prestataire de paiement injoignable.") from exc
        if r.status_code >= 400:
            self._raise(r)
        return r.json()

    def _delete(self, path: str) -> dict:
        try:
            r = httpx.delete(f"{self.base}{path}", auth=(self._key, ""), timeout=15)
        except httpx.HTTPError as exc:
            raise ProviderError("Prestataire de paiement injoignable.") from exc
        if r.status_code >= 400:
            self._raise(r)
        return r.json() if r.content else {}

    def create_checkout(self, *, subscription_id, price_id, customer_email, amount_minor, currency, plan_name):
        if not price_id:
            raise ProviderNotConfigured("Tarif non configuré chez le prestataire pour cette formule.")
        s = get_settings()
        ref = str(subscription_id)
        data = self._post(
            "/checkout/sessions",
            {
                "mode": "subscription",
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": "1",
                "customer_email": customer_email,
                "client_reference_id": ref,
                "metadata[xpass_subscription_id]": ref,
                "subscription_data[metadata][xpass_subscription_id]": ref,
                "success_url": f"{s.app_public_url}/#/abonnement?retour=paiement",
                "cancel_url": f"{s.app_public_url}/#/abonnement?retour=annule",
            },
            idempotency_key=f"checkout-{ref}",
        )
        return Checkout(id=data["id"], url=data["url"])

    def change_subscription_price(self, psp_subscription_id, price_id):
        if not price_id:
            raise ProviderError("Formule sans tarif Stripe (psp_price_id) : changement impossible.")
        sub = self._get(f"/subscriptions/{psp_subscription_id}", params={"expand[]": "items.data"})
        items = (sub.get("items") or {}).get("data") or []
        if not items:
            items = (self._get("/subscription_items", params={"subscription": psp_subscription_id, "limit": "1"})
                     .get("data") or [])
        item_id = (items[0] or {}).get("id") if items else None
        if not item_id:
            raise ProviderError("Abonnement Stripe sans ligne de tarif.")
        self._post(
            f"/subscriptions/{psp_subscription_id}",
            {"items[0][id]": item_id, "items[0][price]": price_id, "proration_behavior": "none"},
            idempotency_key=f"plan-{psp_subscription_id}-{price_id}-{uuid.uuid4()}",
        )

    def set_cancel_at_period_end(self, psp_subscription_id, cancel):
        self._post(
            f"/subscriptions/{psp_subscription_id}",
            {"cancel_at_period_end": "true" if cancel else "false"},
            idempotency_key=f"cancel-{psp_subscription_id}-{cancel}-{uuid.uuid4()}",
        )

    def cancel_subscription(self, psp_subscription_id):
        try:
            self._delete(f"/subscriptions/{psp_subscription_id}")
        except ProviderError as exc:
            if "No such subscription" not in str(exc):
                raise

    def create_transfer(self, *, payout_id, amount_minor, currency, destination):
        data = self._post(
            "/transfers",
            {
                "amount": str(amount_minor),
                "currency": currency.lower(),
                "destination": destination,
                "transfer_group": f"payout-{payout_id}",
                "metadata[xpass_payout_id]": str(payout_id),
            },
            idempotency_key=f"payout-{payout_id}",
        )
        return data["id"]

    def create_invoice_checkout(self, *, invoice_id, reference, amount_minor, currency, customer_email, return_url):
        ref = str(invoice_id)
        data = self._post(
            "/checkout/sessions",
            {
                "mode": "payment",
                "customer_email": customer_email,
                "client_reference_id": ref,
                "metadata[xpass_invoice_id]": ref,
                "payment_intent_data[metadata][xpass_invoice_id]": ref,
                "line_items[0][quantity]": "1",
                "line_items[0][price_data][currency]": currency.lower(),
                "line_items[0][price_data][unit_amount]": str(amount_minor),
                "line_items[0][price_data][product_data][name]": f"Facture XPASS {reference}",
                "success_url": f"{return_url}?paiement=retour",
                "cancel_url": f"{return_url}?paiement=annule",
            },
            idempotency_key=f"invoice-checkout-{ref}",
        )
        return Checkout(id=data["id"], url=data["url"])

    def create_connected_account(self, *, merchant_id, email, country, business_name):
        data = self._post(
            "/accounts",
            {
                "type": "express",
                "country": country,
                "email": email,
                "capabilities[card_payments][requested]": "true",
                "capabilities[transfers][requested]": "true",
                "business_profile[name]": business_name,
                "metadata[xpass_merchant_id]": str(merchant_id),
            },
            idempotency_key=f"account-{merchant_id}",
        )
        return data["id"]

    def onboarding_link(self, *, account_id, refresh_url, return_url):
        data = self._post(
            "/account_links",
            {
                "account": account_id,
                "refresh_url": refresh_url,
                "return_url": return_url,
                "type": "account_onboarding",
                "collection_options[fields]": "eventually_due",
            },
            idempotency_key=f"link-{account_id}-{uuid.uuid4()}",
        )
        return data["url"]

    def dashboard_link(self, account_id):
        return self._post(f"/accounts/{account_id}/login_links", {}, idempotency_key=f"login-{uuid.uuid4()}")["url"]

    def retrieve_account(self, account_id):
        return self._get(f"/accounts/{account_id}")


# ---------------------------------------------------------------- bac à sable


class SandboxProvider:
    """Bac à sable local : aucune somme n'est débitée ni versée. Chaque action produit un webhook signé."""

    name = "sandbox"

    def __init__(self, webhook_secret: str):
        self._secret = webhook_secret

    def create_checkout(self, *, subscription_id, price_id, customer_email, amount_minor, currency, plan_name):
        session_id = f"cs_sbx_{secrets.token_urlsafe(18)}"
        url = f"{get_settings().api_public_url}/api/v1/payments/sandbox/checkout/{session_id}"
        return Checkout(id=session_id, url=url)

    def set_cancel_at_period_end(self, psp_subscription_id, cancel):
        return None  # l'état local est mis à jour par l'appelant ; aucun service externe

    def change_subscription_price(self, psp_subscription_id, price_id):
        return None  # la prochaine facture du bac à sable portera le montant de la nouvelle formule

    def cancel_subscription(self, psp_subscription_id):
        return None  # l'état local est mis à jour par l'appelant ; aucun service externe

    def create_transfer(self, *, payout_id, amount_minor, currency, destination):
        transfer_id = f"tr_sbx_{secrets.token_hex(10)}"
        self.emit(
            "transfer.created",
            {
                "id": transfer_id,
                "object": "transfer",
                "amount": amount_minor,
                "currency": currency.lower(),
                "destination": destination,
                "metadata": {"xpass_payout_id": str(payout_id)},
            },
        )
        return transfer_id

    def create_invoice_checkout(self, *, invoice_id, reference, amount_minor, currency, customer_email, return_url):
        from urllib.parse import quote

        session_id = f"cs_sbx_inv_{invoice_id.hex}"
        api = get_settings().api_public_url
        return Checkout(id=session_id,
                        url=f"{api}/api/v1/payments/sandbox/invoice/{invoice_id}?retour={quote(return_url, safe='')}")

    def create_connected_account(self, *, merchant_id, email, country, business_name):
        return f"acct_sbx_{merchant_id.hex[:16]}"

    def onboarding_link(self, *, account_id, refresh_url, return_url):
        from urllib.parse import quote

        api = get_settings().api_public_url
        return f"{api}/api/v1/payments/sandbox/onboarding/{account_id}?retour={quote(return_url, safe='')}"

    def dashboard_link(self, account_id):
        return None  # pas d'espace prestataire en bac à sable

    def retrieve_account(self, account_id):
        return None  # l'état arrive uniquement par webhook signé (comme les autres événements du bac à sable)

    # -- émission d'événements (même chemin que les webhooks reçus du réseau)

    def event_body(self, event_type: str, obj: dict) -> bytes:
        event = {
            "id": f"evt_sbx_{secrets.token_hex(12)}",
            "object": "event",
            "type": event_type,
            "livemode": False,
            "created": int(time.time()),
            "data": {"object": obj},
        }
        return json.dumps(event).encode()

    def emit(self, event_type: str, obj: dict) -> None:
        from app.db.session import SessionLocal
        from app.modules.payments.service import receive_webhook

        body = self.event_body(event_type, obj)
        with SessionLocal() as db:
            receive_webhook(db, provider=self.name, body=body, signature=sign(self._secret, body))


def get_provider() -> PaymentProvider:
    s = get_settings()
    if s.psp_provider == "stripe":
        return StripeProvider(s.psp_secret_key)
    if s.psp_provider == "sandbox":
        return SandboxProvider(s.psp_webhook_secret)
    raise ProviderNotConfigured("Le paiement n'est pas encore configuré sur cette plateforme.")
