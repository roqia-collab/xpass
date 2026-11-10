"""Administration XPASS (lot 7) : opérations, partenaires, modération, litiges, rapprochement, audit."""
import uuid
from datetime import datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.api.deps import CurrentPrincipal, DbSession
from app.core.config import get_settings
from app.modules.booking.models import Booking
from app.modules.booking.service import funding_by_source
from app.modules.catalog.models import Location, Market, Merchant, Offer, OfferVersion
from app.modules.employer.models import EmployerInvoice
from app.modules.identity.models import Membership, Organization, User
from app.modules.ops import service as ops
from app.modules.ops.models import OPEN_DISPUTES, AuditEvent, Dispute
from app.modules.payments.models import PaymentWebhookEvent
from app.modules.payments.service import MAX_ATTEMPTS
from app.modules.redemption.models import PartnerPayable
from app.modules.settlement.models import PartnerPayout

router = APIRouter(prefix="/admin", tags=["administration"])


def _http(exc: ops.OpsError) -> HTTPException:
    return HTTPException(exc.status, {"code": exc.code, "message": exc.message})


def _guard(principal, roles) -> None:
    try:
        ops.require(principal, roles)
    except ops.OpsError as exc:
        raise _http(exc) from exc


def _commit(db, fn):
    try:
        result = fn()
        db.commit()
        return result
    except ops.OpsError as exc:
        db.rollback()
        raise _http(exc) from exc


class ReasonIn(BaseModel):
    reason: str = Field(max_length=2000)


class AuditOut(BaseModel):
    created_at: datetime
    actor_kind: str
    actor_name: str | None
    action: str
    object_type: str
    object_id: uuid.UUID
    object_label: str
    reason: str | None
    details: dict


def _audit_rows(db, stmt) -> list[AuditOut]:
    rows = db.execute(stmt.add_columns(User.display_name).outerjoin(User, User.id == AuditEvent.actor_user_id)).all()
    return [AuditOut(created_at=a.created_at, actor_kind=a.actor_kind, actor_name=name, action=a.action,
                     object_type=a.object_type, object_id=a.object_id, object_label=a.object_label, reason=a.reason,
                     details=a.details or {}) for a, name in rows]


# ---------------------------------------------------------------- vue d'ensemble (maquette 26)


class QueueItem(BaseModel):
    id: uuid.UUID
    title: str
    subtitle: str
    status: str
    at: datetime
    image_key: str | None = None  # photo de l'établissement (vignette des files)


class OverviewOut(BaseModel):
    merchants_to_review: int
    open_disputes: int
    reconciliation_issues: int
    merchants: list[QueueItem]
    disputes: list[QueueItem]
    payouts: dict[str, int]
    audit: list[AuditOut]
    is_admin: bool
    demo_locations: dict[str, int]  # lieux de démonstration par statut (published / hidden / draft)


