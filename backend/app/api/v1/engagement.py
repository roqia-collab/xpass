"""Relation client ↔ établissement : messagerie par réservation, favoris, avis notés, appareils de notification."""
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentPrincipal, DbSession
from app.modules.booking.models import Booking
from app.modules.catalog import management as m
from app.modules.catalog.models import Category, Location, OfferVersion, Subcategory
from app.modules.engagement import service as eng
from app.modules.engagement.models import Conversation, Message, Review
from app.modules.identity.models import User
from app.modules.ops import service as ops

router = APIRouter(tags=["relation client"])


def _err(exc: eng.EngagementError | m.ManageError) -> HTTPException:
    return HTTPException(exc.status, {"code": exc.code, "message": exc.message})


def _commit(db, fn):
    try:
        out = fn()
        db.commit()
        return out
    except (eng.EngagementError, m.ManageError) as exc:
        db.rollback()
        raise _err(exc) from exc


def _own_booking(db, principal, booking_id: uuid.UUID) -> Booking:
    b = db.get(Booking, booking_id)
    if b is None or b.user_id != principal.user.id:
        raise HTTPException(404, {"code": "booking_not_found", "message": "Réservation introuvable."})
    return b


# ---------------------------------------------------------------- messagerie (client)


class MessageOut(BaseModel):
    id: uuid.UUID
    sender_kind: str
    body: str
    created_at: datetime
    mine: bool


class ThreadOut(BaseModel):
    can_write: bool
    closed_reason: str | None
    location_name: str
    messages: list[MessageOut]


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


def _thread(db, booking: Booking, me: uuid.UUID, side: str) -> ThreadOut:
    from datetime import UTC

    conv = eng.conversation_for(db, booking, create=False)
    try:
        eng._messageable(booking, datetime.now(UTC))
        can, reason = True, None
    except eng.EngagementError as exc:
        can, reason = False, exc.message
    eng.mark_read(conv, side)
    loc = db.get(Location, booking.location_id)
    return ThreadOut(can_write=can, closed_reason=reason, location_name=loc.name,
                     messages=[MessageOut(id=x.id, sender_kind=x.sender_kind, body=x.body, created_at=x.created_at,
                                          mine=x.sender_kind == side) for x in eng.messages(db, conv)])


