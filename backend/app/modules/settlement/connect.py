"""Compte de versement du commerçant (Stripe Connect, comptes Express).

L'identité du représentant, les justificatifs et l'IBAN sont saisis sur la page du prestataire : XPASS ne les
voit ni ne les stocke. XPASS conserve seulement l'identifiant du compte et son statut, mis à jour par le webhook
signé `account.updated` (ou par une relecture explicite du compte au retour du commerçant).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.catalog.models import Market, Merchant
from app.modules.identity.models import User
from app.modules.ops.service import apply_psp_account_update, audit
from app.modules.payments.provider import PaymentProvider, ProviderError, ProviderNotConfigured, get_provider

# Statuts du partenaire qui autorisent l'ouverture du compte de versement (pas de suspension en cours).
ONBOARDING_ALLOWED = ("pending_review", "documents_missing", "approved")


class ConnectError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _provider() -> PaymentProvider:
    try:
        return get_provider()
    except ProviderNotConfigured as exc:
        raise ConnectError("psp_not_configured",
                           "Les versements ne sont pas encore configurés sur la plateforme (prestataire de paiement).", 503) from exc


def _urls() -> tuple[str, str]:
    base = f"{get_settings().portals_public_url.rstrip('/')}/partner/reglements"
    return f"{base}?versements=relancer", f"{base}?versements=retour"


def start_onboarding(db: Session, *, merchant_id, user: User) -> str:
    """Crée le compte connecté si besoin, puis renvoie le lien (à usage unique) de la page du prestataire."""
    merchant = db.scalar(select(Merchant).where(Merchant.id == merchant_id).with_for_update())
    if merchant is None:
        raise ConnectError("merchant_not_found", "Partenaire introuvable.", 404)
    if merchant.commercial_status not in ONBOARDING_ALLOWED:
        raise ConnectError("merchant_not_allowed", "Le compte partenaire doit être actif pour ouvrir les versements.")
    provider = _provider()
    if merchant.psp_status == "rejected":
        raise ConnectError("psp_rejected", "Le prestataire a refusé ce compte : contactez l'assistance XPASS.")
    try:
        if not merchant.psp_account_id:
            market = db.get(Market, merchant.market_id)
            merchant.psp_account_id = provider.create_connected_account(
                merchant_id=merchant.id, email=user.email, country=market.country_code,
                business_name=merchant.display_name)
            merchant.psp_status = "pending"
            audit(db, actor_kind="partner", actor_user_id=user.id, action="merchant.payout_account_created",
                  object_type="merchant", object_id=merchant.id, object_label=merchant.display_name,
                  details={"provider": provider.name})
            db.flush()
        refresh_url, return_url = _urls()
        return provider.onboarding_link(account_id=merchant.psp_account_id, refresh_url=refresh_url,
                                        return_url=return_url)
    except ProviderError as exc:
        raise ConnectError("psp_error", f"Le prestataire de paiement n'a pas répondu : {exc}", 502) from exc


def refresh_status(db: Session, *, merchant_id) -> str:
    """Relit le compte chez le prestataire (retour du commerçant) ; le webhook reste la source principale."""
    merchant = db.get(Merchant, merchant_id)
    if merchant is None or not merchant.psp_account_id:
        return merchant.psp_status if merchant else "not_started"
    provider = _provider()
    try:
        account = provider.retrieve_account(merchant.psp_account_id)
    except ProviderError as exc:
        raise ConnectError("psp_error", f"Le prestataire de paiement n'a pas répondu : {exc}", 502) from exc
    if account is not None:
        apply_psp_account_update(db, provider=provider.name, obj=account)
        db.flush()
    return merchant.psp_status


def dashboard_url(db: Session, *, merchant_id) -> str:
    merchant = db.get(Merchant, merchant_id)
    if merchant is None or not merchant.psp_account_id or merchant.psp_status != "verified":
        raise ConnectError("account_not_ready", "Votre compte de versement n'est pas encore vérifié.")
    provider = _provider()
    try:
        url = provider.dashboard_link(merchant.psp_account_id)
    except ProviderError as exc:
        raise ConnectError("psp_error", f"Le prestataire de paiement n'a pas répondu : {exc}", 502) from exc
    if not url:
        raise ConnectError("no_dashboard", "Pas d'espace prestataire en mode démonstration (bac à sable).")
    return url
