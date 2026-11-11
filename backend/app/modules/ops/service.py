"""Administration (maquettes 26 à 28) : décisions motivées et tracées.

- Toute décision d'un opérateur exige un motif et écrit une ligne d'audit (en ajout seul).
- Validation commerciale et vérification PSP sont distinctes : XPASS valide le dossier commercial,
  seul le prestataire de paiement vérifie l'identité (KYC/KYB). En bac à sable, l'administration
  peut simuler cette vérification, jamais avec un vrai prestataire.
- Litige : la restitution recrée des crédits de la même source que ceux consommés ; l'éventuel
  ajustement partenaire est déduit d'un prochain versement (un versement déjà payé n'est jamais modifié).
"""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.booking.models import Booking
from app.modules.catalog.models import Location, Market, Merchant
from app.modules.employer.models import EmployerContract
from app.modules.identity.models import Membership, Organization, User
from app.modules.ops.models import OPEN_DISPUTES, AuditEvent, Dispute
from app.modules.platform.service import emit
from app.modules.redemption.models import PartnerPayable
from app.modules.wallet import service as wallet_service
from app.modules.wallet.models import CreditJournal, CreditJournalLine, CreditLot, Wallet

ADMIN = ("platform_admin",)
STAFF = ("platform_admin", "platform_operator")
DISPUTE_WINDOW_DAYS = 30
MIN_RESTORED_VALIDITY_DAYS = 30


class OpsError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def require(principal, roles: tuple[str, ...]) -> None:
    if not principal.has_platform_role(*roles):
        raise OpsError("forbidden", "Action réservée à l'administration XPASS." if roles == ADMIN
                       else "Accès réservé à l'équipe XPASS.", 403)


def _reason(reason: str | None) -> str:
    reason = (reason or "").strip()
    if len(reason) < 5:
        raise OpsError("reason_required", "Indiquez le motif de la décision (5 caractères minimum).", 422)
    return reason


def audit(db: Session, *, actor_kind: str, actor_user_id: uuid.UUID | None, action: str, object_type: str,
          object_id: uuid.UUID, object_label: str, reason: str | None = None, details: dict | None = None) -> None:
    db.add(AuditEvent(actor_kind=actor_kind, actor_user_id=actor_user_id, action=action, object_type=object_type,
                      object_id=object_id, object_label=object_label[:200], reason=reason, details=details or {}))
    db.flush()


# ---------------------------------------------------------------- partenaires


DECISIONS = {"approve": "approved", "request_documents": "documents_missing", "suspend": "suspended",
             "reopen": "pending_review"}


def decide_merchant(db: Session, *, merchant_id: uuid.UUID, decision: str, reason: str, by: uuid.UUID) -> Merchant:
    reason = _reason(reason)
    merchant = db.scalar(select(Merchant).where(Merchant.id == merchant_id).with_for_update())
    if merchant is None:
        raise OpsError("merchant_not_found", "Partenaire introuvable.", 404)
    if decision not in DECISIONS:
        raise OpsError("invalid_decision", "Décision inconnue.", 422)
    before, after = merchant.commercial_status, DECISIONS[decision]
    if before == after:
        raise OpsError("no_change", "Le dossier est déjà dans cet état.", 409)
    merchant.commercial_status = after
    audit(db, actor_kind="operator", actor_user_id=by, action=f"merchant.{decision}", object_type="merchant",
          object_id=merchant.id, object_label=merchant.display_name, reason=reason,
          details={"from": before, "to": after})
    emit(db, "merchant", merchant.id, "merchant.commercial_status_changed", {"from": before, "to": after})
    return merchant


def sandbox_psp_verify(db: Session, *, merchant_id: uuid.UUID, reason: str, by: uuid.UUID) -> Merchant:
    """Bac à sable uniquement : simule la vérification KYC/KYB du prestataire."""
    if get_settings().psp_provider != "sandbox":
        raise OpsError("psp_only", "La vérification d'identité est effectuée par le prestataire de paiement.", 409)
    reason = _reason(reason)
    merchant = db.scalar(select(Merchant).where(Merchant.id == merchant_id).with_for_update())
    if merchant is None:
        raise OpsError("merchant_not_found", "Partenaire introuvable.", 404)
    merchant.psp_status = "verified"
    merchant.psp_account_id = merchant.psp_account_id or f"acct_sbx_{merchant.id.hex[:16]}"
    audit(db, actor_kind="operator", actor_user_id=by, action="merchant.psp_sandbox_verified", object_type="merchant",
          object_id=merchant.id, object_label=merchant.display_name, reason=reason)
    return merchant


