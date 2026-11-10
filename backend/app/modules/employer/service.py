"""Avantage salarié (maquettes 23 à 25).

Flux :
1. Les RH invitent des salariés (un par un ou par CSV avec aperçu des erreurs).
2. Le salarié accepte dans l'application, connecté avec l'adresse e-mail invitée.
3. Chaque mois, chaque salarié actif reçoit les crédits de la politique en vigueur, si le contrat est
   actif et si le financement reçu (factures payées) couvre le coût. Une seule allocation par mois.
4. Les RH suivent des indicateurs agrégés ; les détails sous le seuil de confidentialité sont masqués.
"""
import csv
import io
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.booking.models import Booking
from app.modules.catalog.models import Category, Location, Market, Subcategory
from app.modules.employer.models import BudgetPolicy, Employee, EmployerAllocation, EmployerContract, EmployerInvoice
from app.modules.identity.models import Organization, User
from app.modules.payments.service import post_money
from app.modules.platform.service import emit
from app.modules.wallet import service as wallet_service
from app.modules.wallet.models import CreditJournal, CreditJournalLine

HR_WRITE = ("hr_admin",)
HR_READ = ("hr_admin", "hr_viewer")
PRIVACY_THRESHOLD = 10  # en dessous de 10 salariés, le détail par catégorie est masqué
MAX_CSV_BYTES = 200_000
MAX_CSV_ROWS = 2000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class EmployerError(Exception):
    def __init__(self, code: str, message: str, status: int = 409, extra: dict | None = None):
        super().__init__(message)
        self.code, self.message, self.status, self.extra = code, message, status, extra or {}


def organization_for(db: Session, principal, roles: tuple[str, ...]) -> Organization:
    ids = principal.scope_ids("organization", roles)
    if not ids:
        readable = principal.scope_ids("organization", HR_READ)
        raise EmployerError("forbidden", "Action réservée aux administrateurs RH." if readable
                            else "Ce compte n'est rattaché à aucune organisation.", 403)
    return db.get(Organization, ids[0])


def _tz(db: Session, org: Organization) -> ZoneInfo:
    return ZoneInfo(db.scalar(select(Market.timezone).where(Market.id == org.market_id)))


def current_period(db: Session, org: Organization, now: datetime | None = None) -> date:
    return (now or datetime.now(UTC)).astimezone(_tz(db, org)).date().replace(day=1)


def contract_of(db: Session, org: Organization) -> EmployerContract | None:
    return db.scalar(select(EmployerContract).where(EmployerContract.organization_id == org.id))


# ---------------------------------------------------------------- salariés


def normalize_email(email: str) -> str:
    return email.strip().lower()


def invite(db: Session, org: Organization, *, email: str, first_name: str, last_name: str,
           by: uuid.UUID | None) -> Employee:
    email = normalize_email(email)
    if not EMAIL_RE.match(email):
        raise EmployerError("invalid_email", "Adresse e-mail invalide.", 422)
    row_id = db.scalar(
        insert(Employee)
        .values(id=uuid.uuid4(), organization_id=org.id, email=email, first_name=first_name.strip()[:80],
                last_name=last_name.strip()[:80], status="invited", invited_by=by, is_demo=False)
        .on_conflict_do_nothing(index_elements=["organization_id", "email"])
        .returning(Employee.id)
    )
    if row_id is None:
        raise EmployerError("duplicate", "Ce salarié fait déjà partie de l'équipe.", 409)
    # Envoi de l'e-mail d'invitation : après commit, par l'outbox (aucun service e-mail branché à ce stade).
    emit(db, "employee", row_id, "employee.invited", {"organization_id": str(org.id)})
    return db.get(Employee, row_id)


_ALIASES = {
    "email": ("email", "e-mail", "mail", "courriel", "adresse e-mail", "adresse email"),
    "last_name": ("nom", "last name", "lastname", "nom de famille"),
    "first_name": ("prénom", "prenom", "first name", "firstname"),
}


@dataclass
class CsvRow:
    line: int
    email: str
    last_name: str
    first_name: str
    problem: str | None = None
    detail: str | None = None


@dataclass
class CsvPreview:
    headers: list[str]
    mapping: dict[str, str]
    valid: list[CsvRow] = field(default_factory=list)
    errors: list[CsvRow] = field(default_factory=list)


