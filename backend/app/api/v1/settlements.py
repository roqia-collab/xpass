"""Règlements commerçant (maquette 22) : lecture seule, montants en unités mineures avec devise."""
import csv
import io
import uuid
from datetime import date, datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentPrincipal, DbSession, forbidden
from app.core.config import get_settings
from app.modules.catalog.models import Location, Market, Merchant, OfferVersion
from app.modules.booking.models import Booking
from app.modules.redemption.models import PartnerPayable
from app.modules.settlement import connect, service
from app.modules.settlement.models import PartnerAdjustment, PartnerPayout, SettlementTerms

router = APIRouter(tags=["commerçant"])


class TermsOut(BaseModel):
    gross_minor_per_credit: int
    commission_bps: int
    currency: str
    is_demo: bool


class OpenPeriodOut(BaseModel):
    gross_minor: int
    commission_minor: int
    adjustments_minor: int
    net_minor: int
    visits: int
    pending_valuation: int


class PayoutOut(BaseModel):
    id: uuid.UUID
    period_start: date
    period_end: date
    currency: str
    gross_minor: int
    commission_minor: int
    adjustments_minor: int
    net_minor: int
    visits: int
    status: str
    paid_at: datetime | None
    confirmed_minor: int | None


class SettlementsOut(BaseModel):
    currency: str
    psp_status: str
    payouts_enabled: bool
    has_payout_account: bool
    psp_configured: bool
    # Établissement de démonstration : compte de versement fictif (bac à sable uniquement).
    is_demo: bool
    terms: TermsOut | None
    to_receive_minor: int
    open_period: OpenPeriodOut
    payouts: list[PayoutOut]


class PayoutLineOut(BaseModel):
    kind: str
    occurred_at: datetime
    offer_title: str
    location_name: str
    credits: int
    gross_minor: int
    commission_minor: int


class AdjustmentOut(BaseModel):
    reference: str
    label: str
    amount_minor: int


class PayoutDetailOut(PayoutOut):
    lines: list[PayoutLineOut]
    adjustments: list[AdjustmentOut]


def _merchant(db, principal) -> Merchant:
    ids = principal.scope_ids("merchant", ("merchant_owner",))
    if not ids:
        raise forbidden("Les règlements sont réservés au responsable de l'établissement.")
    return db.get(Merchant, ids[0])


def _payout_out(p: PartnerPayout) -> PayoutOut:
    return PayoutOut.model_validate(p, from_attributes=True)


@router.get("/partner/settlements", response_model=SettlementsOut)
def settlements(principal: CurrentPrincipal, db: DbSession) -> SettlementsOut:
    merchant = _merchant(db, principal)
    market = db.get(Market, merchant.market_id)
    terms = db.scalar(select(SettlementTerms).where(SettlementTerms.market_id == market.id,
                                                    SettlementTerms.effective_from <= datetime.now().astimezone())
                      .order_by(SettlementTerms.effective_from.desc()).limit(1))
    payouts = db.scalars(select(PartnerPayout).where(PartnerPayout.merchant_id == merchant.id)
                         .order_by(PartnerPayout.period_start.desc()).limit(26)).all()
    return SettlementsOut(
        currency=market.currency,
        psp_status=merchant.psp_status,
        payouts_enabled=merchant.psp_status == "verified" and bool(merchant.psp_account_id),
        has_payout_account=bool(merchant.psp_account_id),
        psp_configured=bool(get_settings().psp_provider),
        is_demo=merchant.is_demo,
        terms=TermsOut.model_validate(terms, from_attributes=True) if terms else None,
        to_receive_minor=sum(p.net_minor for p in payouts if p.status in ("pending", "in_transit")),
        open_period=OpenPeriodOut(**service.open_period_summary(db, merchant.id)),
        payouts=[_payout_out(p) for p in payouts],
    )