def apply_psp_account_update(db: Session, *, provider: str, obj: dict) -> str:
    """Webhook `account.updated` : le prestataire indique si le compte peut recevoir des versements."""
    merchant = db.scalar(select(Merchant).where(Merchant.psp_account_id == obj.get("id")).with_for_update())
    if merchant is None:
        return "ignored"
    before = merchant.psp_status
    if obj.get("payouts_enabled") and obj.get("charges_enabled", True):
        merchant.psp_status = "verified"
    elif (obj.get("requirements") or {}).get("disabled_reason", "").startswith("rejected"):
        merchant.psp_status = "rejected"
    else:
        merchant.psp_status = "pending"
    if before != merchant.psp_status:
        audit(db, actor_kind="system", actor_user_id=None, action="merchant.psp_status", object_type="merchant",
              object_id=merchant.id, object_label=merchant.display_name, details={"from": before, "to": merchant.psp_status,
                                                                                  "provider": provider})
    return "applied"


def moderate_location(db: Session, *, location_id: uuid.UUID, publish: bool, reason: str, by: uuid.UUID) -> Location:
    reason = _reason(reason)
    loc = db.scalar(select(Location).where(Location.id == location_id).with_for_update())
    if loc is None:
        raise OpsError("location_not_found", "Établissement introuvable.", 404)
    before = loc.status
    loc.status = "published" if publish else "hidden"
    audit(db, actor_kind="operator", actor_user_id=by, action="location.publish" if publish else "location.hide",
          object_type="location", object_id=loc.id, object_label=loc.name, reason=reason,
          details={"from": before, "to": loc.status})
    return loc


# ---------------------------------------------------------------- litiges


def _consumed_by_lot(db: Session, booking_id: uuid.UUID) -> list[tuple[CreditLot, int]]:
    rows = db.execute(
        select(CreditJournalLine.lot_id, func.sum(CreditJournalLine.amount))
        .join(CreditJournal, CreditJournal.id == CreditJournalLine.journal_id)
        .where(CreditJournal.booking_id == booking_id, CreditJournal.kind == "capture",
               CreditJournalLine.account == "consumed")
        .group_by(CreditJournalLine.lot_id)
    ).all()
    return [(db.get(CreditLot, lot_id), int(n)) for lot_id, n in rows if n]


def open_dispute(db: Session, *, user_id: uuid.UUID, booking_id: uuid.UUID, reason: str,
                 now: datetime | None = None) -> Dispute:
    now = now or datetime.now(UTC)
    reason = (reason or "").strip()
    if len(reason) < 10:
        raise OpsError("reason_required", "Décrivez le problème en quelques mots (10 caractères minimum).", 422)
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if booking is None or booking.user_id != user_id:
        raise OpsError("booking_not_found", "Réservation introuvable.", 404)
    eligible = booking.status == "redeemed" or (booking.status == "cancelled" and booking.late_cancellation)
    if not eligible:
        raise OpsError("not_disputable", "Une réclamation concerne une prestation utilisée ou une annulation tardive.", 409)
    reference_at = booking.redeemed_at or booking.cancelled_at
    if reference_at and now - reference_at > timedelta(days=DISPUTE_WINDOW_DAYS):
        raise OpsError("too_late", f"Le délai de réclamation ({DISPUTE_WINDOW_DAYS} jours) est dépassé.", 409)
    if db.scalar(select(Dispute.id).where(Dispute.booking_id == booking.id, Dispute.status.in_(OPEN_DISPUTES))):
        raise OpsError("already_open", "Une réclamation est déjà en cours pour cette réservation.", 409)
    if db.scalar(select(Dispute.id).where(Dispute.booking_id == booking.id, Dispute.status == "resolved_refund")):
        raise OpsError("already_refunded", "Cette réservation a déjà fait l'objet d'une restitution.", 409)
    n = db.scalar(text("SELECT nextval('dispute_reference_seq')"))
    dispute = Dispute(reference=f"L-{n}", booking_id=booking.id, opened_by=user_id, reason=reason[:2000], status="open")
    db.add(dispute)
    db.flush()
    audit(db, actor_kind="customer", actor_user_id=user_id, action="dispute.opened", object_type="dispute",
          object_id=dispute.id, object_label=dispute.reference, reason=dispute.reason)
    emit(db, "dispute", dispute.id, "dispute.opened", {"booking_id": str(booking.id)})
    return dispute