def preview_csv(db: Session, org: Organization, content: str, mapping: dict[str, str] | None = None) -> CsvPreview:
    if len(content.encode()) > MAX_CSV_BYTES:
        raise EmployerError("too_large", "Fichier trop volumineux (200 Ko maximum).", 422)
    content = content.lstrip("﻿")
    try:
        dialect = csv.Sniffer().sniff(content[:2000], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(content), dialect)
    try:
        headers = [h.strip() for h in next(reader)]
    except StopIteration:
        raise EmployerError("empty", "Le fichier est vide.", 422) from None
    lower = {h.lower(): h for h in headers}
    if mapping is None:
        mapping = {}
        for key, aliases in _ALIASES.items():
            found = next((lower[a] for a in aliases if a in lower), None)
            if found:
                mapping[key] = found
    if "email" not in mapping or mapping["email"] not in headers:
        raise EmployerError("missing_email_column", "Indiquez la colonne qui contient l'adresse e-mail.", 422,
                            {"headers": headers})
    index = {k: headers.index(v) for k, v in mapping.items() if v in headers}
    existing = set(db.scalars(select(Employee.email).where(Employee.organization_id == org.id)))
    seen: set[str] = set()
    out = CsvPreview(headers=headers, mapping=mapping)
    for n, values in enumerate(reader, start=2):
        if n - 1 > MAX_CSV_ROWS:
            raise EmployerError("too_many_rows", f"{MAX_CSV_ROWS} lignes maximum par import.", 422)
        if not any(v.strip() for v in values):
            continue

        def get(key: str) -> str:
            i = index.get(key)
            return values[i].strip() if i is not None and i < len(values) else ""

        row = CsvRow(line=n, email=normalize_email(get("email")), last_name=get("last_name")[:80],
                     first_name=get("first_name")[:80])
        if not EMAIL_RE.match(row.email):
            row.problem, row.detail = "invalid_email", "Adresse e-mail incomplète ou invalide."
        elif row.email in existing:
            row.problem, row.detail = "duplicate", "Cet e-mail existe déjà dans l'équipe."
        elif row.email in seen:
            row.problem, row.detail = "duplicate", "E-mail présent plusieurs fois dans le fichier."
        (out.errors if row.problem else out.valid).append(row)
        seen.add(row.email)
    return out


def import_csv(db: Session, org: Organization, content: str, mapping: dict[str, str] | None,
               by: uuid.UUID | None) -> int:
    """Revalide le fichier côté serveur et n'insère que les lignes valides (idempotent)."""
    preview = preview_csv(db, org, content, mapping)
    created = 0
    for row in preview.valid:
        row_id = db.scalar(
            insert(Employee)
            .values(id=uuid.uuid4(), organization_id=org.id, email=row.email, first_name=row.first_name,
                    last_name=row.last_name, status="invited", invited_by=by, is_demo=False)
            .on_conflict_do_nothing(index_elements=["organization_id", "email"])
            .returning(Employee.id)
        )
        if row_id:
            created += 1
            emit(db, "employee", row_id, "employee.invited", {"organization_id": str(org.id)})
    return created


def set_status(db: Session, org: Organization, employee_id: uuid.UUID, action: str, now: datetime | None = None) -> Employee:
    """Suspendre ou retirer arrête les allocations FUTURES ; les crédits déjà attribués restent acquis."""
    now = now or datetime.now(UTC)
    emp = db.scalar(select(Employee).where(Employee.id == employee_id, Employee.organization_id == org.id)
                    .with_for_update())
    if emp is None:
        raise EmployerError("employee_not_found", "Salarié introuvable.", 404)
    if action == "suspend":
        if emp.status == "removed":
            raise EmployerError("invalid_state", "Ce salarié a été retiré.", 409)
        emp.status, emp.suspended_at = "suspended", now
    elif action == "reactivate":
        if emp.status != "suspended":
            raise EmployerError("invalid_state", "Seul un salarié suspendu peut être réactivé.", 409)
        emp.status, emp.suspended_at = ("active" if emp.user_id else "invited"), None
    elif action == "remove":
        emp.status = "removed"
    else:
        raise EmployerError("invalid_action", "Action inconnue.", 422)
    db.flush()
    return emp


# ---------------------------------------------------------------- côté salarié