@router.get("/overview", response_model=OverviewOut)
def overview(principal: CurrentPrincipal, db: DbSession) -> OverviewOut:
    _guard(principal, ops.STAFF)
    review = ("pending_review", "documents_missing")
    merchants = db.scalars(select(Merchant).where(Merchant.commercial_status.in_(review))
                           .order_by(Merchant.created_at).limit(5)).all()
    covers: dict[uuid.UUID, str] = {}
    for merchant_id, key in db.execute(
        select(Location.merchant_id, Location.cover_image_key)
        .where(Location.merchant_id.in_([m.id for m in merchants]), Location.cover_image_key.is_not(None))
        .order_by(Location.created_at)
    ).all():
        covers.setdefault(merchant_id, key)
    disputes = db.execute(
        select(Dispute, Location.name, Location.cover_image_key).join(Booking, Booking.id == Dispute.booking_id)
        .join(Location, Location.id == Booking.location_id)
        .where(Dispute.status.in_(OPEN_DISPUTES)).order_by(Dispute.created_at).limit(5)
    ).all()
    recon = _reconciliation_counts(db)
    payouts = dict(db.execute(select(PartnerPayout.status, func.count()).group_by(PartnerPayout.status)).all())
    return OverviewOut(
        merchants_to_review=db.scalar(select(func.count()).select_from(Merchant).where(Merchant.commercial_status.in_(review))),
        open_disputes=db.scalar(select(func.count()).select_from(Dispute).where(Dispute.status.in_(OPEN_DISPUTES))),
        reconciliation_issues=sum(recon.values()),
        merchants=[QueueItem(id=m.id, title=m.display_name, subtitle=m.city_label, status=m.commercial_status,
                             at=m.created_at, image_key=covers.get(m.id)) for m in merchants],
        disputes=[QueueItem(id=d.id, title=f"{d.reference} · {name}", subtitle=d.reason[:80], status=d.status,
                            at=d.created_at, image_key=cover) for d, name, cover in disputes],
        payouts={k: int(v) for k, v in payouts.items()},
        audit=_audit_rows(db, select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(8)),
        is_admin=principal.has_platform_role(*ops.ADMIN),
        demo_locations={k: int(v) for k, v in db.execute(select(Location.status, func.count())
                        .where(Location.is_demo.is_(True)).group_by(Location.status)).all()},
    )


# ---------------------------------------------------------------- partenaires (maquette 27)


class CheckOut(BaseModel):
    label: str
    detail: str
    ok: bool


class LocationAdminOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: str
    address: str
    kind_label: str
    cover_image_key: str | None
    review_url: str | None
    published_offers: int


class MerchantDetailOut(BaseModel):
    id: uuid.UUID
    display_name: str
    legal_name: str
    city_label: str
    market_code: str
    commercial_status: str
    psp_status: str
    psp_account: bool
    is_demo: bool
    created_at: datetime
    siret: str | None
    contact_phone: str | None
    checks: list[CheckOut]
    locations: list[LocationAdminOut]
    sandbox: bool
    audit: list[AuditOut]


class DecisionIn(ReasonIn):
    decision: Literal["approve", "request_documents", "suspend", "reopen"]


