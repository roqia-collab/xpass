"""Relation client ↔ établissement : messagerie par réservation, favoris, avis notés, rappels de la veille."""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.booking.models import Booking
from app.modules.catalog.models import Location
from app.modules.engagement.models import Conversation, Favorite, Message, PushDevice, Review
from app.modules.identity.models import User
from app.modules.platform.service import emit

MESSAGE_WINDOW = timedelta(days=30)       # après la fin de la prestation
MESSAGE_RATE = 30                          # messages par heure et par expéditeur dans une conversation
REVIEW_WINDOW = timedelta(days=60)        # après la consommation
REMINDER_AHEAD = timedelta(hours=24)
AUTO_ACK = (
    "Bonjour, nous avons bien reçu votre message. "
    "L’établissement vous recontactera dès qu’il en prendra connaissance."
)


class EngagementError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


# ---------------------------------------------------------------- messagerie


def _messageable(booking: Booking, now: datetime) -> None:
    if booking.status not in ("confirmed", "redeemed", "cancelled", "no_show"):
        raise EngagementError("booking_not_messageable", "La messagerie s'ouvre une fois la réservation confirmée.")
    if booking.ends_at < now - MESSAGE_WINDOW:
        raise EngagementError("conversation_closed", "La messagerie est fermée 30 jours après la prestation.")


def conversation_for(db: Session, booking: Booking, *, create: bool) -> Conversation | None:
    conv = db.scalar(select(Conversation).where(Conversation.booking_id == booking.id))
    if conv is None and create:
        db.execute(insert(Conversation).values(id=uuid.uuid4(), booking_id=booking.id, location_id=booking.location_id,
                                               customer_id=booking.user_id).on_conflict_do_nothing(index_elements=["booking_id"]))
        conv = db.scalar(select(Conversation).where(Conversation.booking_id == booking.id))
    return conv


def post_message(db: Session, *, booking: Booking, sender_kind: str, user: User, body: str,
                 now: datetime | None = None) -> Message:
    now = now or datetime.now(UTC)
    body = (body or "").strip()
    if not 1 <= len(body) <= 2000:
        raise EngagementError("invalid_message", "Message vide ou trop long (2 000 caractères maximum).", 422)
    _messageable(booking, now)
    conv = conversation_for(db, booking, create=True)
    recent = db.scalar(select(func.count()).select_from(Message).where(
        Message.conversation_id == conv.id, Message.sender_user_id == user.id, Message.created_at > now - timedelta(hours=1)))
    if recent >= MESSAGE_RATE:
        raise EngagementError("too_many_messages", "Trop de messages en peu de temps : réessayez plus tard.", 429)
    msg = Message(conversation_id=conv.id, sender_kind=sender_kind, sender_user_id=user.id, body=body)
    db.add(msg)
    db.flush()
    conv.last_message_at = now
    if sender_kind == "customer":
        conv.customer_read_at = now
        n = db.scalar(select(func.count()).select_from(Message).where(
            Message.conversation_id == conv.id, Message.sender_kind == "customer"))
        if n == 1:
            db.add(Message(conversation_id=conv.id, sender_kind="system", sender_user_id=None, body=AUTO_ACK))
            db.flush()
            conv.last_message_at = datetime.now(UTC)
    else:
        conv.partner_read_at = now
    db.flush()
    emit(db, "conversation", conv.id, "message.posted", {"sender_kind": sender_kind, "booking_id": str(booking.id)})
    return msg


def messages(db: Session, conv: Conversation | None) -> list[Message]:
    if conv is None:
        return []
    return list(db.scalars(select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)).all())


def mark_read(conv: Conversation | None, side: str, now: datetime | None = None) -> None:
    if conv is not None:
        setattr(conv, f"{side}_read_at", now or datetime.now(UTC))


# ---------------------------------------------------------------- favoris


def set_favorite(db: Session, *, user_id: uuid.UUID, location_id: uuid.UUID, on: bool) -> None:
    if on:
        if db.get(Location, location_id) is None:
            raise EngagementError("location_not_found", "Établissement introuvable.", 404)
        db.execute(insert(Favorite).values(user_id=user_id, location_id=location_id).on_conflict_do_nothing())
    else:
        db.execute(Favorite.__table__.delete().where(Favorite.user_id == user_id, Favorite.location_id == location_id))