def my_invitations(db: Session, user: User) -> list[tuple[Employee, Organization]]:
    return list(db.execute(
        select(Employee, Organization).join(Organization, Organization.id == Employee.organization_id)
        .where(Employee.email == normalize_email(user.email), Employee.status == "invited")
    ).all())


def accept(db: Session, user: User, employee_id: uuid.UUID, now: datetime | None = None) -> Employee:
    now = now or datetime.now(UTC)
    emp = db.scalar(select(Employee).where(Employee.id == employee_id).with_for_update())
    # L'invitation est liée à l'adresse e-mail : un autre compte ne peut pas l'accepter.
    if emp is None or emp.email != normalize_email(user.email):
        raise EmployerError("invitation_not_found", "Invitation introuvable.", 404)
    if emp.status != "invited":
        raise EmployerError("invalid_state", "Cette invitation n'est plus valable.", 409)
    emp.user_id, emp.status, emp.joined_at = user.id, "active", now
    db.flush()
    org = db.get(Organization, emp.organization_id)
    allocate_period(db, org, current_period(db, org, now), now)
    return emp


# ---------------------------------------------------------------- politique de budget


def policy_for(db: Session, org: Organization, period: date) -> BudgetPolicy | None:
    return db.scalar(select(BudgetPolicy).where(BudgetPolicy.organization_id == org.id,
                                                BudgetPolicy.effective_from <= period)
                     .order_by(BudgetPolicy.effective_from.desc()).limit(1))


def set_policy(db: Session, org: Organization, *, credits_per_month: int, eligible_categories: list[str] | None,
               credit_validity_days: int, effective_from: date, by: uuid.UUID | None,
               now: datetime | None = None) -> BudgetPolicy:
    period = current_period(db, org, now)
    if effective_from.day != 1:
        raise EmployerError("invalid_date", "Une politique démarre le 1er d'un mois.", 422)
    if effective_from < period:
        raise EmployerError("past_period", "Impossible de modifier un mois passé.", 422)
    if effective_from == period and db.scalar(select(func.count()).select_from(EmployerAllocation).where(
            EmployerAllocation.organization_id == org.id, EmployerAllocation.period == period)):
        raise EmployerError("period_started", "Les crédits de ce mois ont déjà été attribués : la nouvelle "
                            "politique s'appliquera au mois prochain.", 409)
    if eligible_categories is not None:
        known = set(db.scalars(select(Category.slug)))
        if not eligible_categories or not set(eligible_categories) <= known:
            raise EmployerError("invalid_categories", "Catégories inconnues ou vides.", 422)
    db.execute(
        insert(BudgetPolicy)
        .values(id=uuid.uuid4(), organization_id=org.id, credits_per_month=credits_per_month,
                eligible_categories=eligible_categories, credit_validity_days=credit_validity_days,
                effective_from=effective_from, created_by=by)
        .on_conflict_do_update(
            index_elements=["organization_id", "effective_from"],
            set_={"credits_per_month": credits_per_month, "eligible_categories": eligible_categories,
                  "credit_validity_days": credit_validity_days, "created_by": by},
        )
    )
    db.flush()
    return db.scalar(select(BudgetPolicy).where(BudgetPolicy.organization_id == org.id,
                                                BudgetPolicy.effective_from == effective_from))


# ---------------------------------------------------------------- financement


def balance_minor(db: Session, org: Organization) -> int:
    """Financement disponible = factures payées − coûts déjà alloués."""
    paid = db.scalar(select(func.coalesce(func.sum(EmployerInvoice.amount_minor), 0)).where(
        EmployerInvoice.organization_id == org.id, EmployerInvoice.status == "paid"))
    used = db.scalar(select(func.coalesce(func.sum(EmployerAllocation.cost_minor), 0)).where(
        EmployerAllocation.organization_id == org.id))
    return int(paid) - int(used)


