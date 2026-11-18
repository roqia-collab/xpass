"""Rapports SEO, recommandations, balises appliquées par page et historique des modifications."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin

# Statut d'un rapport, recalculé à chaque décision sur ses recommandations.
REPORT_STATUS = ("new", "in_review", "validated", "applied", "rejected")
# Statut d'une recommandation.
RECO_STATUS = ("new", "validated", "rejected", "applied", "reverted")
PRIORITY = ("critical", "high", "medium", "low")


class SeoReport(IdMixin, Base):
    __tablename__ = "seo_reports"
    __table_args__ = (
        UniqueConstraint("report_id", name="uq_seo_reports_report_id"),
        Index("ix_seo_reports_report_created", "report_created_at"),
        Index("ix_seo_reports_status", "status"),
    )
    report_id: Mapped[str] = mapped_column(String(100))  # identifiant donné par l'émetteur (anti-doublon)
    site_url: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(100))  # adresse IP / nom de l'émetteur
    report_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str] = mapped_column(Text)
    overall_score: Mapped[int | None] = mapped_column(Integer)
    markdown_report: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB)  # contenu complet reçu
    status: Mapped[str] = mapped_column(Enum(*REPORT_STATUS, name="seo_report_status", native_enum=False,
                                             create_constraint=True, length=16), default="new")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SeoRecommendation(IdMixin, Base):
    __tablename__ = "seo_recommendations"
    __table_args__ = (
        UniqueConstraint("report_pk", "external_id", name="uq_seo_recommendations_report_external"),
        Index("ix_seo_recommendations_status", "status"),
    )
    report_pk: Mapped[uuid.UUID] = mapped_column(ForeignKey("seo_reports.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(100))
    priority: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(40))
    page_url: Mapped[str] = mapped_column(String(500))
    page_path: Mapped[str | None] = mapped_column(String(300))  # chemin sur xpass.fr, None si hors site
    issue: Mapped[str] = mapped_column(Text)
    current_value: Mapped[str | None] = mapped_column(Text)  # valeur constatée par l'émetteur
    suggested_value: Mapped[str | None] = mapped_column(Text)
    edited_value: Mapped[str | None] = mapped_column(Text)  # « Modifier avant validation »
    reason: Mapped[str] = mapped_column(Text, default="")
    sender_status: Mapped[str | None] = mapped_column(String(40))  # statut fourni par l'émetteur (informatif)
    status: Mapped[str] = mapped_column(Enum(*RECO_STATUS, name="seo_reco_status", native_enum=False,
                                             create_constraint=True, length=16), default="new")
    decision_note: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SeoPageOverride(IdMixin, Base):
    """Valeur en vigueur d'une balise sur une page. Absente = valeur par défaut du code des portails."""

    __tablename__ = "seo_page_overrides"
    __table_args__ = (UniqueConstraint("page_path", "field", name="uq_seo_page_overrides_page_field"),)
    page_path: Mapped[str] = mapped_column(String(300), index=True)
    field: Mapped[str] = mapped_column(String(40))
    value: Mapped[str] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SeoChange(IdMixin, Base):
    """Historique : une ligne par application, avec l'ancienne valeur pour le retour arrière."""

    __tablename__ = "seo_changes"
    __table_args__ = (Index("ix_seo_changes_page_field", "page_path", "field"),)
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seo_recommendations.id"), index=True)
    page_path: Mapped[str] = mapped_column(String(300))
    field: Mapped[str] = mapped_column(String(40))
    old_value: Mapped[str | None] = mapped_column(Text)  # None = valeur par défaut du code
    new_value: Mapped[str] = mapped_column(Text)
    applied_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reverted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