@router.get("/bookings/{booking_id}/messages", response_model=ThreadOut)
def booking_messages(booking_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> ThreadOut:
    booking = _own_booking(db, principal, booking_id)
    out = _thread(db, booking, principal.user.id, "customer")
    db.commit()
    return out


@router.post("/bookings/{booking_id}/messages", response_model=MessageOut, status_code=201)
def send_booking_message(booking_id: uuid.UUID, body: MessageIn, principal: CurrentPrincipal, db: DbSession) -> MessageOut:
    booking = _own_booking(db, principal, booking_id)
    msg = _commit(db, lambda: eng.post_message(db, booking=booking, sender_kind="customer", user=principal.user, body=body.body))
    return MessageOut(id=msg.id, sender_kind=msg.sender_kind, body=msg.body, created_at=msg.created_at, mine=True)


@router.get("/me/messages/unread", response_model=dict)
def unread(principal: CurrentPrincipal, db: DbSession) -> dict:
    return {"count": eng.unread_for_customer(db, principal.user.id)}


# ---------------------------------------------------------------- messagerie (établissement)


class ConversationRow(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    customer_name: str
    offer_title: str
    starts_at: datetime
    last_message_at: datetime
    last_message: str
    unread: bool


@router.get("/partner/locations/{location_id}/conversations", response_model=list[ConversationRow])
def partner_conversations(location_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> list[ConversationRow]:
    try:
        loc = m.load_location(db, principal, location_id, m.STAFF)
    except m.ManageError as exc:
        raise _err(exc) from exc
    rows = db.execute(
        select(Conversation, Booking, User.display_name, OfferVersion.title)
        .join(Booking, Booking.id == Conversation.booking_id).join(User, User.id == Conversation.customer_id)
        .join(OfferVersion, OfferVersion.id == Booking.offer_version_id)
        .where(Conversation.location_id == loc.id).order_by(Conversation.last_message_at.desc()).limit(100)
    ).all()
    out = []
    for conv, booking, name, title in rows:
        last = db.scalar(select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at.desc()).limit(1))
        if last is None:
            continue
        unread = eng.partner_has_unread(db, conv)
        out.append(ConversationRow(id=conv.id, booking_id=booking.id, customer_name=eng.public_name(name), offer_title=title,
                                   starts_at=booking.starts_at, last_message_at=conv.last_message_at,
                                   last_message=last.body[:140], unread=unread))
    return out


def _partner_conv(db, principal, location_id: uuid.UUID, conversation_id: uuid.UUID) -> tuple[Conversation, Booking]:
    try:
        loc = m.load_location(db, principal, location_id, m.STAFF)
    except m.ManageError as exc:
        raise _err(exc) from exc
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.location_id != loc.id:
        raise HTTPException(404, {"code": "conversation_not_found", "message": "Conversation introuvable."})
    return conv, db.get(Booking, conv.booking_id)


@router.get("/partner/locations/{location_id}/conversations/{conversation_id}", response_model=ThreadOut)
def partner_thread(location_id: uuid.UUID, conversation_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> ThreadOut:
    _, booking = _partner_conv(db, principal, location_id, conversation_id)
    out = _thread(db, booking, principal.user.id, "partner")
    db.commit()
    return out


@router.post("/partner/locations/{location_id}/conversations/{conversation_id}/messages", response_model=MessageOut, status_code=201)
def partner_reply(location_id: uuid.UUID, conversation_id: uuid.UUID, body: MessageIn, principal: CurrentPrincipal,
                  db: DbSession) -> MessageOut:
    _, booking = _partner_conv(db, principal, location_id, conversation_id)
    msg = _commit(db, lambda: eng.post_message(db, booking=booking, sender_kind="partner", user=principal.user, body=body.body))
    return MessageOut(id=msg.id, sender_kind=msg.sender_kind, body=msg.body, created_at=msg.created_at, mine=True)


class AdminConversationRow(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    location_name: str
    customer_name: str
    offer_title: str
    last_message: str
    last_message_at: datetime
    unread_for_venue: bool


@router.get("/admin/conversations", response_model=list[AdminConversationRow], tags=["administration"])
def admin_conversations(principal: CurrentPrincipal, db: DbSession) -> list[AdminConversationRow]:
    """Même fil que l'application et le portail commerçant : l'administration voit les échanges en cours."""
    try:
        ops.require(principal, ops.STAFF)
    except ops.OpsError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc
    rows = db.execute(
        select(Conversation, Booking, User.display_name, OfferVersion.title, Location.name)
        .join(Booking, Booking.id == Conversation.booking_id)
        .join(User, User.id == Conversation.customer_id)
        .join(OfferVersion, OfferVersion.id == Booking.offer_version_id)
        .join(Location, Location.id == Conversation.location_id)
        .order_by(Conversation.last_message_at.desc()).limit(80)
    ).all()
    out = []
    for conv, booking, name, title, loc_name in rows:
        last = db.scalar(select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at.desc()).limit(1))
        if last is None:
            continue
        out.append(AdminConversationRow(
            id=conv.id, booking_id=booking.id, location_name=loc_name, customer_name=eng.public_name(name),
            offer_title=title, last_message=last.body[:180], last_message_at=conv.last_message_at,
            unread_for_venue=eng.partner_has_unread(db, conv)))
    return out


# ---------------------------------------------------------------- favoris


class FavoriteOut(BaseModel):
    location_id: uuid.UUID
    slug: str
    name: str
    kind_label: str
    district_label: str
    category_slug: str
    cover_image_key: str | None


@router.get("/me/favorites", response_model=list[FavoriteOut])
def favorites(principal: CurrentPrincipal, db: DbSession) -> list[FavoriteOut]:
    ids = eng.favorite_ids(db, principal.user.id)
    if not ids:
        return []
    rows = db.execute(select(Location, Category.slug).join(Subcategory, Subcategory.id == Location.subcategory_id)
                      .join(Category, Category.id == Subcategory.category_id)
                      .where(Location.id.in_(ids), Location.status == "published")).all()
    by_id = {loc.id: (loc, cat) for loc, cat in rows}
    return [FavoriteOut(location_id=loc.id, slug=loc.slug, name=loc.name, kind_label=loc.kind_label,
                        district_label=loc.district_label, category_slug=cat, cover_image_key=loc.cover_image_key)
            for i in ids if i in by_id for loc, cat in [by_id[i]]]


@router.put("/me/favorites/{location_id}", status_code=204)
def add_favorite(location_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> None:
    _commit(db, lambda: eng.set_favorite(db, user_id=principal.user.id, location_id=location_id, on=True))


@router.delete("/me/favorites/{location_id}", status_code=204)
def remove_favorite(location_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> None:
    _commit(db, lambda: eng.set_favorite(db, user_id=principal.user.id, location_id=location_id, on=False))


# ---------------------------------------------------------------- avis notés


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(None, max_length=1000)


class ReviewOut(BaseModel):
    id: uuid.UUID
    rating: int
    comment: str | None
    author: str
    created_at: datetime
    partner_reply: str | None
    status: str


class ReviewsOut(BaseModel):
    average: float | None
    count: int
    items: list[ReviewOut]


def _review_out(r: Review, author: str) -> ReviewOut:
    return ReviewOut(id=r.id, rating=r.rating, comment=r.comment, author=eng.public_name(author), created_at=r.created_at,
                     partner_reply=r.partner_reply, status=r.status)


@router.post("/bookings/{booking_id}/review", response_model=ReviewOut, status_code=201)
def review(booking_id: uuid.UUID, body: ReviewIn, principal: CurrentPrincipal, db: DbSession) -> ReviewOut:
    r = _commit(db, lambda: eng.create_review(db, user=principal.user, booking_id=booking_id, rating=body.rating,
                                              comment=body.comment))
    return _review_out(r, principal.user.display_name)


@router.get("/bookings/{booking_id}/review", response_model=ReviewOut | None)
def my_review(booking_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> ReviewOut | None:
    _own_booking(db, principal, booking_id)
    r = db.scalar(select(Review).where(Review.booking_id == booking_id))
    return _review_out(r, principal.user.display_name) if r else None


def _reviews(db, location_id: uuid.UUID, *, include_hidden: bool) -> ReviewsOut:
    avg, n = eng.rating_summary(db, location_id)
    stmt = select(Review, User.display_name).join(User, User.id == Review.user_id).where(Review.location_id == location_id)
    if not include_hidden:
        stmt = stmt.where(Review.status == "published")
    rows = db.execute(stmt.order_by(Review.created_at.desc()).limit(50)).all()
    return ReviewsOut(average=avg, count=n, items=[_review_out(r, name) for r, name in rows])


@router.get("/catalog/locations/{slug}/reviews", response_model=ReviewsOut)
def public_reviews(slug: str, db: DbSession) -> ReviewsOut:
    loc = db.scalar(select(Location).where(Location.slug == slug, Location.status == "published"))
    if loc is None:
        raise HTTPException(404, {"code": "location_not_found", "message": "Établissement introuvable."})
    return _reviews(db, loc.id, include_hidden=False)


@router.get("/partner/locations/{location_id}/reviews", response_model=ReviewsOut)
def partner_reviews(location_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> ReviewsOut:
    try:
        loc = m.load_location(db, principal, location_id, m.STAFF)
    except m.ManageError as exc:
        raise _err(exc) from exc
    return _reviews(db, loc.id, include_hidden=False)


class ReplyIn(BaseModel):
    reply: str = Field(min_length=2, max_length=1000)


@router.post("/partner/locations/{location_id}/reviews/{review_id}/reply", response_model=dict)
def partner_review_reply(location_id: uuid.UUID, review_id: uuid.UUID, body: ReplyIn, principal: CurrentPrincipal,
                         db: DbSession) -> dict:
    def run():
        loc = m.load_location(db, principal, location_id, m.OWNER)
        eng.reply_review(db, review_id=review_id, location_id=loc.id, reply=body.reply)
    _commit(db, run)
    return {"ok": True}


class HideIn(BaseModel):
    reason: str = Field(max_length=2000)


@router.get("/admin/reviews", response_model=list[dict])
def admin_reviews(principal: CurrentPrincipal, db: DbSession) -> list[dict]:
    try:
        ops.require(principal, ops.STAFF)
    except ops.OpsError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc
    rows = db.execute(select(Review, Location.name, User.display_name).join(Location, Location.id == Review.location_id)
                      .join(User, User.id == Review.user_id).order_by(Review.created_at.desc()).limit(100)).all()
    return [{**_review_out(r, name).model_dump(mode="json"), "location_name": ln} for r, ln, name in rows]


@router.post("/admin/reviews/{review_id}/hide", response_model=dict)
def admin_hide_review(review_id: uuid.UUID, body: HideIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    try:
        ops.require(principal, ops.STAFF)
        eng.hide_review(db, review_id=review_id, reason=body.reason, by=principal.user.id)
        db.commit()
    except (eng.EngagementError, ops.OpsError) as exc:
        db.rollback()
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc
    return {"ok": True}


# ---------------------------------------------------------------- appareils (notifications)


class DeviceIn(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    platform: Literal["android", "ios", "web"]


@router.post("/me/devices", status_code=204)
def register_device(body: DeviceIn, principal: CurrentPrincipal, db: DbSession) -> None:
    _commit(db, lambda: eng.register_device(db, user_id=principal.user.id, token=body.token, platform=body.platform))


@router.post("/me/devices/remove", status_code=204)
def unregister_device(body: DeviceIn, principal: CurrentPrincipal, db: DbSession) -> None:
    _commit(db, lambda: eng.unregister_device(db, user_id=principal.user.id, token=body.token))
