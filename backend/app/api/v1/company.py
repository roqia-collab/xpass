"""Portail entreprise (RH) — maquettes 23 à 25 — et acceptation de l'invitation par le salarié."""
import csv
import io
import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.api.deps import CurrentPrincipal, DbSession, forbidden
from app.modules.catalog.models import Category, Offer
from app.modules.employer import service as s
from app.modules.employer.models import BudgetPolicy, Employee, EmployerAllocation, EmployerInvoice

router = APIRouter(tags=["entreprise"])


def _http(exc: s.EmployerError) -> HTTPException:
    return HTTPException(exc.status, {"code": exc.code, "message": exc.message, **exc.extra})


def _org(db, principal, roles):
    try:
        return s.organization_for(db, principal, roles)
    except s.EmployerError as exc:
        raise _http(exc) from exc


def _commit(db, fn):
    try:
        result = fn()
        db.commit()
        return result
    except s.EmployerError as exc:
        db.rollback()
        raise _http(exc) from exc


def _period(value: str | None, db, org) -> date:
    if not value:
        return s.current_period(db, org)
    try:
        return datetime.strptime(value, "%Y-%m").date()
    except ValueError:
        raise HTTPException(422, {"code": "invalid_period", "message": "Période attendue au format AAAA-MM."}) from None


# ---------------------------------------------------------------- schémas


class PolicyOut(BaseModel):
    credits_per_month: int
    eligible_categories: list[str] | None
    credit_validity_days: int
    effective_from: date


class ContractOut(BaseModel):
    status: str
    credit_price_minor: int
    currency: str
    starts_on: date
    term_months: int = 12
    covered_cities: list[str] = ["Paris"]
    commission_bps: int = 1000
    free_cancellation_hours: int = 24
    is_demo: bool


class CategoryUsage(BaseModel):
    slug: str
    name: str
    masked: bool
    share: int | None
    employees: int | None


class ReportOut(BaseModel):
    period: date
    currency: str | None
    eligible: int
    active: int
    activation_rate: int
    monthly_budget_minor: int
    allocated_credits: int
    allocated_cost_minor: int
    consumed_credits: int
    consumed_cost_minor: int
    # Part des crédits consommés liée aux annulations tardives et absences (agrégé).
    penalty_credits: int = 0
    balance_minor: int
    categories: list[CategoryUsage]
    privacy_threshold: int


class OverviewOut(BaseModel):
    organization_name: str
    can_edit: bool
    contract: ContractOut | None
    policy: PolicyOut | None
    next_policy: PolicyOut | None
    categories: list[dict]
    report: ReportOut


