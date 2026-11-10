"""Compte client (écran 16) : préférences, export des données, suppression, demandes d'assistance."""
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session

from app.modules.booking.models import ACTIVE_STATUSES, Booking
from app.modules.catalog.models import Location, OfferVersion
from app.modules.employer.models import Employee
from app.modules.identity.models import Membership, User
from app.modules.ops.models import Dispute, SupportRequest
from app.modules.payments.models import Invoice, Subscription
from app.modules.platform.service import emit
from app.modules.wallet.models import CreditJournal, CreditJournalLine, CreditLot, Wallet

LOCALES = ("fr", "en", "ar")


class AccountError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def update_profile(db: Session, user: User, *, display_name: str | None, locale: str | None,
                   notify_email: bool | None) -> User:
    if display_name is not None:
        name = display_name.strip()
        if not 1 <= len(name) <= 120:
            raise AccountError("invalid_name", "Nom invalide.", 422)
        user.display_name = name
    if locale is not None:
        if locale not in LOCALES:
            raise AccountError("invalid_locale", "Langue non disponible.", 422)
        user.locale = locale
    if notify_email is not None:
        user.notify_email = notify_email
    db.flush()
    return user


def export_data(db: Session, user: User) -> dict:
    """Portabilité (RGPD) : les données de l'utilisateur dans un format lisible par machine."""
    bookings = db.execute(
        select(Booking, Location.name, OfferVersion.title)
        .join(Location, Location.id == Booking.location_id)
        .join(OfferVersion, OfferVersion.id == Booking.offer_version_id)
        .where(Booking.user_id == user.id).order_by(Booking.created_at)
    ).all()
    lots = db.execute(select(CreditLot).join(Wallet, Wallet.id == CreditLot.wallet_id).where(Wallet.user_id == user.id)).scalars().all()
    movements = db.execute(
        select(CreditJournal.kind, CreditJournal.memo, CreditJournal.created_at, func.sum(CreditJournalLine.amount))
        .join(CreditJournalLine, CreditJournalLine.journal_id == CreditJournal.id)
        .join(Wallet, Wallet.id == CreditJournal.wallet_id)
        .where(Wallet.user_id == user.id, CreditJournalLine.account == "available")
        .group_by(CreditJournal.id).order_by(CreditJournal.created_at)
    ).all()
    support = db.scalars(select(SupportRequest).where(SupportRequest.user_id == user.id)).all()
    disputes = db.scalars(select(Dispute).join(Booking, Booking.id == Dispute.booking_id).where(Booking.user_id == user.id)).all()
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "account": {"email": user.email, "display_name": user.display_name, "locale": user.locale,
                    "notify_email": user.notify_email, "created_at": user.created_at.isoformat()},
        "bookings": [{"location": loc, "offer": title, "starts_at": b.starts_at.isoformat(), "status": b.status,
                      "party_size": b.party_size, "total_credits": b.total_credits} for b, loc, title in bookings],
        "credit_lots": [{"source": lot.source, "label": lot.label, "granted_credits": lot.granted_credits,
                         "expires_at": lot.expires_at.isoformat() if lot.expires_at else None} for lot in lots],
        "credit_movements": [{"kind": k, "memo": m, "at": at.isoformat(), "available_delta": int(n)}
                             for k, m, at, n in movements],
        "support_requests": [{"reference": r.reference, "subject": r.subject, "message": r.message,
                              "status": r.status, "reply": r.reply} for r in support],
        "disputes": [{"reference": d.reference, "reason": d.reason, "status": d.status,
                      "credits_restored": d.credits_restored} for d in disputes],
    }


def delete_account(db: Session, user: User, now: datetime | None = None) -> None:
    """Efface les données personnelles et ferme le compte.

    Les écritures financières (journal de crédits, reçus, dettes partenaires) sont conservées, sans
    identité, pour les obligations comptables. Les crédits restants sont perdus (l'écran le signale).
    """
    now = now or datetime.now(UTC)
    upcoming = db.scalar(select(func.count()).select_from(Booking).where(
        Booking.user_id == user.id, Booking.status.in_(ACTIVE_STATUSES), Booking.ends_at > now))
    if upcoming:
        raise AccountError("has_bookings", "Annulez d'abord vos réservations à venir.", 409)
    if db.scalar(select(func.count()).select_from(Membership).where(Membership.user_id == user.id)):
        raise AccountError("has_roles", "Ce compte a un accès professionnel : contactez l'équipe XPASS.", 409)
    db.execute(update(Employee).where(Employee.user_id == user.id).values(status="removed", user_id=None))
    db.execute(update(SupportRequest).where(SupportRequest.user_id == user.id, SupportRequest.status != "closed")
               .values(status="closed"))
    db.execute(delete(Membership).where(Membership.user_id == user.id))
    db.execute(text("DELETE FROM idempotency_keys WHERE user_id = :u"), {"u": user.id})
    user.email = f"supprime-{user.id.hex}@deleted.invalid"
    user.display_name = "Compte supprimé"
    user.oidc_subject = None
    user.is_active = False
    user.notify_email = False
    user.deleted_at = now
    db.flush()