def _load_dispute(db: Session, dispute_id: uuid.UUID) -> Dispute:
    d = db.scalar(select(Dispute).where(Dispute.id == dispute_id).with_for_update())
    if d is None:
        raise OpsError("dispute_not_found", "Litige introuvable.", 404)
    return d


def update_dispute(db: Session, *, dispute_id: uuid.UUID, status: str, notes: str | None, reason: str,
                   by: uuid.UUID) -> Dispute:
    reason = _reason(reason)
    d = _load_dispute(db, dispute_id)
    if d.status not in OPEN_DISPUTES:
        raise OpsError("closed", "Ce litige est clos.", 409)
    if status not in OPEN_DISPUTES:
        raise OpsError("invalid_status", "Utilisez « restituer » ou « rejeter » pour clore le litige.", 422)
    before = d.status
    d.status = status
    if notes is not None:
        d.operator_notes = notes.strip()[:4000] or None
    audit(db, actor_kind="operator", actor_user_id=by, action="dispute.updated", object_type="dispute",
          object_id=d.id, object_label=d.reference, reason=reason, details={"from": before, "to": status})
    return d


def refund_dispute(db: Session, *, dispute_id: uuid.UUID, partner_adjustment_minor: int, reason: str, by: uuid.UUID,
                   now: datetime | None = None) -> Dispute:
    """Restitue au client TOUS les crédits consommés (par source, lot par lot) et, si demandé, retient un
    montant sur un prochain versement du partenaire. Idempotent par construction (index uniques)."""
    from app.modules.settlement.service import create_adjustment

    now = now or datetime.now(UTC)
    reason = _reason(reason)
    d = _load_dispute(db, dispute_id)
    if d.status not in OPEN_DISPUTES:
        raise OpsError("closed", "Ce litige est clos.", 409)
    booking = db.get(Booking, d.booking_id)
    consumed = _consumed_by_lot(db, booking.id)
    if not consumed:
        raise OpsError("nothing_to_restore", "Aucun crédit consommé pour cette réservation.", 409)
    payable = db.scalar(select(PartnerPayable).where(PartnerPayable.booking_id == booking.id))
    if partner_adjustment_minor < 0:
        raise OpsError("invalid_amount", "Montant invalide.", 422)
    if partner_adjustment_minor and (payable is None or payable.amount_minor is None
                                     or partner_adjustment_minor > payable.amount_minor - payable.commission_minor):
        raise OpsError("adjustment_too_high", "L'ajustement ne peut pas dépasser ce qui revient au partenaire.", 422)

    wallet = db.scalar(select(Wallet).where(Wallet.id == booking.wallet_id).with_for_update())
    restored = 0
    for lot, amount in consumed:
        expires = None if lot.expires_at is None else max(lot.expires_at, now + timedelta(days=MIN_RESTORED_VALIDITY_DAYS))
        wallet_service.grant(db, wallet, source=lot.source, amount=amount, label=f"Restitution · litige {d.reference}",
                             origin_type="dispute_refund", origin_ref=f"{d.id}:{lot.id}", expires_at=expires,
                             eligible_categories=lot.eligible_categories)
        restored += amount
    if partner_adjustment_minor:
        merchant_id = db.scalar(select(Location.merchant_id).where(Location.id == booking.location_id))
        create_adjustment(db, merchant_id=merchant_id, amount_minor=-partner_adjustment_minor,
                          label=f"Litige {d.reference}", created_by=by)
    d.status, d.credits_restored = "resolved_refund", restored
    d.partner_adjustment_minor = partner_adjustment_minor or None
    d.resolution_reason, d.resolved_by, d.resolved_at = reason, by, now
    audit(db, actor_kind="operator", actor_user_id=by, action="dispute.refunded", object_type="dispute",
          object_id=d.id, object_label=d.reference, reason=reason,
          details={"credits": restored, "partner_adjustment_minor": partner_adjustment_minor})
    emit(db, "dispute", d.id, "dispute.refunded", {"credits": restored})
    return d


def reject_dispute(db: Session, *, dispute_id: uuid.UUID, reason: str, by: uuid.UUID, now: datetime | None = None) -> Dispute:
    reason = _reason(reason)
    d = _load_dispute(db, dispute_id)
    if d.status not in OPEN_DISPUTES:
        raise OpsError("closed", "Ce litige est clos.", 409)
    d.status, d.resolution_reason, d.resolved_by, d.resolved_at = "resolved_rejected", reason, by, now or datetime.now(UTC)
    audit(db, actor_kind="operator", actor_user_id=by, action="dispute.rejected", object_type="dispute",
          object_id=d.id, object_label=d.reference, reason=reason)
    emit(db, "dispute", d.id, "dispute.rejected", {})
    return d


