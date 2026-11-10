"""Scan et consommation côté partenaire (maquettes 19 et 20)."""
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentPrincipal, DbSession, forbidden
from app.modules.booking.models import Booking
from app.modules.booking.service import BookingError
from app.modules.catalog.models import Location, Merchant, OfferVersion, Resource
from app.modules.identity.models import User
from app.modules.platform.service import IdempotencyMismatch, run_idempotent
from app.modules.redemption import service
from app.modules.redemption.models import Redemption

router = APIRouter(tags=["commerçant"])


class ScanIn(BaseModel):
    location_id: uuid.UUID
    qr: str | None = Field(None, max_length=200)
    code: str | None = Field(None, max_length=20)

    @model_validator(mode="after")
    def _one_of(self):
        if bool(self.qr) == bool(self.code):
            raise ValueError("Fournir soit le contenu du QR, soit le code manuel.")
        return self


class ScanPreviewOut(BaseModel):
    booking_id: uuid.UUID
    status: str
    customer_name: str
    location_name: str
    kind_label: str
    district_label: str
    cover_image_key: str | None
    offer_title: str
    resource_name: str | None
    local_start: str
    duration_min: int
    party_size: int
    total_credits: int
    # Le jeton reste réservé à cet opérateur jusqu'à cette heure pour confirmer.
    confirm_before: datetime


class RedemptionOut(BaseModel):
    booking_id: uuid.UUID
    receipt_reference: str
    credits: int
    redeemed_at: datetime
    customer_name: str
    offer_title: str


class VisitOut(BaseModel):
    booking_id: uuid.UUID
    customer_name: str
    offer_title: str
    resource_name: str | None
    credits: int
    method: str
    local_time: str


def _check_location(db, principal, location_id: uuid.UUID) -> Location:
    merchant_ids = principal.scope_ids("merchant", ("merchant_owner", "merchant_staff"))
    location = db.scalar(
        select(Location).options(selectinload(Location.merchant).selectinload(Merchant.market)).where(
            Location.id == location_id
        )
    )
    if location is None or location.merchant_id not in merchant_ids:
        raise forbidden("Vous n'avez pas accès à cet établissement.")
    return location


def _http(exc: BookingError) -> HTTPException:
    return HTTPException(exc.status, {"code": exc.code, "message": exc.message})


@router.post("/partner/scan/preview", response_model=ScanPreviewOut)
def scan_preview(body: ScanIn, principal: CurrentPrincipal, db: DbSession) -> ScanPreviewOut:
    """Aperçu de la réservation : AUCUNE consommation, aucun mouvement de crédits."""
    location = _check_location(db, principal, body.location_id)
    try:
        booking, token = service.preview(
            db, operator_id=principal.user.id, location_id=location.id, qr=body.qr, code=body.code
        )
        version = db.get(OfferVersion, booking.offer_version_id)
        resource = db.get(Resource, booking.resource_id) if booking.resource_id else None
        customer = db.get(User, booking.user_id)
        db.commit()
    except BookingError as exc:
        db.rollback()
        raise _http(exc) from exc
    tz = ZoneInfo(location.merchant.market.timezone)
    return ScanPreviewOut(
        booking_id=booking.id,
        status=booking.status,
        customer_name=customer.display_name,
        location_name=location.name,
        kind_label=location.kind_label,
        district_label=location.district_label,
        cover_image_key=location.cover_image_key,
        offer_title=version.title,
        resource_name=resource.name if resource else None,
        local_start=booking.starts_at.astimezone(tz).replace(tzinfo=None).isoformat(timespec="minutes"),
        duration_min=version.duration_min,
        party_size=booking.party_size,
        total_credits=booking.total_credits,
        confirm_before=token.scanned_at + service.SCAN_HOLD,
    )


@router.post("/partner/redemptions", response_model=RedemptionOut, status_code=201)
def redeem(
    body: ScanIn,
    principal: CurrentPrincipal,
    db: DbSession,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
):
    """Confirme la consommation : crédits capturés, reçu, dette partenaire et outbox dans une transaction."""
    location = _check_location(db, principal, body.location_id)

    def action():
        result = service.redeem(db, operator_id=principal.user.id, location_id=location.id, qr=body.qr, code=body.code)
        customer = db.get(User, result.booking.user_id)
        version = db.get(OfferVersion, result.booking.offer_version_id)
        out = RedemptionOut(
            booking_id=result.booking.id,
            receipt_reference=result.receipt.reference,
            credits=result.redemption.credits,
            redeemed_at=result.booking.redeemed_at,
            customer_name=customer.display_name,
            offer_title=version.title,
        )
        return 201, out.model_dump(mode="json")

    try:
        result = run_idempotent(
            db, user_id=principal.user.id, scope="partner.redeem", key=idempotency_key,
            body=body.model_dump(mode="json"), action=action,
        )
    except IdempotencyMismatch as exc:
        db.rollback()
        raise HTTPException(422, {"code": "idempotency_mismatch", "message": "Clé déjà utilisée."}) from exc
    except BookingError as exc:
        db.rollback()
        raise _http(exc) from exc
    headers = {"Idempotent-Replayed": "true"} if result.replayed else {}
    return JSONResponse(result.body, status_code=result.status, headers=headers)


@router.get("/partner/redemptions", response_model=list[VisitOut])
def visits(
    principal: CurrentPrincipal,
    db: DbSession,
    location_id: uuid.UUID,
    day: Annotated[date | None, Query(alias="date")] = None,
) -> list[VisitOut]:
    location = _check_location(db, principal, location_id)
    tz = ZoneInfo(location.merchant.market.timezone)
    day = day or datetime.now(tz).date()
    start = datetime.combine(day, time.min, tz)
    rows = db.execute(
        select(Redemption, Booking, OfferVersion.title, Resource.name, User.display_name)
        .join(Booking, Booking.id == Redemption.booking_id)
        .join(OfferVersion, OfferVersion.id == Booking.offer_version_id)
        .join(User, User.id == Booking.user_id)
        .outerjoin(Resource, Resource.id == Booking.resource_id)
        .where(
            Redemption.location_id == location.id,
            Redemption.created_at >= start.astimezone(UTC),
            Redemption.created_at < (start + timedelta(days=1)).astimezone(UTC),
        )
        .order_by(Redemption.created_at)
    ).all()
    return [
        VisitOut(
            booking_id=b.id, customer_name=customer, offer_title=title, resource_name=res, credits=r.credits,
            method=r.method, local_time=r.created_at.astimezone(tz).strftime("%H:%M"),
        )
        for r, b, title, res, customer in rows
    ]