class EmployeeOut(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    status: str
    invited_at: datetime
    joined_at: datetime | None
    credits_this_month: int | None


class InviteIn(BaseModel):
    email: str = Field(max_length=254)
    first_name: str = Field("", max_length=80)
    last_name: str = Field("", max_length=80)


class CsvIn(BaseModel):
    content: str = Field(max_length=s.MAX_CSV_BYTES)
    mapping: dict[Literal["email", "first_name", "last_name"], str] | None = None


class CsvRowOut(BaseModel):
    line: int
    email: str
    last_name: str
    first_name: str
    problem: str | None
    detail: str | None


class CsvPreviewOut(BaseModel):
    headers: list[str]
    mapping: dict[str, str]
    valid_count: int
    duplicate_count: int
    invalid_count: int
    errors: list[CsvRowOut]


class PolicyIn(BaseModel):
    credits_per_month: int = Field(ge=1, le=10_000)
    eligible_categories: list[str] | None = None
    credit_validity_days: int = Field(60, ge=7, le=366)
    effective_from: date


class FundingIn(BaseModel):
    amount_minor: int = Field(ge=100, le=100_000_000)


class InvoiceOut(BaseModel):
    id: uuid.UUID
    reference: str
    label: str
    amount_minor: int
    currency: str
    issued_on: date
    due_on: date
    status: str
    paid_at: datetime | None
    is_demo: bool


class AllocationDayOut(BaseModel):
    day: date
    employees: int
    credits: int
    cost_minor: int


class InvitationOut(BaseModel):
    id: uuid.UUID
    organization_name: str


# ---------------------------------------------------------------- vue d'ensemble


def _policy_out(p: BudgetPolicy | None) -> PolicyOut | None:
    return PolicyOut.model_validate(p, from_attributes=True) if p else None


@router.get("/company/overview", response_model=OverviewOut)
def overview(principal: CurrentPrincipal, db: DbSession, period: str | None = None) -> OverviewOut:
    org = _org(db, principal, s.HR_READ)
    p = _period(period, db, org)
    contract = s.contract_of(db, org)
    current = s.policy_for(db, org, p)
    upcoming = db.scalar(select(BudgetPolicy).where(BudgetPolicy.organization_id == org.id, BudgetPolicy.effective_from > p)
                         .order_by(BudgetPolicy.effective_from).limit(1))
    return OverviewOut(
        organization_name=org.name,
        can_edit=org.id in principal.scope_ids("organization", s.HR_WRITE),
        contract=ContractOut.model_validate(contract, from_attributes=True) if contract else None,
        policy=_policy_out(current),
        next_policy=_policy_out(upcoming),
        categories=[{"slug": slug, "name": name} for slug, name in db.execute(select(Category.slug, Category.name).order_by(Category.sort_order))],
        report=ReportOut(**s.report(db, org, p)),
    )


@router.put("/company/policy", response_model=PolicyOut)
def set_policy(body: PolicyIn, principal: CurrentPrincipal, db: DbSession) -> PolicyOut:
    org = _org(db, principal, s.HR_WRITE)
    policy = _commit(db, lambda: s.set_policy(db, org, by=principal.user.id, **body.model_dump()))
    return _policy_out(policy)


# ---------------------------------------------------------------- salariés


@router.get("/company/employees", response_model=list[EmployeeOut])
def employees(principal: CurrentPrincipal, db: DbSession, status: str | None = None,
              q: Annotated[str | None, Query(max_length=80)] = None) -> list[EmployeeOut]:
    org = _org(db, principal, s.HR_READ)
    period = s.current_period(db, org)
    stmt = select(Employee).where(Employee.organization_id == org.id)
    if status:
        stmt = stmt.where(Employee.status == status)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(Employee.email.like(like), func.lower(Employee.last_name).like(like),
                              func.lower(Employee.first_name).like(like)))
    rows = db.scalars(stmt.order_by(Employee.invited_at.desc()).limit(500)).all()
    alloc = dict(db.execute(select(EmployerAllocation.employee_id, EmployerAllocation.credits).where(
        EmployerAllocation.organization_id == org.id, EmployerAllocation.period == period)).all())
    return [EmployeeOut(id=e.id, email=e.email, first_name=e.first_name, last_name=e.last_name, status=e.status,
                        invited_at=e.invited_at, joined_at=e.joined_at, credits_this_month=alloc.get(e.id))
            for e in rows]


@router.post("/company/employees", status_code=201, response_model=EmployeeOut)
def invite(body: InviteIn, principal: CurrentPrincipal, db: DbSession) -> EmployeeOut:
    org = _org(db, principal, s.HR_WRITE)
    e = _commit(db, lambda: s.invite(db, org, by=principal.user.id, **body.model_dump()))
    return EmployeeOut(id=e.id, email=e.email, first_name=e.first_name, last_name=e.last_name, status=e.status,
                       invited_at=e.invited_at, joined_at=None, credits_this_month=None)


def _preview_out(p: s.CsvPreview) -> CsvPreviewOut:
    return CsvPreviewOut(
        headers=p.headers, mapping=p.mapping, valid_count=len(p.valid),
        duplicate_count=sum(1 for r in p.errors if r.problem == "duplicate"),
        invalid_count=sum(1 for r in p.errors if r.problem == "invalid_email"),
        errors=[CsvRowOut(**r.__dict__) for r in p.errors[:200]],
    )