# ---------------------------------------------------------------- rapprochement


def payout_action(db: Session, *, payout_id: uuid.UUID, action: str, reason: str, by: uuid.UUID) -> None:
    """`retry` : un versement en échec repart en attente (nouveau transfert).
    `close` : un écart examiné est clos (montant confirmé par le prestataire accepté), avec motif."""
    from app.modules.settlement.models import PartnerPayout

    reason = _reason(reason)
    payout = db.scalar(select(PartnerPayout).where(PartnerPayout.id == payout_id).with_for_update())
    if payout is None:
        raise OpsError("payout_not_found", "Versement introuvable.", 404)
    before = payout.status
    if action == "retry" and payout.status == "failed":
        payout.status, payout.psp_transfer_id, payout.provider = "pending", None, None
    elif action == "close" and payout.status == "to_reconcile":
        payout.status = "paid"
        payout.paid_at = payout.paid_at or datetime.now(UTC)
    else:
        raise OpsError("invalid_action", "Action impossible dans l'état actuel du versement.", 409)
    audit(db, actor_kind="operator", actor_user_id=by, action=f"payout.{action}", object_type="partner_payout",
          object_id=payout.id, object_label=f"Versement {payout.period_start}", reason=reason,
          details={"from": before, "to": payout.status, "net_minor": payout.net_minor,
                   "confirmed_minor": payout.confirmed_minor})


def webhook_action(db: Session, *, event_id: uuid.UUID, action: str, reason: str, by: uuid.UUID) -> None:
    """Anomalie de paiement : `retry` (remise en file après correction) ou `dismiss` (classée, motivée)."""
    from app.modules.payments.models import PaymentWebhookEvent

    reason = _reason(reason)
    ev = db.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.id == event_id).with_for_update())
    if ev is None or ev.processed_at is not None:
        raise OpsError("event_not_found", "Événement introuvable ou déjà traité.", 404)
    if action == "retry":
        ev.attempts = 0
    elif action == "dismiss":
        ev.processed_at, ev.outcome = datetime.now(UTC), "dismissed"
    else:
        raise OpsError("invalid_action", "Action inconnue.", 422)
    audit(db, actor_kind="operator", actor_user_id=by, action=f"payment_event.{action}", object_type="payment_event",
          object_id=ev.id, object_label=f"{ev.event_type} {ev.event_id}", reason=reason, details={"error": ev.last_error})



# ---------------------------------------------------------------- accès professionnels


ACCESS_ROLES = {
    "merchant": ("merchant_owner", "merchant_staff"),
    "organization": ("hr_admin", "hr_viewer"),
}


def _scope_label(db: Session, scope_type: str, scope_id: uuid.UUID) -> str:
    if scope_type == "merchant":
        m = db.get(Merchant, scope_id)
        if m is None:
            raise OpsError("merchant_not_found", "Partenaire introuvable.", 404)
        return m.display_name
    o = db.get(Organization, scope_id)
    if o is None:
        raise OpsError("organization_not_found", "Entreprise introuvable.", 404)
    return o.name


def create_rh_service(db: Session, *, name: str, city_label: str, hr_email: str, by: uuid.UUID,
                      by_name: str | None = None) -> Organization:
    """L'admin crée un service RH : entreprise, contrat actif, et accès administrateur RH."""
    name = (name or "").strip()
    if len(name) < 2 or len(name) > 160:
        raise OpsError("invalid_name", "Indiquez le nom du service RH (2 à 160 caractères).", 422)
    market_id = db.scalar(select(Market.id).where(Market.code == "FR"))
    if market_id is None:
        raise OpsError("market_missing", "Le marché France n'est pas prêt.", 503)
    from app.modules.catalog.launch import LaunchError, require_opened_label

    try:
        city_name = require_opened_label(db, city_label)
    except LaunchError as exc:
        raise OpsError(exc.code, exc.message, exc.status) from exc
    org = Organization(
        market_id=market_id, name=name, city_label=city_name, is_demo=False,
    )
    db.add(org)
    db.flush()
    today = datetime.now(UTC).date().replace(day=1)
    db.add(EmployerContract(
        organization_id=org.id, status="active", credit_price_minor=100, currency="EUR",
        payment_terms_days=30, starts_on=today, term_months=12, covered_cities=["Paris"],
        commission_bps=1000, free_cancellation_hours=24, is_demo=False,
    ))
    db.flush()
    grant_access(db, email=hr_email, scope_type="organization", scope_id=org.id, role="hr_admin",
                 by=by, actor_kind="operator", by_name=by_name)
    audit(db, actor_kind="operator", actor_user_id=by, action="organization.created", object_type="organization",
          object_id=org.id, object_label=org.name, details={"hr_email": hr_email.strip().lower()})
    return org