def request_funding(db: Session, org: Organization, *, amount_minor: int, by: uuid.UUID | None,
                    now: datetime | None = None) -> EmployerInvoice:
    now = now or datetime.now(UTC)
    contract = contract_of(db, org)
    if contract is None or contract.status in ("ended", "suspended"):
        raise EmployerError("contract_inactive", "Le contrat de votre organisation ne permet pas de financement.", 409)
    if amount_minor % contract.credit_price_minor:
        raise EmployerError("invalid_amount", "Le montant doit correspondre à un nombre entier de crédits.", 422)
    today = now.astimezone(_tz(db, org)).date()
    n = db.scalar(text("SELECT nextval('employer_invoice_seq')"))
    invoice = EmployerInvoice(
        organization_id=org.id, reference=f"FAC-{today:%Y-%m}-{n:04d}", label="Financement employeur",
        amount_minor=amount_minor, currency=contract.currency, issued_on=today,
        due_on=today + timedelta(days=contract.payment_terms_days), status="pending", created_by=by,
    )
    db.add(invoice)
    db.flush()
    emit(db, "employer_invoice", invoice.id, "employer_invoice.issued", {"reference": invoice.reference})
    return invoice


def confirm_payment(db: Session, invoice_id: uuid.UUID, *, by: uuid.UUID | None, now: datetime | None = None) -> EmployerInvoice:
    """Virement reçu, confirmé par l'équipe XPASS (rapprochement bancaire). Puis allocation du mois en cours."""
    now = now or datetime.now(UTC)
    invoice = db.scalar(select(EmployerInvoice).where(EmployerInvoice.id == invoice_id).with_for_update())
    if invoice is None:
        raise EmployerError("invoice_not_found", "Facture introuvable.", 404)
    if invoice.status != "pending":
        raise EmployerError("invalid_state", "Cette facture n'est pas en attente.", 409)
    invoice.status, invoice.paid_at, invoice.confirmed_by = "paid", now, by
    post_money(db, kind="employer_funding", memo=invoice.reference, ref_type="employer_invoice", ref_id=invoice.id,
               lines=[("bank_cash", invoice.amount_minor, invoice.currency, None),
                      ("employer_prepaid", -invoice.amount_minor, invoice.currency, None)])
    org = db.get(Organization, invoice.organization_id)
    allocate_period(db, org, current_period(db, org, now), now)
    return invoice


# ---------------------------------------------------------------- allocations


@dataclass
class AllocationRun:
    allocated: int = 0
    skipped_no_funds: int = 0


def allocate_period(db: Session, org: Organization, period: date, now: datetime | None = None) -> AllocationRun:
    """Attribue les crédits du mois aux salariés actifs qui ne les ont pas encore reçus (idempotent)."""
    now = now or datetime.now(UTC)
    run = AllocationRun()
    # Verrou de l'organisation : deux exécutions concurrentes ne peuvent pas dépasser le financement.
    db.execute(select(Organization.id).where(Organization.id == org.id).with_for_update())
    contract = contract_of(db, org)
    market = db.get(Market, org.market_id)
    if contract is None or contract.status != "active" or contract.currency != market.currency:
        return run
    policy = policy_for(db, org, period)
    if policy is None:
        return run
    employees = db.scalars(
        select(Employee).where(
            Employee.organization_id == org.id, Employee.status == "active", Employee.user_id.is_not(None),
            ~select(EmployerAllocation.id).where(EmployerAllocation.employee_id == Employee.id,
                                                 EmployerAllocation.period == period).exists(),
        ).order_by(Employee.joined_at)
    ).all()
    available = balance_minor(db, org)
    cost = policy.credits_per_month * contract.credit_price_minor
    for emp in employees:
        if available < cost:
            run.skipped_no_funds += 1
            continue
        wallet = wallet_service.get_or_create_wallet(db, emp.user_id, org.market_id, lock=True)
        lot = wallet_service.grant(
            db, wallet, source="employer", amount=policy.credits_per_month,
            label=f"Avantage {org.name} · {period:%m/%Y}", origin_type="employer_allocation",
            origin_ref=f"{emp.id}:{period.isoformat()}",
            expires_at=now + timedelta(days=policy.credit_validity_days),
            eligible_categories=policy.eligible_categories,
        )
        allocation = EmployerAllocation(organization_id=org.id, employee_id=emp.id, policy_id=policy.id, period=period,
                                        credits=policy.credits_per_month, cost_minor=cost, currency=contract.currency,
                                        credit_lot_id=lot.id)
        db.add(allocation)
        db.flush()  # unicité (salarié, mois)
        post_money(db, kind="employer_allocation", memo=f"Allocation {period:%m/%Y}", ref_type="employer_allocation",
                   ref_id=allocation.id, lines=[("employer_prepaid", cost, contract.currency, None),
                                                ("customer_deferred", -cost, contract.currency, None)])
        available -= cost
        run.allocated += 1
    if run.skipped_no_funds:
        emit(db, "organization", org.id, "employer.funding_insufficient",
             {"period": period.isoformat(), "employees": run.skipped_no_funds})
    return run