def favorite_ids(db: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    return list(db.scalars(select(Favorite.location_id).where(Favorite.user_id == user_id)
                           .order_by(Favorite.created_at.desc())).all())


# ---------------------------------------------------------------- avis notés


def create_review(db: Session, *, user: User, booking_id: uuid.UUID, rating: int, comment: str | None,
                  now: datetime | None = None) -> Review:
    now = now or datetime.now(UTC)
    booking = db.get(Booking, booking_id)
    if booking is None or booking.user_id != user.id:
        raise EngagementError("booking_not_found", "Réservation introuvable.", 404)
    if booking.status != "redeemed" or booking.redeemed_at is None:
        raise EngagementError("not_redeemed", "Vous pourrez noter la prestation une fois qu'elle aura eu lieu.")
    if booking.redeemed_at < now - REVIEW_WINDOW:
        raise EngagementError("review_closed", "Les avis sont possibles pendant 60 jours après la prestation.")
    if not 1 <= rating <= 5:
        raise EngagementError("invalid_rating", "Note de 1 à 5.", 422)
    if db.scalar(select(Review.id).where(Review.booking_id == booking.id)):
        raise EngagementError("already_reviewed", "Vous avez déjà donné votre avis sur cette prestation.")
    review = Review(booking_id=booking.id, location_id=booking.location_id, user_id=user.id, rating=rating,
                    comment=(comment or "").strip()[:1000] or None, status="published")
    db.add(review)
    db.flush()
    emit(db, "review", review.id, "review.created", {"location_id": str(booking.location_id), "rating": rating})
    return review


def rating_summary(db: Session, location_id: uuid.UUID) -> tuple[float | None, int]:
    avg, n = db.execute(select(func.avg(Review.rating), func.count()).where(
        Review.location_id == location_id, Review.status == "published")).one()
    return (round(float(avg), 1) if avg is not None else None), int(n)


def public_name(display_name: str) -> str:
    """Prénom et initiale (« Camille D. ») : jamais le nom complet sur un avis public."""
    parts = display_name.split()
    if not parts:
        return "Client XPASS"
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[1][0]}."


def reply_review(db: Session, *, review_id: uuid.UUID, location_id: uuid.UUID, reply: str,
                 now: datetime | None = None) -> Review:
    review = db.get(Review, review_id)
    if review is None or review.location_id != location_id:
        raise EngagementError("review_not_found", "Avis introuvable.", 404)
    reply = (reply or "").strip()
    if not 2 <= len(reply) <= 1000:
        raise EngagementError("invalid_reply", "Réponse de 2 à 1 000 caractères.", 422)
    review.partner_reply, review.replied_at = reply, now or datetime.now(UTC)
    db.flush()
    return review


def hide_review(db: Session, *, review_id: uuid.UUID, reason: str, by: uuid.UUID) -> Review:
    from app.modules.ops.service import _reason, audit

    reason = _reason(reason)
    review = db.get(Review, review_id)
    if review is None:
        raise EngagementError("review_not_found", "Avis introuvable.", 404)
    review.status = "hidden"
    loc = db.get(Location, review.location_id)
    audit(db, actor_kind="operator", actor_user_id=by, action="review.hidden", object_type="location",
          object_id=loc.id, object_label=loc.name, reason=reason, details={"review_id": str(review.id), "rating": review.rating})
    return review


# ---------------------------------------------------------------- appareils et rappels


def register_device(db: Session, *, user_id: uuid.UUID, token: str, platform: str) -> None:
    token = token.strip()
    if not 20 <= len(token) <= 512 or platform not in ("android", "ios", "web"):
        raise EngagementError("invalid_device", "Jeton de notification invalide.", 422)
    db.execute(insert(PushDevice).values(id=uuid.uuid4(), user_id=user_id, token=token, platform=platform)
               .on_conflict_do_update(constraint="uq_push_devices_token",
                                      set_={"user_id": user_id, "platform": platform, "last_seen_at": func.now()}))


def unregister_device(db: Session, *, user_id: uuid.UUID, token: str) -> None:
    db.execute(PushDevice.__table__.delete().where(PushDevice.user_id == user_id, PushDevice.token == token))


def due_reminders(db: Session, now: datetime | None = None, limit: int = 200) -> int:
    """Réservations confirmées qui commencent dans les 24 h : un rappel (e-mail et notification), une seule fois.

    Les réservations prises moins de 2 heures avant le début n'en reçoivent pas (la confirmation suffit).
    """
    now = now or datetime.now(UTC)
    rows = db.scalars(
        select(Booking).where(Booking.status == "confirmed", Booking.reminder_sent_at.is_(None),
                              Booking.starts_at > now, Booking.starts_at <= now + REMINDER_AHEAD,
                              Booking.created_at <= Booking.starts_at - timedelta(hours=2))
        .order_by(Booking.starts_at).limit(limit).with_for_update(skip_locked=True)
    ).all()
    for b in rows:
        b.reminder_sent_at = now
        emit(db, "booking", b.id, "booking.reminder", {})
    db.flush()
    return len(rows)


def unread_for_customer(db: Session, user_id: uuid.UUID) -> int:
    last = select(Message.sender_kind).where(Message.conversation_id == Conversation.id) \
        .order_by(Message.created_at.desc()).limit(1).scalar_subquery()
    return int(db.scalar(select(func.count()).select_from(Conversation).where(
        Conversation.customer_id == user_id, last != "customer",
        (Conversation.customer_read_at.is_(None)) | (Conversation.customer_read_at < Conversation.last_message_at))) or 0)


def partner_has_unread(db: Session, conv: Conversation) -> bool:
    last_customer = db.scalar(
        select(func.max(Message.created_at)).where(Message.conversation_id == conv.id, Message.sender_kind == "customer"))
    return last_customer is not None and (conv.partner_read_at is None or conv.partner_read_at < last_customer)