def open_support(db: Session, user: User, *, category: str, subject: str, message: str,
                 booking_id: uuid.UUID | None) -> SupportRequest:
    subject, message = subject.strip(), message.strip()
    if len(subject) < 3 or len(message) < 10:
        raise AccountError("too_short", "Précisez l'objet et décrivez votre demande (10 caractères minimum).", 422)
    if booking_id is not None:
        owner = db.scalar(select(Booking.user_id).where(Booking.id == booking_id))
        if owner != user.id:
            raise AccountError("booking_not_found", "Réservation introuvable.", 404)
    open_count = db.scalar(select(func.count()).select_from(SupportRequest).where(
        SupportRequest.user_id == user.id, SupportRequest.status == "open"))
    if open_count >= 5:
        raise AccountError("too_many", "Vous avez déjà 5 demandes en cours : l'équipe vous répond au plus vite.", 429)
    n = db.scalar(text("SELECT nextval('support_reference_seq')"))
    req = SupportRequest(reference=f"S-{n}", user_id=user.id, category=category, subject=subject[:160],
                         message=message[:4000], booking_id=booking_id, status="open")
    db.add(req)
    db.flush()
    emit(db, "support_request", req.id, "support.opened", {"category": category})
    return req


def answer_support(db: Session, *, request_id: uuid.UUID, reply: str, close: bool, by: uuid.UUID) -> SupportRequest:
    from app.modules.ops.service import audit

    reply = reply.strip()
    if len(reply) < 5:
        raise AccountError("too_short", "Rédigez une réponse.", 422)
    req = db.scalar(select(SupportRequest).where(SupportRequest.id == request_id).with_for_update())
    if req is None:
        raise AccountError("not_found", "Demande introuvable.", 404)
    if req.status == "closed":
        raise AccountError("closed", "Cette demande est close.", 409)
    req.reply, req.replied_by, req.replied_at = reply[:4000], by, datetime.now(UTC)
    req.status = "closed" if close else "answered"
    audit(db, actor_kind="operator", actor_user_id=by, action="support.answered", object_type="support_request",
          object_id=req.id, object_label=req.reference, reason=None, details={"closed": close})
    emit(db, "support_request", req.id, "support.answered", {})
    return req


def list_notifications(db: Session, user: User, *, limit: int = 40) -> list[dict]:
    """Fil d'alertes du client, construit à partir des événements déjà enregistrés (pas de table dédiée)."""
    items: list[dict] = []
    bookings = db.execute(
        select(Booking, Location.name, OfferVersion.title)
        .join(Location, Location.id == Booking.location_id)
        .join(OfferVersion, OfferVersion.id == Booking.offer_version_id)
        .where(Booking.user_id == user.id, Booking.status.in_(("confirmed", "cancelled", "redeemed")))
        .order_by(Booking.created_at.desc())
        .limit(30)
    ).all()
    for b, loc, title in bookings:
        if b.status == "confirmed":
            kind, headline, body, when = ("booking.confirmed", "Réservation confirmée",
                                          f"{title} chez {loc}.", b.confirmed_at or b.created_at)
            route = f"/reservations/{b.id}"
        elif b.status == "cancelled":
            kind, headline, body, when = ("booking.cancelled", "Réservation annulée",
                                          f"{title} chez {loc}.", b.cancelled_at or b.created_at)
            route = f"/reservations/{b.id}"
        else:
            kind, headline, body, when = ("booking.redeemed", "Prestation effectuée",
                                          f"Merci pour votre visite chez {loc}.", b.redeemed_at or b.created_at)
            route = f"/reservations/{b.id}/recu"
        items.append({"id": f"booking:{b.id}:{b.status}", "kind": kind, "title": headline,
                      "body": body, "route": route, "created_at": when})
    for inv in db.scalars(select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.paid_at.desc()).limit(10)):
        items.append({"id": f"invoice:{inv.id}", "kind": "invoice.paid", "title": "Paiement confirmé",
                      "body": f"{inv.credits} crédits ont été ajoutés à votre compte.",
                      "route": "/abonnement", "created_at": inv.paid_at})
    for sub in db.scalars(select(Subscription).where(Subscription.user_id == user.id,
                                                     Subscription.status == "past_due")):
        items.append({"id": f"subscription:{sub.id}:past_due", "kind": "payment.refused",
                      "title": "Paiement refusé",
                      "body": "Le renouvellement de votre abonnement n’a pas abouti. Vous pouvez réessayer depuis Mon abonnement.",
                      "route": "/abonnement", "created_at": sub.updated_at or sub.created_at})
    for req in db.scalars(select(SupportRequest).where(SupportRequest.user_id == user.id,
                                                       SupportRequest.reply.is_not(None))
                          .order_by(SupportRequest.replied_at.desc()).limit(10)):
        items.append({"id": f"support:{req.id}", "kind": "support.replied",
                      "title": "Réponse de l’équipe XPASS", "body": req.subject,
                      "route": "/profil", "created_at": req.replied_at or req.created_at})
    items.sort(key=lambda x: x["created_at"] or datetime.min.replace(tzinfo=UTC), reverse=True)
    return items[:limit]
