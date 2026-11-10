import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.platform.models import IdempotencyKey, OutboxEvent


def emit(db: Session, aggregate_type: str, aggregate_id: uuid.UUID, event_type: str, payload: dict) -> None:
    """Ajoute un événement à l'outbox dans la transaction courante (diffusé après commit)."""
    db.add(OutboxEvent(aggregate_type=aggregate_type, aggregate_id=aggregate_id, event_type=event_type, payload=payload))


def body_hash(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


class IdempotencyMismatch(Exception):
    """Même clé réutilisée avec un corps différent."""


@dataclass
class IdempotentResult:
    status: int
    body: dict
    replayed: bool


def run_idempotent(
    db: Session,
    *,
    user_id: uuid.UUID,
    scope: str,
    key: str,
    body: dict,
    action: Callable[[], tuple[int, dict]],
) -> IdempotentResult:
    """Exécute `action` une seule fois par (utilisateur, portée, clé).

    L'effet métier et l'enregistrement de la clé sont validés dans LA MÊME transaction :
    soit les deux existent, soit aucun. Une requête concurrente avec la même clé échoue
    sur la contrainte d'unicité puis rejoue la réponse enregistrée.
    """
    digest = body_hash(body)

    def stored() -> IdempotencyKey | None:
        return db.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.user_id == user_id, IdempotencyKey.scope == scope, IdempotencyKey.key == key
            )
        )

    def replay(row: IdempotencyKey) -> IdempotentResult:
        if row.request_hash != digest:
            raise IdempotencyMismatch()
        return IdempotentResult(row.response_status, row.response_body, True)

    existing = stored()
    if existing is not None:
        db.rollback()
        return replay(existing)

    try:
        status, response = action()
        db.add(
            IdempotencyKey(
                user_id=user_id, scope=scope, key=key, request_hash=digest, response_status=status,
                response_body=json.loads(json.dumps(response, default=str)),
            )
        )
        db.commit()
        return IdempotentResult(status, response, False)
    except IntegrityError:
        db.rollback()
        existing = stored()
        if existing is not None:
            return replay(existing)
        raise
