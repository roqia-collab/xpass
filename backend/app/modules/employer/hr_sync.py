"""Import automatique des salariés depuis le logiciel RH de l'entreprise (API de synchronisation).

Le logiciel RH envoie la liste complète des salariés éligibles avec une clé d'API propre à l'entreprise
(`Authorization: Bearer xph_…`). La clé n'est montrée qu'une fois ; XPASS n'en garde que l'empreinte SHA-256.
Aucune donnée de visite ne remonte vers l'entreprise par cette API.
"""
import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.employer import service as s
from app.modules.employer.models import Employee, OrganizationApiKey
from app.modules.identity.models import Organization

PREFIX = "xph_"
MAX_ROWS = 5000


def _digest(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def issue_key(db: Session, org: Organization, *, label: str, by: uuid.UUID) -> tuple[OrganizationApiKey, str]:
    if db.scalar(select(OrganizationApiKey.id).where(OrganizationApiKey.organization_id == org.id,
                                                     OrganizationApiKey.revoked_at.is_(None)).limit(5).offset(4)):
        raise s.EmployerError("too_many_keys", "5 clés actives au maximum : révoquez-en une.", 409)
    raw = PREFIX + secrets.token_urlsafe(32)
    key = OrganizationApiKey(organization_id=org.id, label=(label.strip() or "Logiciel RH")[:80], prefix=raw[:12],
                             key_hash=_digest(raw), created_by=by)
    db.add(key)
    db.flush()
    return key, raw


def revoke_key(db: Session, org: Organization, key_id: uuid.UUID) -> None:
    key = db.get(OrganizationApiKey, key_id)
    if key is None or key.organization_id != org.id:
        raise s.EmployerError("key_not_found", "Clé introuvable.", 404)
    key.revoked_at = key.revoked_at or datetime.now(UTC)


def authenticate(db: Session, raw: str | None) -> Organization | None:
    if not raw or not raw.startswith(PREFIX):
        return None
    key = db.scalar(select(OrganizationApiKey).where(OrganizationApiKey.key_hash == _digest(raw),
                                                     OrganizationApiKey.revoked_at.is_(None)))
    if key is None:
        return None
    key.last_used_at = datetime.now(UTC)
    return db.get(Organization, key.organization_id)


@dataclass
class SyncRow:
    email: str
    first_name: str
    last_name: str


@dataclass
class SyncResult:
    invited: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: int = 0
    removed: list[str] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)


def sync(db: Session, org: Organization, rows: list[SyncRow], *, remove_missing: bool, dry_run: bool) -> SyncResult:
    """Ajoute les nouveaux salariés (invitation), met à jour les noms, retire ceux absents si demandé."""
    if len(rows) > MAX_ROWS:
        raise s.EmployerError("too_many_rows", f"{MAX_ROWS} salariés au maximum par envoi.", 422)
    result = SyncResult()
    existing = {e.email: e for e in db.scalars(select(Employee).where(Employee.organization_id == org.id))}
    seen: set[str] = set()
    for r in rows:
        email = s.normalize_email(r.email)
        if not s.EMAIL_RE.match(email):
            result.skipped.append({"email": r.email, "reason": "adresse invalide"})
            continue
        if email in seen:
            result.skipped.append({"email": email, "reason": "doublon dans l'envoi"})
            continue
        seen.add(email)
        emp = existing.get(email)
        if emp is None:
            result.invited.append(email)
            if not dry_run:
                s.invite(db, org, email=email, first_name=r.first_name, last_name=r.last_name, by=None)
        elif emp.status == "removed":
            result.skipped.append({"email": email, "reason": "retiré : à réinviter depuis le portail"})
        elif (emp.first_name, emp.last_name) != (r.first_name.strip()[:80], r.last_name.strip()[:80]):
            result.updated.append(email)
            if not dry_run:
                emp.first_name, emp.last_name = r.first_name.strip()[:80], r.last_name.strip()[:80]
        else:
            result.unchanged += 1
    if remove_missing:
        for email, emp in existing.items():
            if email not in seen and emp.status != "removed" and not emp.is_demo:
                result.removed.append(email)
                if not dry_run:
                    s.set_status(db, org, emp.id, "remove")
    db.flush()
    return result