def _detail(db, merchant: Merchant, payout_id: uuid.UUID) -> tuple[PartnerPayout, list, list]:
    payout = db.get(PartnerPayout, payout_id)
    if payout is None or payout.merchant_id != merchant.id:
        raise HTTPException(404, {"code": "payout_not_found", "message": "Règlement introuvable."})
    lines = db.execute(
        select(PartnerPayable, OfferVersion.title, Location.name)
        .join(Booking, Booking.id == PartnerPayable.booking_id)
        .join(OfferVersion, OfferVersion.id == Booking.offer_version_id)
        .join(Location, Location.id == PartnerPayable.location_id)
        .where(PartnerPayable.payout_id == payout.id)
        .order_by(PartnerPayable.occurred_at)
    ).all()
    adjustments = db.scalars(select(PartnerAdjustment).where(PartnerAdjustment.payout_id == payout.id)).all()
    return payout, lines, adjustments


@router.get("/partner/settlements/{payout_id}", response_model=PayoutDetailOut)
def payout_detail(payout_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> PayoutDetailOut:
    payout, lines, adjustments = _detail(db, _merchant(db, principal), payout_id)
    return PayoutDetailOut(
        **_payout_out(payout).model_dump(),
        lines=[PayoutLineOut(kind=p.kind, occurred_at=p.occurred_at, offer_title=t, location_name=n, credits=p.credits,
                             gross_minor=p.amount_minor, commission_minor=p.commission_minor) for p, t, n in lines],
        adjustments=[AdjustmentOut(reference=a.reference, label=a.label, amount_minor=a.amount_minor) for a in adjustments],
    )


def _money(minor: int) -> str:
    sign = "-" if minor < 0 else ""
    return f"{sign}{abs(minor) // 100},{abs(minor) % 100:02d}"


@router.get("/partner/settlements/{payout_id}/statement.csv", response_class=Response)
def statement(payout_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> Response:
    payout, lines, adjustments = _detail(db, _merchant(db, principal), payout_id)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Période", f"{payout.period_start} au {payout.period_end}", "Devise", payout.currency])
    w.writerow(["Date", "Type", "Prestation", "Établissement", "Crédits", "Brut", "Commission"])
    for p, title, loc in lines:
        w.writerow([p.occurred_at.date().isoformat(), {"redemption": "Visite", "late_cancellation": "Annulation tardive", "no_show": "Absence"}.get(p.kind, p.kind),
                    title, loc, p.credits, _money(p.amount_minor), _money(-p.commission_minor)])
    for a in adjustments:
        w.writerow(["", "Ajustement", f"{a.reference} {a.label}", "", "", _money(a.amount_minor), ""])
    w.writerow([])
    for label, value in [("Brut", payout.gross_minor), ("Commission", -payout.commission_minor),
                         ("Ajustements", payout.adjustments_minor), ("Net", payout.net_minor)]:
        w.writerow([label, _money(value)])
    # BOM pour une ouverture correcte des accents dans un tableur.
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="releve-{payout.period_start}.csv"'})


# ---------------------------------------------------------------- compte de versement (Stripe Connect)


class LinkOut(BaseModel):
    url: str


class PayoutAccountOut(BaseModel):
    psp_status: str
    payouts_enabled: bool


def _connect(db, fn):
    try:
        result = fn()
        db.commit()
        return result
    except connect.ConnectError as exc:
        db.rollback()
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc


@router.post("/partner/payout-account/onboarding", response_model=LinkOut)
def payout_onboarding(principal: CurrentPrincipal, db: DbSession) -> LinkOut:
    """Lien vers la page du prestataire (identité, IBAN). Responsable uniquement."""
    merchant = _merchant(db, principal)
    return LinkOut(url=_connect(db, lambda: connect.start_onboarding(db, merchant_id=merchant.id, user=principal.user)))


@router.post("/partner/payout-account/refresh", response_model=PayoutAccountOut)
def payout_refresh(principal: CurrentPrincipal, db: DbSession) -> PayoutAccountOut:
    merchant = _merchant(db, principal)
    status = _connect(db, lambda: connect.refresh_status(db, merchant_id=merchant.id))
    return PayoutAccountOut(psp_status=status, payouts_enabled=status == "verified" and bool(merchant.psp_account_id))


@router.post("/partner/payout-account/dashboard", response_model=LinkOut)
def payout_dashboard(principal: CurrentPrincipal, db: DbSession) -> LinkOut:
    merchant = _merchant(db, principal)
    return LinkOut(url=_connect(db, lambda: connect.dashboard_url(db, merchant_id=merchant.id)))
