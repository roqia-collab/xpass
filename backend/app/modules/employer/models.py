"""Avantage salarié : contrat employeur, salariés, politiques de budget, financements et allocations.

Règles :
- l'argent (unités mineures + devise du marché) et les crédits (entiers) ne sont jamais confondus ;
- les allocations n'ont lieu que si le contrat est ACTIF et que le financement reçu les couvre ;
- une seule allocation par salarié et par mois ; les crédits déjà attribués restent acquis ;
- les RH ne voient que des données agrégées, jamais les visites individuelles.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin


def _enum(*values: str, name: str, length: int = 16) -> Enum:
    return Enum(*values, name=name, native_enum=False, create_constraint=True, length=length)


CONTRACT_STATUS = ("draft", "active", "suspended", "ended")


class EmployerContract(IdMixin, Base):
    """Conditions contractuelles d'une organisation (validées par XPASS ; administration au lot 7)."""

    __tablename__ = "employer_contracts"
    __table_args__ = (
        Index("uq_employer_contracts_org", "organization_id", unique=True),
        CheckConstraint("credit_price_minor > 0", name="price_positive"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    status: Mapped[str] = mapped_column(_enum(*CONTRACT_STATUS, name="contract_status"))
    # Prix facturé à l'entreprise pour un crédit alloué, dans la devise du marché.
    credit_price_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=7)
    starts_on: Mapped[date] = mapped_column(Date)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


EMPLOYEE_STATUS = ("invited", "active", "suspended", "removed")


class Employee(IdMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        Index("uq_employees_org_email", "organization_id", "email", unique=True),
        Index("uq_employees_org_user", "organization_id", "user_id", unique=True,
              postgresql_where=text("user_id IS NOT NULL")),
        CheckConstraint("email = lower(email)", name="email_lower"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    # Renseigné quand le salarié accepte l'invitation avec un compte dont l'e-mail correspond.
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(_enum(*EMPLOYEE_STATUS, name="employee_status"))
    invited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class BudgetPolicy(IdMixin, Base):
    """Politique de budget versionnée : une nouvelle ligne par changement, effective au 1er d'un mois."""

    __tablename__ = "budget_policies"
    __table_args__ = (
        Index("uq_budget_policies_org_from", "organization_id", "effective_from", unique=True),
        CheckConstraint("credits_per_month > 0", name="credits_positive"),
        CheckConstraint("extract(day from effective_from) = 1", name="first_of_month"),
        CheckConstraint("credit_validity_days BETWEEN 7 AND 366", name="validity_range"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    credits_per_month: Mapped[int] = mapped_column(Integer)
    # NULL = tous les univers.
    eligible_categories: Mapped[list[str] | None] = mapped_column(ARRAY(String(32)))
    credit_validity_days: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[date] = mapped_column(Date)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


INVOICE_STATUS = ("pending", "paid", "void")


class EmployerInvoice(IdMixin, Base):
    """Facture de financement : son paiement (confirmé par XPASS) alimente le solde prépayé."""

    __tablename__ = "employer_invoices"
    __table_args__ = (
        Index("uq_employer_invoices_reference", "reference", unique=True),
        CheckConstraint("amount_minor > 0", name="amount_positive"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    reference: Mapped[str] = mapped_column(String(24))
    label: Mapped[str] = mapped_column(String(120))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    issued_on: Mapped[date] = mapped_column(Date)
    due_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(_enum(*INVOICE_STATUS, name="employer_invoice_status"))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class EmployerAllocation(IdMixin, Base):
    """Crédits attribués à un salarié pour un mois. Unique par (salarié, mois)."""

    __tablename__ = "employer_allocations"
    __table_args__ = (
        Index("uq_employer_allocations_period", "employee_id", "period", unique=True),
        CheckConstraint("credits > 0 AND cost_minor > 0", name="positive"),
        CheckConstraint("extract(day from period) = 1", name="first_of_month"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"))
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("budget_policies.id"))
    period: Mapped[date] = mapped_column(Date)
    credits: Mapped[int] = mapped_column(Integer)
    cost_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    credit_lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("credit_lots.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrganizationApiKey(IdMixin, Base):
    """Clé d'API de synchronisation RH : seule l'empreinte SHA-256 est conservée (clé montrée une fois)."""

    __tablename__ = "organization_api_keys"
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    label: Mapped[str] = mapped_column(String(80))
    prefix: Mapped[str] = mapped_column(String(12))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
