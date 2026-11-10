"""Briques transverses : idempotence des commandes et outbox transactionnelle."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, SmallInteger, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin


class IdempotencyKey(IdMixin, Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("user_id", "scope", "key"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    scope: Mapped[str] = mapped_column(String(80))
    key: Mapped[str] = mapped_column(String(100))
    # Empreinte SHA-256 du corps : même clé + corps différent = erreur.
    request_hash: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int] = mapped_column(SmallInteger)
    response_body: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxEvent(IdMixin, Base):
    """Événement écrit dans la même transaction que l'effet métier, diffusé après commit par Celery."""

    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_pending", "created_at", postgresql_where=text("published_at IS NULL")),)
    aggregate_type: Mapped[str] = mapped_column(String(40))
    aggregate_id: Mapped[uuid.UUID] = mapped_column()
    event_type: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500))