@router.get("/merchants/{merchant_id}", response_model=MerchantDetailOut)
def merchant_detail(merchant_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> MerchantDetailOut:
    _guard(principal, ops.STAFF)
    m = db.get(Merchant, merchant_id)
    if m is None:
        raise HTTPException(404, {"code": "merchant_not_found", "message": "Partenaire introuvable."})
    market = db.get(Market, m.market_id)
    locs = db.execute(
        select(Location, func.count(Offer.id).filter(Offer.is_active.is_(True)))
        .outerjoin(Offer, Offer.location_id == Location.id).where(Location.merchant_id == m.id)
        .group_by(Location.id).order_by(Location.name)
    ).all()
    owners = db.scalar(select(func.count()).select_from(User).where(User.memberships.any(scope_id=m.id, role="merchant_owner")))
    locations = [LocationAdminOut(id=loc.id, name=loc.name, slug=loc.slug, status=loc.status,
                                  address=f"{loc.address_line}, {loc.postal_code}", kind_label=loc.kind_label,
                                  cover_image_key=loc.cover_image_key, review_url=loc.review_url, published_offers=n)
                 for loc, n in locs]
    # Contrôles calculés à partir des données réelles (aucun document téléversé à ce stade).
    check = m.company_check or {}
    if check.get("status") == "verified":
        company = CheckOut(label="Entreprise (annuaire SIRENE)", ok=True,
                           detail=f"SIRET {m.siret} · {check.get('legal_name')} · établissement actif")
    elif check.get("status") == "unavailable":
        company = CheckOut(label="Entreprise (annuaire SIRENE)", ok=False,
                           detail=f"SIRET {m.siret} : annuaire indisponible à l'inscription, à vérifier à la main")
    else:
        company = CheckOut(label="Entreprise (annuaire SIRENE)", ok=False, detail="SIRET non renseigné")
    geo = db.execute(select(Location.geocode_label, Location.geocode_score).where(Location.merchant_id == m.id)).all()
    address = CheckOut(label="Adresse (Base Adresse Nationale)", ok=bool(geo) and all(s and s >= 0.7 for _, s in geo),
                       detail=" · ".join(f"{label} (confiance {round((s or 0) * 100)} %)" for label, s in geo if label)
                       or "Adresse non géocodée")
    checks = [
        company,
        address,
        CheckOut(label="Responsable identifié", detail="Compte responsable rattaché au partenaire", ok=bool(owners)),
        CheckOut(label="Coordonnées de l'établissement", detail="Au moins un établissement avec adresse", ok=bool(locations)),
        CheckOut(label="Prestations proposées", detail="Au moins une prestation publiée",
                 ok=any(x.published_offers for x in locations)),
        CheckOut(label="Lien Google Avis", detail="Renseigné par le partenaire", ok=any(x.review_url for x in locations)),
        CheckOut(label="Photos de l'établissement", detail="Photo principale présente",
                 ok=all(x.cover_image_key for x in locations) and bool(locations)),
        CheckOut(label="Documents de l'entreprise", detail="Téléversement des justificatifs non disponible (à venir)", ok=False),
    ]
    return MerchantDetailOut(
        id=m.id, display_name=m.display_name, legal_name=m.legal_name, city_label=m.city_label, market_code=market.code,
        commercial_status=m.commercial_status, psp_status=m.psp_status, psp_account=bool(m.psp_account_id),
        is_demo=m.is_demo, created_at=m.created_at, siret=m.siret, contact_phone=m.contact_phone,
        checks=checks, locations=locations,
        sandbox=get_settings().psp_provider == "sandbox",
        audit=_audit_rows(db, select(AuditEvent).where(
            or_(AuditEvent.object_id == m.id, AuditEvent.object_id.in_([x.id for x in locations])))
            .order_by(AuditEvent.created_at.desc()).limit(30)),
    )


@router.post("/merchants/{merchant_id}/decision", response_model=dict)
def merchant_decision(merchant_id: uuid.UUID, body: DecisionIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _guard(principal, ops.ADMIN)
    m = _commit(db, lambda: ops.decide_merchant(db, merchant_id=merchant_id, decision=body.decision,
                                                reason=body.reason, by=principal.user.id))
    return {"commercial_status": m.commercial_status}


@router.post("/merchants/{merchant_id}/psp-sandbox-verify", response_model=dict)
def merchant_psp_sandbox(merchant_id: uuid.UUID, body: ReasonIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _guard(principal, ops.ADMIN)
    m = _commit(db, lambda: ops.sandbox_psp_verify(db, merchant_id=merchant_id, reason=body.reason, by=principal.user.id))
    return {"psp_status": m.psp_status}


# ---------------------------------------------------------------- modération


class ModerationIn(ReasonIn):
    publish: bool


class ModerationRow(BaseModel):
    id: uuid.UUID
    name: str
    merchant_name: str
    commercial_status: str
    status: str
    published_offers: int
    updated_at: datetime


@router.get("/locations", response_model=list[ModerationRow])
def locations(principal: CurrentPrincipal, db: DbSession, status: str | None = None) -> list[ModerationRow]:
    _guard(principal, ops.STAFF)
    stmt = (select(Location, Merchant, func.count(Offer.id).filter(Offer.is_active.is_(True)))
            .join(Merchant, Merchant.id == Location.merchant_id).outerjoin(Offer, Offer.location_id == Location.id)
            .group_by(Location.id, Merchant.id).order_by(Location.updated_at.desc()).limit(200))
    if status:
        stmt = stmt.where(Location.status == status)
    return [ModerationRow(id=loc.id, name=loc.name, merchant_name=m.display_name, commercial_status=m.commercial_status,
                          status=loc.status, published_offers=n, updated_at=loc.updated_at)
            for loc, m, n in db.execute(stmt).all()]


@router.post("/locations/{location_id}/moderation", response_model=dict)
def moderate(location_id: uuid.UUID, body: ModerationIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _guard(principal, ops.STAFF)
    loc = _commit(db, lambda: ops.moderate_location(db, location_id=location_id, publish=body.publish,
                                                    reason=body.reason, by=principal.user.id))
    return {"status": loc.status}


# ---------------------------------------------------------------- litiges (maquette 28)


class DisputeRow(BaseModel):
    id: uuid.UUID
    reference: str
    status: str
    location_name: str
    customer_name: str
    created_at: datetime
    reason: str


class DisputeDetailOut(BaseModel):
    id: uuid.UUID
    reference: str
    status: str
    reason: str
    operator_notes: str | None
    created_at: datetime
    updated_at: datetime
    resolution_reason: str | None
    credits_restored: int | None
    partner_adjustment_minor: int | None
    customer_name: str
    location_name: str
    location_kind: str
    location_address: str
    cover_image_key: str | None
    merchant_id: uuid.UUID
    offer_title: str
    booking_status: str
    local_start: str
    party_size: int
    total_credits: int
    funding: dict[str, int]
    payable_gross_minor: int | None
    payable_net_minor: int | None
    currency: str | None
    payout_status: str | None
    payout_paid_at: datetime | None
    timeline: list[AuditOut]
    redeemed_at: datetime | None


class DisputeUpdateIn(ReasonIn):
    status: Literal["open", "in_review", "waiting_customer"]
    notes: str | None = Field(None, max_length=4000)


class RefundIn(ReasonIn):
    partner_adjustment_minor: int = Field(0, ge=0, le=10_000_000)


@router.get("/disputes", response_model=list[DisputeRow])
def disputes(principal: CurrentPrincipal, db: DbSession, scope: Literal["open", "closed", "all"] = "open") -> list[DisputeRow]:
    _guard(principal, ops.STAFF)
    stmt = (select(Dispute, Location.name, User.display_name).join(Booking, Booking.id == Dispute.booking_id)
            .join(Location, Location.id == Booking.location_id).join(User, User.id == Booking.user_id)
            .order_by(Dispute.created_at.desc()).limit(200))
    if scope == "open":
        stmt = stmt.where(Dispute.status.in_(OPEN_DISPUTES))
    elif scope == "closed":
        stmt = stmt.where(Dispute.status.not_in(OPEN_DISPUTES))
    return [DisputeRow(id=d.id, reference=d.reference, status=d.status, location_name=loc, customer_name=cust,
                       created_at=d.created_at, reason=d.reason[:160]) for d, loc, cust in db.execute(stmt).all()]


@router.get("/disputes/{dispute_id}", response_model=DisputeDetailOut)
def dispute_detail(dispute_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> DisputeDetailOut:
    _guard(principal, ops.STAFF)
    d = db.get(Dispute, dispute_id)
    if d is None:
        raise HTTPException(404, {"code": "dispute_not_found", "message": "Litige introuvable."})
    b = db.get(Booking, d.booking_id)
    loc = db.get(Location, b.location_id)
    merchant = db.get(Merchant, loc.merchant_id)
    tz = ZoneInfo(db.scalar(select(Market.timezone).where(Market.id == merchant.market_id)))
    payable = db.scalar(select(PartnerPayable).where(PartnerPayable.booking_id == b.id))
    payout = db.get(PartnerPayout, payable.payout_id) if payable and payable.payout_id else None
    return DisputeDetailOut(
        id=d.id, reference=d.reference, status=d.status, reason=d.reason, operator_notes=d.operator_notes,
        created_at=d.created_at, updated_at=d.updated_at, resolution_reason=d.resolution_reason,
        credits_restored=d.credits_restored, partner_adjustment_minor=d.partner_adjustment_minor,
        customer_name=db.scalar(select(User.display_name).where(User.id == b.user_id)),
        location_name=loc.name, location_kind=loc.kind_label, location_address=f"{loc.address_line}, {loc.postal_code}",
        cover_image_key=loc.cover_image_key, merchant_id=merchant.id,
        offer_title=db.scalar(select(OfferVersion.title).where(OfferVersion.id == b.offer_version_id)),
        booking_status=b.status, local_start=b.starts_at.astimezone(tz).replace(tzinfo=None).isoformat(timespec="minutes"),
        party_size=b.party_size, total_credits=b.total_credits,
        funding=funding_by_source(db, [b.id]).get(b.id, {}),
        payable_gross_minor=payable.amount_minor if payable else None,
        payable_net_minor=(payable.amount_minor - payable.commission_minor) if payable and payable.amount_minor is not None else None,
        currency=payable.currency if payable else None,
        payout_status=payout.status if payout else None, payout_paid_at=payout.paid_at if payout else None,
        timeline=_audit_rows(db, select(AuditEvent).where(AuditEvent.object_id == d.id).order_by(AuditEvent.created_at)),
        redeemed_at=b.redeemed_at,
    )


@router.post("/disputes/{dispute_id}/update", response_model=dict)
def dispute_update(dispute_id: uuid.UUID, body: DisputeUpdateIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _guard(principal, ops.STAFF)
    d = _commit(db, lambda: ops.update_dispute(db, dispute_id=dispute_id, status=body.status, notes=body.notes,
                                               reason=body.reason, by=principal.user.id))
    return {"status": d.status}


@router.post("/disputes/{dispute_id}/refund", response_model=dict)
def dispute_refund(dispute_id: uuid.UUID, body: RefundIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _guard(principal, ops.STAFF)
    d = _commit(db, lambda: ops.refund_dispute(db, dispute_id=dispute_id, reason=body.reason, by=principal.user.id,
                                               partner_adjustment_minor=body.partner_adjustment_minor))
    return {"status": d.status, "credits_restored": d.credits_restored}


@router.post("/disputes/{dispute_id}/reject", response_model=dict)
def dispute_reject(dispute_id: uuid.UUID, body: ReasonIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _guard(principal, ops.STAFF)
    d = _commit(db, lambda: ops.reject_dispute(db, dispute_id=dispute_id, reason=body.reason, by=principal.user.id))
    return {"status": d.status}


# ---------------------------------------------------------------- rapprochement


class ReconPayout(BaseModel):
    id: uuid.UUID
    merchant_name: str
    period_start: str
    status: str
    net_minor: int
    confirmed_minor: int | None
    currency: str


class ReconEvent(BaseModel):
    id: uuid.UUID
    event_type: str
    event_id: str
    received_at: datetime
    attempts: int
    last_error: str | None
    blocked: bool


class ReconInvoice(BaseModel):
    id: uuid.UUID
    reference: str
    organization_name: str
    amount_minor: int
    currency: str
    issued_on: str
    due_on: str
    is_demo: bool


class ReconciliationOut(BaseModel):
    payouts: list[ReconPayout]
    events: list[ReconEvent]
    employer_invoices: list[ReconInvoice]
    is_admin: bool


def _reconciliation_counts(db) -> dict[str, int]:
    return {
        "payouts": db.scalar(select(func.count()).select_from(PartnerPayout).where(PartnerPayout.status.in_(("to_reconcile", "failed")))),
        "events": db.scalar(select(func.count()).select_from(PaymentWebhookEvent).where(
            PaymentWebhookEvent.processed_at.is_(None), PaymentWebhookEvent.last_error.is_not(None))),
        "invoices": db.scalar(select(func.count()).select_from(EmployerInvoice).where(EmployerInvoice.status == "pending")),
    }


@router.get("/reconciliation", response_model=ReconciliationOut)
def reconciliation(principal: CurrentPrincipal, db: DbSession) -> ReconciliationOut:
    _guard(principal, ops.STAFF)
    payouts = db.execute(select(PartnerPayout, Merchant.display_name).join(Merchant, Merchant.id == PartnerPayout.merchant_id)
                         .where(PartnerPayout.status.in_(("to_reconcile", "failed"))).order_by(PartnerPayout.period_start)).all()
    events = db.scalars(select(PaymentWebhookEvent).where(PaymentWebhookEvent.processed_at.is_(None),
                                                          PaymentWebhookEvent.last_error.is_not(None))
                        .order_by(PaymentWebhookEvent.received_at).limit(100)).all()
    invoices = db.execute(select(EmployerInvoice, Organization.name).join(Organization, Organization.id == EmployerInvoice.organization_id)
                          .where(EmployerInvoice.status == "pending").order_by(EmployerInvoice.due_on)).all()
    return ReconciliationOut(
        payouts=[ReconPayout(id=p.id, merchant_name=n, period_start=str(p.period_start), status=p.status, net_minor=p.net_minor,
                             confirmed_minor=p.confirmed_minor, currency=p.currency) for p, n in payouts],
        events=[ReconEvent(id=e.id, event_type=e.event_type, event_id=e.event_id, received_at=e.received_at,
                           attempts=e.attempts, last_error=e.last_error, blocked=e.attempts >= MAX_ATTEMPTS) for e in events],
        employer_invoices=[ReconInvoice(id=i.id, reference=i.reference, organization_name=n, amount_minor=i.amount_minor,
                                        currency=i.currency, issued_on=str(i.issued_on), due_on=str(i.due_on), is_demo=i.is_demo)
                           for i, n in invoices],
        is_admin=principal.has_platform_role(*ops.ADMIN),
    )


@router.post("/payouts/{payout_id}/{action}", response_model=dict)
def payout_action(payout_id: uuid.UUID, action: Literal["retry", "close"], body: ReasonIn,
                  principal: CurrentPrincipal, db: DbSession) -> dict:
    _guard(principal, ops.ADMIN)
    _commit(db, lambda: ops.payout_action(db, payout_id=payout_id, action=action, reason=body.reason, by=principal.user.id))
    return {"ok": True}


@router.post("/payment-events/{event_id}/{action}", response_model=dict)
def event_action(event_id: uuid.UUID, action: Literal["retry", "dismiss"], body: ReasonIn,
                 principal: CurrentPrincipal, db: DbSession) -> dict:
    _guard(principal, ops.ADMIN)
    _commit(db, lambda: ops.webhook_action(db, event_id=event_id, action=action, reason=body.reason, by=principal.user.id))
    return {"ok": True}


# ---------------------------------------------------------------- audit


@router.get("/audit", response_model=list[AuditOut])
def audit_log(principal: CurrentPrincipal, db: DbSession, object_type: str | None = None,
              limit: Annotated[int, Query(ge=1, le=500)] = 100) -> list[AuditOut]:
    _guard(principal, ops.STAFF)
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    if object_type:
        stmt = stmt.where(AuditEvent.object_type == object_type)
    return _audit_rows(db, stmt)


# ---------------------------------------------------------------- accès commerçants et entreprises


class VenueBrief(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: str


class OrgMerchant(BaseModel):
    id: uuid.UUID
    display_name: str
    city_label: str
    commercial_status: str
    owner_email: str | None
    venues: list[VenueBrief]


class OrganizationRow(BaseModel):
    id: uuid.UUID
    name: str
    city_label: str | None
    is_demo: bool
    hr_accounts: int
    merchants: list[OrgMerchant]


class RhServiceIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    city_label: str = Field("", max_length=80)
    hr_email: str = Field(max_length=254)


@router.get("/organizations", response_model=list[OrganizationRow])
def organizations(principal: CurrentPrincipal, db: DbSession) -> list[OrganizationRow]:
    from app.modules.catalog.chain import list_for_org

    _guard(principal, ops.STAFF)
    counts = dict(db.execute(select(Membership.scope_id, func.count()).where(Membership.scope_type == "organization")
                             .group_by(Membership.scope_id)).all())
    rows = db.scalars(select(Organization).order_by(Organization.name)).all()
    return [OrganizationRow(id=o.id, name=o.name, city_label=o.city_label, is_demo=o.is_demo,
                            hr_accounts=int(counts.get(o.id, 0)), merchants=list_for_org(db, o.id))
            for o in rows]


@router.post("/organizations", response_model=OrganizationRow, status_code=201)
def create_organization(body: RhServiceIn, principal: CurrentPrincipal, db: DbSession) -> OrganizationRow:
    from app.modules.catalog.chain import list_for_org

    _guard(principal, ops.ADMIN)
    org = _commit(db, lambda: ops.create_rh_service(
        db, name=body.name, city_label=body.city_label, hr_email=body.hr_email,
        by=principal.user.id, by_name=principal.user.display_name,
    ))
    return OrganizationRow(id=org.id, name=org.name, city_label=org.city_label, is_demo=org.is_demo,
                           hr_accounts=1, merchants=list_for_org(db, org.id))


class AccessRow(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    linked: bool  # compte déjà relié à la page sécurisée (première connexion faite)
    created_at: datetime


class AccessIn(BaseModel):
    email: str = Field(max_length=254)
    scope_type: Literal["merchant", "organization"]
    scope_id: uuid.UUID
    role: Literal["merchant_owner", "merchant_staff", "hr_admin", "hr_viewer"]


@router.get("/access", response_model=list[AccessRow])
def access_list(principal: CurrentPrincipal, db: DbSession, scope_type: Literal["merchant", "organization"],
                scope_id: uuid.UUID) -> list[AccessRow]:
    _guard(principal, ops.STAFF)
    rows = db.execute(select(Membership, User).join(User, User.id == Membership.user_id)
                      .where(Membership.scope_type == scope_type, Membership.scope_id == scope_id)
                      .order_by(Membership.created_at)).all()
    return [AccessRow(id=m.id, email=u.email, display_name=u.display_name, role=m.role,
                      linked=u.oidc_subject is not None, created_at=m.created_at) for m, u in rows]


@router.post("/access", response_model=dict, status_code=201)
def access_grant(body: AccessIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _guard(principal, ops.ADMIN)
    m = _commit(db, lambda: ops.grant_access(db, email=body.email, scope_type=body.scope_type,
                                             scope_id=body.scope_id, role=body.role, by=principal.user.id))
    return {"id": str(m.id)}


@router.post("/access/{membership_id}/revoke", response_model=dict)
def access_revoke(membership_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> dict:
    _guard(principal, ops.ADMIN)
    _commit(db, lambda: ops.revoke_access(db, membership_id=membership_id, by=principal.user.id))
    return {"ok": True}


# ---------------------------------------------------------------- lieux de démonstration


class DemoVisibilityIn(ReasonIn):
    visible: bool


@router.post("/demo-locations", response_model=dict)
def demo_locations(body: DemoVisibilityIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    """Masque (ou réaffiche) d'un geste les lieux de démonstration, quand les vrais partenaires sont publiés."""
    _guard(principal, ops.ADMIN)
    n = _commit(db, lambda: ops.set_demo_visibility(db, visible=body.visible, reason=body.reason, by=principal.user.id))
    return {"changed": n}


# ---------------------------------------------------------------- demandes de modification d'établissement


class ChangeRequestRow(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    location_name: str
    merchant_name: str
    requested_by: str
    changes: dict
    status: str
    decision_reason: str | None
    created_at: datetime


class ChangeDecisionIn(ReasonIn):
    approve: bool


@router.get("/change-requests", response_model=list[ChangeRequestRow])
def change_requests(principal: CurrentPrincipal, db: DbSession,
                    status: Literal["pending", "approved", "rejected"] = "pending") -> list[ChangeRequestRow]:
    _guard(principal, ops.STAFF)
    from app.modules.catalog.models import LocationChangeRequest

    rows = db.execute(
        select(LocationChangeRequest, Location.name, Merchant.display_name, User.email)
        .join(Location, Location.id == LocationChangeRequest.location_id)
        .join(Merchant, Merchant.id == Location.merchant_id)
        .join(User, User.id == LocationChangeRequest.requested_by)
        .where(LocationChangeRequest.status == status).order_by(LocationChangeRequest.created_at).limit(100)
    ).all()
    return [ChangeRequestRow(id=r.id, location_id=r.location_id, location_name=ln, merchant_name=mn, requested_by=email,
                             changes=r.changes, status=r.status, decision_reason=r.decision_reason, created_at=r.created_at)
            for r, ln, mn, email in rows]


@router.post("/change-requests/{request_id}/decision", response_model=dict)
def change_decision(request_id: uuid.UUID, body: ChangeDecisionIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _guard(principal, ops.STAFF)
    from app.modules.catalog import onboarding

    try:
        onboarding.decide_change(db, request_id=request_id, approve=body.approve, reason=body.reason, by=principal.user.id)
        db.commit()
    except (onboarding.OnboardingError, ops.OpsError) as exc:
        db.rollback()
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc
    return {"ok": True}


# ---------------------------------------------------------------- formules d'abonnement


class AdminPlanOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    price_minor: int
    currency: str
    credits_per_period: int
    credit_validity_days: int | None
    psp_price_id: str | None
    is_active: bool
    is_demo: bool
    subscribers: int


class AdminPlanIn(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=2, max_length=80)
    price_minor: int = Field(ge=100, le=1_000_000)
    credits_per_period: int = Field(ge=1, le=10_000)
    credit_validity_days: int | None = Field(None, ge=7, le=366)
    psp_price_id: str | None = Field(None, max_length=120)
    is_active: bool = True


def _plans_out(db, market: str) -> list[AdminPlanOut]:
    from app.modules.payments import plans as plan_service

    try:
        rows = plan_service.list_plans(db, market)
    except plan_service.PlanError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc
    return [AdminPlanOut(id=p.id, code=p.code, name=p.name, price_minor=p.price_minor, currency=p.currency,
                         credits_per_period=p.credits_per_period, credit_validity_days=p.credit_validity_days,
                         psp_price_id=p.psp_price_id, is_active=p.is_active, is_demo=p.is_demo, subscribers=n)
            for p, n in rows]


@router.get("/plans", response_model=list[AdminPlanOut])
def admin_plans(principal: CurrentPrincipal, db: DbSession, market: str = "FR") -> list[AdminPlanOut]:
    _guard(principal, ops.STAFF)
    return _plans_out(db, market)


def _save_plan(db, principal, market: str, plan_id: uuid.UUID | None, body: AdminPlanIn) -> list[AdminPlanOut]:
    from app.modules.payments import plans as plan_service

    _guard(principal, ops.ADMIN)
    try:
        plan_service.save_plan(db, market_code=market, plan_id=plan_id, data=body.model_dump(), by=principal.user.id)
        db.commit()
    except plan_service.PlanError as exc:
        db.rollback()
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc
    return _plans_out(db, market)


@router.post("/plans", response_model=list[AdminPlanOut], status_code=201)
def create_plan(body: AdminPlanIn, principal: CurrentPrincipal, db: DbSession, market: str = "FR") -> list[AdminPlanOut]:
    return _save_plan(db, principal, market, None, body)


@router.put("/plans/{plan_id}", response_model=list[AdminPlanOut])
def update_plan(plan_id: uuid.UUID, body: AdminPlanIn, principal: CurrentPrincipal, db: DbSession,
                market: str = "FR") -> list[AdminPlanOut]:
    return _save_plan(db, principal, market, plan_id, body)