def allocate_all(db: Session, now: datetime | None = None) -> int:
    total = 0
    org_ids = db.scalars(select(EmployerContract.organization_id).where(EmployerContract.status == "active")).all()
    for org_id in org_ids:
        org = db.get(Organization, org_id)
        total += allocate_period(db, org, current_period(db, org, now), now).allocated
    return total


# ---------------------------------------------------------------- rapports agrégés


def report(db: Session, org: Organization, period: date) -> dict:
    end = (period.replace(day=28) + timedelta(days=4)).replace(day=1)
    contract = contract_of(db, org)
    counts = dict(db.execute(select(Employee.status, func.count()).where(Employee.organization_id == org.id)
                             .group_by(Employee.status)).all())
    eligible = counts.get("invited", 0) + counts.get("active", 0)
    active = counts.get("active", 0)
    policy = policy_for(db, org, period)
    alloc = db.execute(select(func.coalesce(func.sum(EmployerAllocation.credits), 0),
                              func.coalesce(func.sum(EmployerAllocation.cost_minor), 0))
                       .where(EmployerAllocation.organization_id == org.id, EmployerAllocation.period == period)).one()
    lots = select(EmployerAllocation.credit_lot_id).where(EmployerAllocation.organization_id == org.id)
    usage = db.execute(
        select(Category.slug, Category.name, func.sum(CreditJournalLine.amount), func.count(func.distinct(Booking.user_id)))
        .select_from(CreditJournalLine)
        .join(CreditJournal, CreditJournal.id == CreditJournalLine.journal_id)
        .join(Booking, Booking.id == CreditJournal.booking_id)
        .join(Location, Location.id == Booking.location_id)
        .join(Subcategory, Subcategory.id == Location.subcategory_id)
        .join(Category, Category.id == Subcategory.category_id)
        .where(CreditJournalLine.lot_id.in_(lots), CreditJournalLine.account == "consumed",
               CreditJournal.kind == "capture", CreditJournal.created_at >= period, CreditJournal.created_at < end)
        .group_by(Category.slug, Category.name)
    ).all()
    consumed = sum(int(c) for _, _, c, _ in usage)
    # Crédits employeur perdus en annulations tardives et absences (total agrégé, aucun détail par salarié).
    penalty = int(db.scalar(
        select(func.coalesce(func.sum(CreditJournalLine.amount), 0))
        .select_from(CreditJournalLine)
        .join(CreditJournal, CreditJournal.id == CreditJournalLine.journal_id)
        .join(Booking, Booking.id == CreditJournal.booking_id)
        .where(CreditJournalLine.lot_id.in_(lots), CreditJournalLine.account == "consumed",
               CreditJournal.kind == "capture", CreditJournal.created_at >= period, CreditJournal.created_at < end,
               Booking.status.in_(("cancelled", "no_show")))
    ))
    categories = []
    for slug, name, credits, people in usage:
        # Confidentialité : moins de PRIVACY_THRESHOLD salariés -> aucun détail.
        masked = people < PRIVACY_THRESHOLD
        categories.append({"slug": slug, "name": name, "masked": masked,
                           "share": None if masked or not consumed else round(int(credits) * 100 / consumed),
                           "employees": None if masked else int(people)})
    price = contract.credit_price_minor if contract else 0
    return {
        "period": period,
        "currency": contract.currency if contract else None,
        "eligible": eligible,
        "active": active,
        "activation_rate": round(active * 100 / eligible) if eligible else 0,
        "monthly_budget_minor": (policy.credits_per_month * active * price) if policy else 0,
        "allocated_credits": int(alloc[0]),
        "allocated_cost_minor": int(alloc[1]),
        "consumed_credits": consumed,
        "consumed_cost_minor": consumed * price,
        "penalty_credits": penalty,
        "balance_minor": balance_minor(db, org),
        "categories": sorted(categories, key=lambda c: c["slug"]),
        "privacy_threshold": PRIVACY_THRESHOLD,
    }
