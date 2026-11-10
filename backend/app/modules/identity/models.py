import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin

SCOPE_TYPE = ("platform", "merchant", "organization")
ROLE = ("platform_admin", "platform_operator", "merchant_owner", "merchant_staff", "hr_admin", "hr_viewer")

# Rôles autorisés par type de portée.
ROLE_SCOPES = {
    "platform_admin": "platform",
    "platform_operator": "platform",
    "merchant_owner": "merchant",
    "merchant_staff": "merchant",
    "hr_admin": "organization",
    "hr_viewer": "organization",
}


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(254), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    oidc_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    # Préférences (écran 16).
    locale: Mapped[str] = mapped_column(String(5), default="fr", server_default="fr")
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Suppression demandée : données personnelles effacées, écritures financières conservées (obligations légales).
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")


class Organization(IdMixin, TimestampMixin, Base):
    __tablename__ = "organizations"
    market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("markets.id"))
    name: Mapped[str] = mapped_column(String(160))
    sector_label: Mapped[str | None] = mapped_column(String(120))
    city_label: Mapped[str | None] = mapped_column(String(80))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Membership(IdMixin, TimestampMixin, Base):
    """Rattache un utilisateur à une portée (plateforme, marchand ou organisation) avec un rôle."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "scope_type", "scope_id", "role", name="uq_memberships_scope_role"),
        CheckConstraint(
            "(scope_type = 'platform' AND scope_id IS NULL) OR (scope_type <> 'platform' AND scope_id IS NOT NULL)",
            name="scope_id_shape",
        ),
        CheckConstraint(
            "(role IN ('platform_admin','platform_operator') AND scope_type = 'platform') OR "
            "(role IN ('merchant_owner','merchant_staff') AND scope_type = 'merchant') OR "
            "(role IN ('hr_admin','hr_viewer') AND scope_type = 'organization')",
            name="role_matches_scope",
        ),
        Index("ix_memberships_scope", "scope_type", "scope_id"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scope_type: Mapped[str] = mapped_column(
        Enum(*SCOPE_TYPE, name="scope_type", native_enum=False, create_constraint=True, length=16)
    )
    # Pas de clé étrangère polymorphe : l'intégrité est vérifiée par le service.
    scope_id: Mapped[uuid.UUID | None] = mapped_column()
    role: Mapped[str] = mapped_column(Enum(*ROLE, name="role", native_enum=False, create_constraint=True, length=32))

    user: Mapped[User] = relationship(back_populates="memberships")
