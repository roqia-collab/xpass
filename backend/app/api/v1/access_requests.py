"""Formulaire public et mots de passe remis par l'admin ou le RH."""
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import CurrentPrincipal, DbSession
from app.modules.catalog.launch import LaunchError
from app.modules.catalog.onboarding import OnboardingError
from app.modules.identity import requests as requests_service
from app.modules.ops.service import OpsError, require

router = APIRouter(tags=["demandes"])


class SubmitIn(BaseModel):
    kind: str = Field(pattern="^(rh|merchant)$")
    gmail: str = Field(max_length=254)
    full_name: str = Field(max_length=120)
    place_name: str = Field(max_length=160)
    city: str = Field(max_length=80)
    message: str = Field("", max_length=1000)
    website: str = Field("", max_length=200)


class PasswordIn(BaseModel):
    password: str = Field(min_length=8, max_length=72)


class StaffPasswordIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=72)


def _http(exc: OpsError | LaunchError | OnboardingError) -> HTTPException:
    return HTTPException(exc.status, {"code": exc.code, "message": exc.message})


def _run(db, fn):
    try:
        result = fn()
        db.commit()
        return result
    except (OpsError, LaunchError, OnboardingError) as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/access-requests", status_code=201)
def submit_access_request(body: SubmitIn, db: DbSession) -> dict:
    if body.website.strip():
        return {"ok": True}
    try:
        row = requests_service.submit_request(
            db, kind=body.kind, gmail=body.gmail, full_name=body.full_name,
            place_name=body.place_name, city=body.city, message=body.message,
        )
        db.commit()
    except OpsError as exc:
        db.rollback()
        raise _http(exc) from exc
    requests_service.notify_admin(db, row)
    return {"ok": True}


@router.get("/admin/access-requests")
def admin_access_requests(principal: CurrentPrincipal, db: DbSession) -> list[dict]:
    try:
        require(principal, ("platform_admin", "platform_operator"))
    except OpsError as exc:
        raise _http(exc) from exc
    return [
        {
            "id": str(row.id),
            "kind": row.kind,
            "gmail": row.gmail,
            "full_name": row.full_name,
            "place_name": row.place_name,
            "city": row.city,
            "message": row.message,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
        }
        for row in requests_service.list_requests(db)
    ]


@router.post("/admin/access-requests/{request_id}/accept")
def accept_access_request(request_id: uuid.UUID, body: PasswordIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    try:
        require(principal, ("platform_admin",))
    except OpsError as exc:
        raise _http(exc) from exc
    _run(db, lambda: requests_service.accept_request(
        db, request_id, password=body.password, actor_id=principal.user.id, actor_name=principal.user.display_name,
    ))
    return {"ok": True}


@router.post("/admin/access-requests/{request_id}/refuse")
def refuse_access_request(request_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> dict:
    try:
        require(principal, ("platform_admin",))
    except OpsError as exc:
        raise _http(exc) from exc
    _run(db, lambda: requests_service.refuse_request(db, request_id, actor_id=principal.user.id))
    return {"ok": True}


@router.post("/admin/login-password")
def admin_set_password(body: StaffPasswordIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    try:
        require(principal, ("platform_admin",))
    except OpsError as exc:
        raise _http(exc) from exc
    _run(db, lambda: requests_service.set_password_for_member(db, email=body.email, password=body.password, merchant_org_ids=None))
    return {"ok": True}


@router.post("/company/login-password")
def company_set_password(body: StaffPasswordIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    org_ids = principal.scope_ids("organization", ("hr_admin",))
    if not org_ids:
        raise HTTPException(403, {"code": "forbidden", "message": "Seul un administrateur RH peut donner ce mot de passe."})
    _run(db, lambda: requests_service.set_password_for_member(db, email=body.email, password=body.password, merchant_org_ids=org_ids))
    return {"ok": True}
