"""Compte client (écran 16) et file d'assistance de l'administration."""
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentPrincipal, DbSession, forbidden
from app.modules.identity import account
from app.modules.identity.models import User
from app.modules.ops.models import SupportRequest

router = APIRouter(tags=["compte"])


def _commit(db, fn):
    try:
        result = fn()
        db.commit()
        return result
    except account.AccountError as exc:
        db.rollback()
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc


class ProfileIn(BaseModel):
    display_name: str | None = Field(None, max_length=120)
    locale: Literal["fr", "en", "ar"] | None = None
    notify_email: bool | None = None


class DeleteIn(BaseModel):
    # Confirmation explicite saisie par l'utilisateur.
    confirm: Literal["SUPPRIMER"]


class SupportIn(BaseModel):
    category: Literal["booking", "credits", "account", "partner", "other"]
    subject: str = Field(max_length=160)
    message: str = Field(max_length=4000)
    booking_id: uuid.UUID | None = None


class SupportOut(BaseModel):
    id: uuid.UUID
    reference: str
    category: str
    subject: str
    message: str
    status: str
    reply: str | None
    replied_at: datetime | None
    created_at: datetime


class AdminSupportOut(SupportOut):
    customer_name: str
    customer_email: str


class ReplyIn(BaseModel):
    reply: str = Field(max_length=4000)
    close: bool = False


class NotificationOut(BaseModel):
    id: str
    kind: str
    title: str
    body: str
    route: str
    created_at: datetime


@router.patch("/me", response_model=dict)
def update_me(body: ProfileIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    u = _commit(db, lambda: account.update_profile(db, principal.user, **body.model_dump()))
    return {"display_name": u.display_name, "locale": u.locale, "notify_email": u.notify_email}


@router.get("/me/notifications", response_model=list[NotificationOut])
def my_notifications(principal: CurrentPrincipal, db: DbSession) -> list[NotificationOut]:
    return [NotificationOut(**n) for n in account.list_notifications(db, principal.user)]


@router.get("/me/export")
def export_me(principal: CurrentPrincipal, db: DbSession) -> JSONResponse:
    data = account.export_data(db, principal.user)
    return JSONResponse(data, headers={"Content-Disposition": 'attachment; filename="mes-donnees-xpass.json"',
                                       "Cache-Control": "no-store"})


@router.post("/me/delete", response_model=dict)
def delete_me(body: DeleteIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _commit(db, lambda: account.delete_account(db, principal.user))
    return {"deleted": True}


@router.get("/me/support", response_model=list[SupportOut])
def my_support(principal: CurrentPrincipal, db: DbSession) -> list[SupportOut]:
    rows = db.scalars(select(SupportRequest).where(SupportRequest.user_id == principal.user.id)
                      .order_by(SupportRequest.created_at.desc()).limit(50))
    return [SupportOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/me/support", status_code=201, response_model=SupportOut)
def open_support(body: SupportIn, principal: CurrentPrincipal, db: DbSession) -> SupportOut:
    r = _commit(db, lambda: account.open_support(db, principal.user, **body.model_dump()))
    return SupportOut.model_validate(r, from_attributes=True)


@router.get("/admin/support", response_model=list[AdminSupportOut], tags=["administration"])
def admin_support(principal: CurrentPrincipal, db: DbSession,
                  status: Literal["open", "answered", "closed", "all"] = "open") -> list[AdminSupportOut]:
    if not principal.has_platform_role("platform_admin", "platform_operator"):
        raise forbidden()
    stmt = (select(SupportRequest, User.display_name, User.email).join(User, User.id == SupportRequest.user_id)
            .order_by(SupportRequest.created_at).limit(200))
    if status != "all":
        stmt = stmt.where(SupportRequest.status == status)
    return [AdminSupportOut(**SupportOut.model_validate(r, from_attributes=True).model_dump(), customer_name=n,
                            customer_email=e) for r, n, e in db.execute(stmt).all()]


@router.post("/admin/support/{request_id}/reply", response_model=dict, tags=["administration"])
def admin_reply(request_id: uuid.UUID, body: ReplyIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    if not principal.has_platform_role("platform_admin", "platform_operator"):
        raise forbidden()
    r = _commit(db, lambda: account.answer_support(db, request_id=request_id, reply=body.reply, close=body.close,
                                                   by=principal.user.id))
    return {"status": r.status}