def grant_access(db: Session, *, email: str, scope_type: str, scope_id: uuid.UUID, role: str,
                 by: uuid.UUID, actor_kind: str = "operator", by_name: str | None = None) -> Membership:
    """Donne un rôle commerçant ou RH à une adresse e-mail.

    Si aucun compte n'existe, il est préparé : la personne crée ensuite son compte sur la page sécurisée avec
    cette adresse, et la connexion (e-mail vérifié) le relie automatiquement. Le mot de passe n'est jamais géré ici.
    """
    email = (email or "").strip().lower()
    if "@" not in email or "." not in email.split("@")[-1] or len(email) > 254:
        raise OpsError("invalid_email", "Adresse e-mail invalide.", 422)
    if role not in ACCESS_ROLES.get(scope_type, ()):
        raise OpsError("invalid_role", "Rôle incompatible avec cet espace.", 422)
    label = _scope_label(db, scope_type, scope_id)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, display_name=email.split("@")[0], is_demo=False)
        db.add(user)
        db.flush()
    elif user.deleted_at is not None or not user.is_active:
        raise OpsError("account_closed", "Ce compte est fermé.", 409)
    exists = db.scalar(select(Membership.id).where(
        Membership.user_id == user.id, Membership.scope_type == scope_type, Membership.scope_id == scope_id,
        Membership.role == role))
    if exists is not None:
        raise OpsError("already_granted", "Cette personne a déjà ce rôle.", 409)
    membership = Membership(user_id=user.id, scope_type=scope_type, scope_id=scope_id, role=role)
    db.add(membership)
    db.flush()
    audit(db, actor_kind=actor_kind, actor_user_id=by, action="access.granted", object_type=scope_type,
          object_id=scope_id, object_label=label, details={"email": email, "role": role})
    emit(db, "membership", membership.id, "access.granted",
         {"scope_type": scope_type, "scope_label": label, "role": role, "by_name": by_name})
    return membership


def revoke_access(db: Session, *, membership_id: uuid.UUID, by: uuid.UUID, scope_id: uuid.UUID | None = None,
                  actor_kind: str = "operator") -> None:
    """Retire un accès. Un commerçant (`scope_id` imposé) ne retire ni son propre accès ni le dernier responsable."""
    membership = db.get(Membership, membership_id)
    if membership is None or membership.scope_type not in ACCESS_ROLES or (
            scope_id is not None and membership.scope_id != scope_id):
        raise OpsError("access_not_found", "Accès introuvable.", 404)
    if actor_kind == "partner":
        if membership.user_id == by:
            raise OpsError("own_access", "Vous ne pouvez pas retirer votre propre accès.", 409)
        if membership.role == "merchant_owner":
            owners = db.scalar(select(func.count()).select_from(Membership).where(
                Membership.scope_id == membership.scope_id, Membership.role == "merchant_owner"))
            if owners <= 1:
                raise OpsError("last_owner", "L'établissement doit garder au moins un responsable.", 409)
    user = db.get(User, membership.user_id)
    label = _scope_label(db, membership.scope_type, membership.scope_id)
    audit(db, actor_kind=actor_kind, actor_user_id=by, action="access.revoked", object_type=membership.scope_type,
          object_id=membership.scope_id, object_label=label, details={"email": user.email, "role": membership.role})
    db.delete(membership)
    db.flush()


def set_demo_visibility(db: Session, *, visible: bool, reason: str, by: uuid.UUID) -> int:
    reason = _reason(reason)
    target, source = ("published", "hidden") if visible else ("hidden", "published")
    locations = db.scalars(select(Location).where(Location.is_demo.is_(True), Location.status == source)).all()
    for loc in locations:
        loc.status = target
        audit(db, actor_kind="operator", actor_user_id=by, action="location.publish" if visible else "location.hide",
              object_type="location", object_id=loc.id, object_label=loc.name, reason=reason,
              details={"from": source, "to": target, "demo": True})
    db.flush()
    return len(locations)