@router.post("/company/employees/import/preview", response_model=CsvPreviewOut)
def import_preview(body: CsvIn, principal: CurrentPrincipal, db: DbSession) -> CsvPreviewOut:
    org = _org(db, principal, s.HR_WRITE)
    try:
        return _preview_out(s.preview_csv(db, org, body.content, body.mapping))
    except s.EmployerError as exc:
        raise _http(exc) from exc


@router.post("/company/employees/import", response_model=dict)
def import_confirm(body: CsvIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    org = _org(db, principal, s.HR_WRITE)
    created = _commit(db, lambda: s.import_csv(db, org, body.content, body.mapping, principal.user.id))
    return {"created": created}


@router.post("/company/employees/{employee_id}/{action}", response_model=dict)
def employee_action(employee_id: uuid.UUID, action: Literal["suspend", "reactivate", "remove"],
                    principal: CurrentPrincipal, db: DbSession) -> dict:
    org = _org(db, principal, s.HR_WRITE)
    e = _commit(db, lambda: s.set_status(db, org, employee_id, action))
    return {"status": e.status}


# ---------------------------------------------------------------- financements, allocations, rapports


@router.get("/company/invoices", response_model=list[InvoiceOut])
def invoices(principal: CurrentPrincipal, db: DbSession) -> list[InvoiceOut]:
    org = _org(db, principal, s.HR_READ)
    rows = db.scalars(select(EmployerInvoice).where(EmployerInvoice.organization_id == org.id)
                      .order_by(EmployerInvoice.issued_on.desc(), EmployerInvoice.reference.desc()).limit(60))
    return [InvoiceOut.model_validate(i, from_attributes=True) for i in rows]


@router.post("/company/invoices", status_code=201, response_model=InvoiceOut)
def request_funding(body: FundingIn, principal: CurrentPrincipal, db: DbSession) -> InvoiceOut:
    org = _org(db, principal, s.HR_WRITE)
    inv = _commit(db, lambda: s.request_funding(db, org, amount_minor=body.amount_minor, by=principal.user.id))
    return InvoiceOut.model_validate(inv, from_attributes=True)


@router.get("/company/allocations", response_model=list[AllocationDayOut])
def allocations(principal: CurrentPrincipal, db: DbSession, period: str | None = None) -> list[AllocationDayOut]:
    """Calendrier agrégé par jour (aucun détail par salarié)."""
    org = _org(db, principal, s.HR_READ)
    p = _period(period, db, org)
    day = func.date(EmployerAllocation.created_at)
    rows = db.execute(
        select(day, func.count(), func.sum(EmployerAllocation.credits), func.sum(EmployerAllocation.cost_minor))
        .where(EmployerAllocation.organization_id == org.id, EmployerAllocation.period == p)
        .group_by(day).order_by(day)
    ).all()
    return [AllocationDayOut(day=d, employees=n, credits=int(c), cost_minor=int(m)) for d, n, c, m in rows]


@router.get("/company/report", response_model=ReportOut)
def report(principal: CurrentPrincipal, db: DbSession, period: str | None = None) -> ReportOut:
    org = _org(db, principal, s.HR_READ)
    return ReportOut(**s.report(db, org, _period(period, db, org)))


def _cell(value) -> str:
    """Neutralise l'injection de formules dans un tableur."""
    v = str(value)
    return "'" + v if v[:1] in ("=", "+", "-", "@") else v


@router.get("/company/report.csv", response_class=Response)
def report_csv(principal: CurrentPrincipal, db: DbSession, period: str | None = None) -> Response:
    org = _org(db, principal, s.HR_READ)
    r = s.report(db, org, _period(period, db, org))
    money = lambda m: f"{m // 100},{m % 100:02d}"  # noqa: E731
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Organisation", _cell(org.name)])
    w.writerow(["Période", r["period"].strftime("%m/%Y"), "Devise", r["currency"] or ""])
    for label, value in [("Salariés éligibles", r["eligible"]), ("Salariés actifs", r["active"]),
                         ("Taux d'activation (%)", r["activation_rate"]), ("Crédits alloués", r["allocated_credits"]),
                         ("Coût alloué", money(r["allocated_cost_minor"])), ("Crédits utilisés", r["consumed_credits"]),
                         ("Financement disponible", money(r["balance_minor"]))]:
        w.writerow([label, value])
    w.writerow([])
    w.writerow(["Catégorie", "Part des crédits utilisés (%)", "Salariés"])
    for c in r["categories"]:
        w.writerow([c["name"], "masqué" if c["masked"] else c["share"], "masqué" if c["masked"] else c["employees"]])
    w.writerow([f"Détail masqué sous {r['privacy_threshold']} salariés (confidentialité)."])
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="rapport-{r["period"]:%Y-%m}.csv"'})


# ---------------------------------------------------------------- administration (interface au lot 7)


@router.post("/admin/employer-invoices/{invoice_id}/confirm-payment", response_model=InvoiceOut, tags=["administration"])
def confirm_payment(invoice_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> InvoiceOut:
    if not principal.has_platform_role("platform_admin"):
        raise forbidden("Réservé à l'administration XPASS.")
    def fn():
        from app.modules.ops.service import audit

        invoice = s.confirm_payment(db, invoice_id, by=principal.user.id)
        audit(db, actor_kind="operator", actor_user_id=principal.user.id, action="employer_invoice.paid",
              object_type="employer_invoice", object_id=invoice.id, object_label=invoice.reference,
              reason="Virement reçu", details={"amount_minor": invoice.amount_minor, "currency": invoice.currency})
        return invoice

    inv = _commit(db, fn)
    return InvoiceOut.model_validate(inv, from_attributes=True)


# ---------------------------------------------------------------- salarié (application)


@router.get("/me/employer-invitations", response_model=list[InvitationOut], tags=["salarié"])
def my_invitations(principal: CurrentPrincipal, db: DbSession) -> list[InvitationOut]:
    return [InvitationOut(id=e.id, organization_name=o.name) for e, o in s.my_invitations(db, principal.user)]


@router.post("/me/employer-invitations/{employee_id}/accept", response_model=dict, tags=["salarié"])
def accept_invitation(employee_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> dict:
    e = _commit(db, lambda: s.accept(db, principal.user, employee_id))
    return {"status": e.status}



class PayOut(BaseModel):
    url: str


@router.post("/company/invoices/{invoice_id}/pay", response_model=PayOut)
def pay_invoice(invoice_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> PayOut:
    """Paiement en ligne d'une facture de financement (carte ou prélèvement SEPA) sur la page du prestataire."""
    from app.core.config import get_settings
    from app.modules.payments.provider import ProviderError, ProviderNotConfigured, get_provider

    org = _org(db, principal, s.HR_WRITE)
    invoice = db.get(EmployerInvoice, invoice_id)
    if invoice is None or invoice.organization_id != org.id:
        raise HTTPException(404, {"code": "invoice_not_found", "message": "Facture introuvable."})
    if invoice.status != "pending":
        raise HTTPException(409, {"code": "invoice_not_payable", "message": "Cette facture n'est pas en attente de paiement."})
    try:
        checkout = get_provider().create_invoice_checkout(
            invoice_id=invoice.id, reference=invoice.reference, amount_minor=invoice.amount_minor,
            currency=invoice.currency, customer_email=principal.user.email,
            return_url=f"{get_settings().portals_public_url.rstrip('/')}/company/factures")
    except ProviderNotConfigured as exc:
        raise HTTPException(503, {"code": "psp_not_configured", "message": str(exc)}) from exc
    except ProviderError as exc:
        raise HTTPException(502, {"code": "psp_error", "message": str(exc)}) from exc
    return PayOut(url=checkout.url)



# ---------------------------------------------------------------- synchronisation RH (logiciel RH → XPASS)


class ApiKeyOut(BaseModel):
    id: uuid.UUID
    label: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class ApiKeyCreated(ApiKeyOut):
    key: str  # affichée une seule fois


class ApiKeyIn(BaseModel):
    label: str = Field("Logiciel RH", max_length=80)


@router.get("/company/api-keys", response_model=list[ApiKeyOut])
def api_keys(principal: CurrentPrincipal, db: DbSession) -> list[ApiKeyOut]:
    from app.modules.employer.models import OrganizationApiKey

    org = _org(db, principal, s.HR_WRITE)
    rows = db.scalars(select(OrganizationApiKey).where(OrganizationApiKey.organization_id == org.id)
                      .order_by(OrganizationApiKey.created_at.desc()))
    return [ApiKeyOut.model_validate(k, from_attributes=True) for k in rows]


@router.post("/company/api-keys", response_model=ApiKeyCreated, status_code=201)
def create_api_key(body: ApiKeyIn, principal: CurrentPrincipal, db: DbSession) -> ApiKeyCreated:
    from app.modules.employer import hr_sync

    org = _org(db, principal, s.HR_WRITE)
    key, raw = _commit(db, lambda: hr_sync.issue_key(db, org, label=body.label, by=principal.user.id))
    return ApiKeyCreated(**ApiKeyOut.model_validate(key, from_attributes=True).model_dump(), key=raw)


class VenueBrief(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: str
    address_line: str = ""
    postal_code: str = ""
    district_label: str = ""
    description: str = ""
    cover_image_key: str | None = None
    price_credits: int | None = None
    subcategory_slug: str = ""


class CompanyMerchantOut(BaseModel):
    id: uuid.UUID
    display_name: str
    city_label: str
    commercial_status: str
    owner_email: str | None
    venues: list[VenueBrief]


class CompanyMerchantIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    owner_email: str = Field(max_length=254)
    location_name: str = Field(min_length=2, max_length=120)
    subcategory_slug: str = Field(min_length=2, max_length=32)
    address_line: str = Field(min_length=3, max_length=200)
    postal_code: str = Field(min_length=4, max_length=12)
    city: str = Field(min_length=2, max_length=80)
    description: str = Field("", max_length=2000)
    price_credits: int = Field(8, ge=1, le=500)


@router.get("/company/merchants", response_model=list[CompanyMerchantOut])
def company_merchants(principal: CurrentPrincipal, db: DbSession) -> list[CompanyMerchantOut]:
    from app.modules.catalog.chain import list_for_org

    org = _org(db, principal, s.HR_READ)
    return list_for_org(db, org.id)


@router.post("/company/merchants", response_model=CompanyMerchantOut, status_code=201)
def create_company_merchant(body: CompanyMerchantIn, principal: CurrentPrincipal, db: DbSession) -> CompanyMerchantOut:
    from app.modules.catalog import management, onboarding
    from app.modules.catalog.chain import MerchantDraft, create_merchant_for_org, list_for_org
    from app.modules.ops.service import OpsError

    org = _org(db, principal, s.HR_WRITE)
    try:
        merchant = create_merchant_for_org(db, org, principal.user, MerchantDraft(**body.model_dump()))
        db.commit()
    except (onboarding.OnboardingError, management.ManageError, OpsError) as exc:
        db.rollback()
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc
    row = next(item for item in list_for_org(db, org.id) if item["id"] == merchant.id)
    return row


class AddressIn(BaseModel):
    address_line: str = Field(min_length=3, max_length=200)
    postal_code: str = Field(min_length=4, max_length=12)
    city: str = Field(min_length=2, max_length=80)


class AddressOut(BaseModel):
    label: str
    address_line: str
    postal_code: str
    city: str
    district: str
    latitude: float
    longitude: float


class VisibilityIn(BaseModel):
    published: bool


@router.post("/company/merchants/locate", response_model=AddressOut)
def locate_merchant(body: AddressIn, principal: CurrentPrincipal, db: DbSession) -> AddressOut:
    from app.modules.catalog import onboarding
    from app.modules.catalog.chain import preview_address

    _org(db, principal, s.HR_WRITE)
    try:
        return AddressOut(**preview_address(body.address_line, body.postal_code, body.city))
    except onboarding.OnboardingError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc


@router.patch("/company/merchants/{merchant_id}", response_model=CompanyMerchantOut)
def update_company_merchant(merchant_id: uuid.UUID, body: CompanyMerchantIn, principal: CurrentPrincipal, db: DbSession) -> CompanyMerchantOut:
    from app.modules.catalog import management, onboarding
    from app.modules.catalog.chain import MerchantDraft, list_for_org, update_merchant_for_org
    from app.modules.ops.service import OpsError

    org = _org(db, principal, s.HR_WRITE)
    try:
        merchant = update_merchant_for_org(db, org, principal.user, merchant_id, MerchantDraft(**body.model_dump()))
        db.commit()
    except (onboarding.OnboardingError, management.ManageError, OpsError) as exc:
        db.rollback()
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc
    return next(item for item in list_for_org(db, org.id) if item["id"] == merchant.id)


@router.post("/company/merchants/{merchant_id}/visibility", response_model=CompanyMerchantOut)
def merchant_visibility(merchant_id: uuid.UUID, body: VisibilityIn, principal: CurrentPrincipal, db: DbSession) -> CompanyMerchantOut:
    from app.modules.catalog import onboarding
    from app.modules.catalog.chain import list_for_org, set_visibility

    org = _org(db, principal, s.HR_WRITE)
    try:
        merchant = set_visibility(db, org, principal.user, merchant_id, body.published)
        db.commit()
    except onboarding.OnboardingError as exc:
        db.rollback()
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc
    return next(item for item in list_for_org(db, org.id) if item["id"] == merchant.id)


@router.post("/company/merchants/{merchant_id}/cover", response_model=dict)
async def merchant_cover(merchant_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession, file: UploadFile = File(...)) -> dict:
    from app.modules.catalog import onboarding, photos
    from app.modules.catalog.chain import _owned
    from app.modules.catalog.models import Location

    org = _org(db, principal, s.HR_WRITE)
    try:
        merchant = _owned(db, org, merchant_id)
    except onboarding.OnboardingError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from exc
    location = db.scalar(select(Location).where(Location.merchant_id == merchant.id).order_by(Location.name))
    if location is None:
        raise HTTPException(404, {"code": "location_missing", "message": "Aucun établissement à illustrer."})
    data = await file.read(photos.MAX_BYTES + 1)
    try:
        jpeg = photos.prepare(data)
    except photos.PhotoError as exc:
        raise HTTPException(422, {"code": exc.code, "message": exc.message}) from exc
    key = onboarding.new_media_key(merchant.id)
    photos.store(key, jpeg)
    location.cover_image_key = key
    offer = db.scalar(select(Offer).where(Offer.location_id == location.id).order_by(Offer.sort_order))
    if offer is not None and not offer.image_key:
        offer.image_key = key
    db.commit()
    return {"image_key": key}


class CompanyEventIn(BaseModel):
    location_id: uuid.UUID
    title: str = Field(min_length=2, max_length=120)
    summary: str = Field("", max_length=500)
    starts_at: datetime
    ends_at: datetime
    price_credits: int = Field(ge=1, le=500)


class CompanyEventVisibility(BaseModel):
    published: bool


def _event_http(exc) -> HTTPException:
    return HTTPException(exc.status, {"code": exc.code, "message": exc.message})


@router.get("/company/events")
def company_events(principal: CurrentPrincipal, db: DbSession) -> list[dict]:
    from app.modules.catalog.events import list_managed

    org = _org(db, principal, s.HR_READ)
    return list_managed(db, org.id)


@router.post("/company/events", status_code=201)
def company_create_event(body: CompanyEventIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    from app.modules.catalog.events import EventError, create_event

    org = _org(db, principal, s.HR_WRITE)
    try:
        event = create_event(
            db, location_id=body.location_id, title=body.title, summary=body.summary,
            starts_at=body.starts_at, ends_at=body.ends_at, price_credits=body.price_credits,
            by=principal.user.id, actor_kind="hr", organization_id=org.id,
        )
        db.commit()
    except EventError as exc:
        db.rollback()
        raise _event_http(exc) from exc
    return {"id": event.id}


@router.patch("/company/events/{event_id}")
def company_update_event(event_id: uuid.UUID, body: CompanyEventIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    from app.modules.catalog.events import EventError, update_event

    org = _org(db, principal, s.HR_WRITE)
    try:
        event = update_event(
            db, event_id, title=body.title, summary=body.summary, starts_at=body.starts_at, ends_at=body.ends_at,
            price_credits=body.price_credits, by=principal.user.id, actor_kind="hr", organization_id=org.id,
        )
        db.commit()
    except EventError as exc:
        db.rollback()
        raise _event_http(exc) from exc
    return {"id": event.id}


@router.post("/company/events/{event_id}/visibility")
def company_event_visibility(event_id: uuid.UUID, body: CompanyEventVisibility, principal: CurrentPrincipal, db: DbSession) -> dict:
    from app.modules.catalog.events import EventError, set_event_visible

    org = _org(db, principal, s.HR_WRITE)
    try:
        event = set_event_visible(
            db, event_id, published=body.published, by=principal.user.id, actor_kind="hr", organization_id=org.id,
        )
        db.commit()
    except EventError as exc:
        db.rollback()
        raise _event_http(exc) from exc
    return {"id": event.id, "status": event.status}


@router.post("/company/events/{event_id}/cover")
async def company_event_cover(event_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession, file: UploadFile = File(...)) -> dict:
    from app.modules.catalog import onboarding, photos
    from app.modules.catalog.events import EventError, set_cover

    org = _org(db, principal, s.HR_WRITE)
    data = await file.read(photos.MAX_BYTES + 1)
    try:
        jpeg = photos.prepare(data)
        event = set_cover(db, event_id, onboarding.new_media_key(org.id), org.id)
        photos.store(event.cover_image_key, jpeg)
        db.commit()
    except photos.PhotoError as exc:
        db.rollback()
        raise HTTPException(422, {"code": exc.code, "message": exc.message}) from exc
    except EventError as exc:
        db.rollback()
        raise _event_http(exc) from exc
    return {"image_key": event.cover_image_key}


@router.post("/company/api-keys/{key_id}/revoke", response_model=dict)
def revoke_api_key(key_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> dict:
    from app.modules.employer import hr_sync

    org = _org(db, principal, s.HR_WRITE)
    _commit(db, lambda: hr_sync.revoke_key(db, org, key_id))
    return {"ok": True}


class SyncEmployeeIn(BaseModel):
    email: str = Field(max_length=254)
    first_name: str = Field("", max_length=80)
    last_name: str = Field("", max_length=80)


class SyncIn(BaseModel):
    employees: list[SyncEmployeeIn]
    remove_missing: bool = False


@router.put("/hr-sync/employees", tags=["synchronisation RH"])
def hr_sync_employees(body: SyncIn, db: DbSession, authorization: Annotated[str | None, Header()] = None,
                      dry_run: bool = False) -> dict:
    """Liste complète des salariés éligibles envoyée par le logiciel RH (clé d'API de l'entreprise)."""
    from app.modules.employer import hr_sync
    from app.modules.ops.service import audit

    raw = (authorization or "").removeprefix("Bearer ").strip()
    org = hr_sync.authenticate(db, raw)
    if org is None:
        raise HTTPException(401, {"code": "invalid_api_key", "message": "Clé d'API invalide ou révoquée."})
    rows = [hr_sync.SyncRow(email=e.email, first_name=e.first_name, last_name=e.last_name) for e in body.employees]
    result = _commit(db, lambda: _sync_and_audit(db, org, rows, body.remove_missing, dry_run, hr_sync, audit))
    return {"dry_run": dry_run, "invited": len(result.invited), "updated": len(result.updated),
            "unchanged": result.unchanged, "removed": len(result.removed), "skipped": result.skipped}


def _sync_and_audit(db, org, rows, remove_missing, dry_run, hr_sync, audit):
    result = hr_sync.sync(db, org, rows, remove_missing=remove_missing, dry_run=dry_run)
    if not dry_run:
        audit(db, actor_kind="system", actor_user_id=None, action="employer.hr_sync", object_type="organization",
              object_id=org.id, object_label=org.name,
              details={"invited": len(result.invited), "updated": len(result.updated), "removed": len(result.removed),
                       "skipped": len(result.skipped)})
    return result
