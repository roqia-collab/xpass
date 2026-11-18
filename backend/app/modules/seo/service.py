"""Rapports SEO : réception, décisions humaines, application des balises et retour arrière.

Règles :
- Rien n'est appliqué sans validation explicite d'un administrateur, puis une confirmation d'application.
- Une application ne modifie qu'UNE balise d'UNE page (table seo_page_overrides) ; l'ancienne valeur est gardée
  dans seo_changes, avec l'auteur et la date, et peut être restaurée tant qu'aucune modification plus récente
  n'a été appliquée à la même balise de la même page.
- Les pages publiques des portails lisent ces valeurs (GET /api/v1/seo/pages) et retombent sur leurs valeurs
  par défaut si aucune n'est enregistrée.
"""
import json
import re
import threading
import time
import uuid
from collections import deque
from datetime import UTC, datetime
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.ops.service import audit
from app.modules.seo.models import SeoChange, SeoPageOverride, SeoRecommendation, SeoReport
from app.modules.seo.schemas import ReportIn

SITE_HOSTS = ("xpass.fr", "www.xpass.fr")

# Pages publiques de xpass.fr dont les balises sont branchées sur ces valeurs (voir apps/portals/src/lib/seo.ts).
PAGES = ("/", "/demande", "/devenir-partenaire", "/legal/cgu", "/legal/partenaires", "/legal/confidentialite",
         "/legal/mentions-legales")

# Catégorie reçue -> balise gérée. Les autres catégories (robots.txt, sitemap, contenu, performance…) peuvent
# être validées ou rejetées, mais s'appliquent à la main : elles ne touchent pas qu'une page.
CATEGORY_FIELD = {
    "title": "title",
    "meta_title": "title",
    "meta_description": "description",
    "description": "description",
    "canonical": "canonical",
    "og_title": "og_title",
    "open_graph_title": "og_title",
    "og_description": "og_description",
    "open_graph_description": "og_description",
    "og_image": "og_image",
    "open_graph_image": "og_image",
    "twitter_card": "twitter_card",
    "twitter_title": "twitter_title",
    "twitter_description": "twitter_description",
    "twitter_image": "twitter_image",
    "robots": "robots",
    "meta_robots": "robots",
    "json_ld": "json_ld",
    "jsonld": "json_ld",
    "structured_data": "json_ld",
}
FIELDS = tuple(sorted(set(CATEGORY_FIELD.values())))
_ROBOTS_TOKENS = {"index", "noindex", "follow", "nofollow", "noarchive", "nosnippet", "noimageindex", "notranslate",
                  "all", "none"}
_ROBOTS_PARAM = re.compile(r"^(max-snippet:-?\d+|max-image-preview:(none|standard|large)|max-video-preview:-?\d+)$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class SeoError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


# ---------------------------------------------------------------- limite de requêtes (réception)


class RateLimiter:
    """Fenêtre glissante d'une heure par émetteur, en mémoire (l'API tourne en un seul processus uvicorn)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: float = 3600.0) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


# ---------------------------------------------------------------- pages et valeurs


def page_path(url: str) -> str | None:
    """Chemin sur xpass.fr, ou None si l'adresse est hors du site."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if (parts.hostname or "").lower() not in SITE_HOSTS:
        return None
    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    return path[:300]


def field_for(category: str) -> str | None:
    return CATEGORY_FIELD.get(category)


def _https_url(value: str, *, own_site: bool) -> str:
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname:
        raise SeoError("invalid_value", "L'adresse doit commencer par https://.", 422)
    if own_site and parts.hostname.lower() not in SITE_HOSTS:
        raise SeoError("invalid_value", "L'adresse canonique doit rester sur xpass.fr.", 422)
    return value


def clean_value(field: str, raw: str | None) -> str:
    """Valide et normalise la valeur d'une balise. Refuse tout ce qui ne correspond pas au type attendu."""
    value = (raw or "").strip()
    if not value:
        raise SeoError("invalid_value", "La nouvelle valeur est vide.", 422)
    if field != "json_ld" and ("\n" in value or "\r" in value):
        raise SeoError("invalid_value", "La valeur doit tenir sur une seule ligne.", 422)
    if _CONTROL.search(value):
        raise SeoError("invalid_value", "La valeur contient des caractères de contrôle.", 422)
    limits = {"title": 120, "og_title": 200, "twitter_title": 200, "description": 400, "og_description": 400,
              "twitter_description": 400, "canonical": 500, "og_image": 500, "twitter_image": 500, "robots": 200,
              "twitter_card": 40, "json_ld": 20_000}
    if len(value) > limits[field]:
        raise SeoError("invalid_value", f"Valeur trop longue ({limits[field]} caractères maximum).", 422)
    if field == "canonical":
        return _https_url(value, own_site=True)
    if field in ("og_image", "twitter_image"):
        return _https_url(value, own_site=False)
    if field == "twitter_card":
        if value not in ("summary", "summary_large_image"):
            raise SeoError("invalid_value", "twitter:card doit valoir summary ou summary_large_image.", 422)
        return value
    if field == "robots":
        tokens = [t.strip().lower() for t in value.split(",") if t.strip()]
        if not tokens or any(t not in _ROBOTS_TOKENS and not _ROBOTS_PARAM.match(t) for t in tokens):
            raise SeoError("invalid_value", "Directive robots inconnue (ex. « index, follow »).", 422)
        return ", ".join(tokens)
    if field == "json_ld":
        try:
            data = json.loads(value)
        except ValueError as exc:
            raise SeoError("invalid_value", "Le JSON-LD n'est pas un JSON valide.", 422) from exc
        if not isinstance(data, (dict, list)) or not data:
            raise SeoError("invalid_value", "Le JSON-LD doit être un objet ou une liste d'objets.", 422)
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return value


# ---------------------------------------------------------------- réception


def ingest(db: Session, data: ReportIn, *, source: str) -> SeoReport:
    if db.scalar(select(SeoReport.id).where(SeoReport.report_id == data.reportId)) is not None:
        raise SeoError("duplicate_report", "Ce rapport (reportId) a déjà été reçu.", 409)
    report = SeoReport(
        report_id=data.reportId, site_url=data.siteUrl, source=source[:100], report_created_at=data.createdAt,
        summary=data.summary, overall_score=data.overallScore, markdown_report=data.markdownReport,
        payload=data.model_dump(mode="json"), status="new",
    )
    db.add(report)
    try:
        db.flush()
    except IntegrityError as exc:  # deux envois simultanés du même rapport
        db.rollback()
        raise SeoError("duplicate_report", "Ce rapport (reportId) a déjà été reçu.", 409) from exc
    for r in data.recommendations:
        db.add(SeoRecommendation(
            report_pk=report.id, external_id=r.id, priority=r.priority, category=r.category, page_url=r.pageUrl,
            page_path=page_path(r.pageUrl), issue=r.issue, current_value=r.currentValue,
            suggested_value=r.suggestedValue, reason=r.reason, sender_status=r.status, status="new",
        ))
    db.flush()
    return report


# ---------------------------------------------------------------- statuts


def refresh_report_status(db: Session, report: SeoReport) -> None:
    statuses = list(db.scalars(select(SeoRecommendation.status).where(SeoRecommendation.report_pk == report.id)))
    if not statuses or all(s == "new" for s in statuses):
        report.status = "new"
    elif "new" in statuses:
        report.status = "in_review"
    elif "validated" in statuses:
        report.status = "validated"
    elif any(s in ("applied", "reverted") for s in statuses):
        report.status = "applied"
    else:
        report.status = "rejected"


def _recommendation(db: Session, reco_id: uuid.UUID) -> SeoRecommendation:
    reco = db.scalar(select(SeoRecommendation).where(SeoRecommendation.id == reco_id).with_for_update())
    if reco is None:
        raise SeoError("not_found", "Recommandation introuvable.", 404)
    return reco


def applicable(reco: SeoRecommendation) -> tuple[bool, str | None]:
    """Peut-on appliquer automatiquement ? Sinon, pourquoi."""
    if field_for(reco.category) is None:
        return False, "Catégorie appliquée à la main (elle ne concerne pas une seule balise d'une page)."
    if reco.page_path is None:
        return False, "La page n'est pas sur xpass.fr."
    if reco.page_path not in PAGES:
        return False, "Cette page n'a pas de balises gérées depuis l'administration."
    return True, None


def proposed_value(reco: SeoRecommendation) -> str | None:
    return reco.edited_value if reco.edited_value is not None else reco.suggested_value


def _audit(db: Session, reco: SeoRecommendation, by: uuid.UUID, action: str, reason: str | None = None,
           details: dict | None = None) -> None:
    audit(db, actor_kind="operator", actor_user_id=by, action=f"seo.{action}", object_type="seo_recommendation",
          object_id=reco.id, object_label=f"{reco.category} · {reco.page_path or reco.page_url}", reason=reason,
          details=details or {})


# ---------------------------------------------------------------- décisions


def validate(db: Session, reco_id: uuid.UUID, *, by: uuid.UUID, note: str | None = None,
             value: str | None = None) -> SeoRecommendation:
    """Valide (éventuellement avec une valeur modifiée). Ne publie rien : l'application est une étape à part."""
    reco = _recommendation(db, reco_id)
    if reco.status == "applied":
        raise SeoError("already_applied", "Recommandation déjà appliquée : annulez-la d'abord.", 409)
    field = field_for(reco.category)
    if value is not None:
        reco.edited_value = clean_value(field, value) if field else value.strip()
    elif field and applicable(reco)[0]:
        clean_value(field, proposed_value(reco))  # refuse dès la validation une valeur inapplicable
    reco.status = "validated"
    reco.decision_note = (note or "").strip() or None
    reco.decided_by, reco.decided_at = by, datetime.now(UTC)
    _audit(db, reco, by, "validate", reco.decision_note,
           {"edited": reco.edited_value is not None, "value": (proposed_value(reco) or "")[:500]})
    refresh_report_status(db, db.get(SeoReport, reco.report_pk))
    return reco


def reject(db: Session, reco_id: uuid.UUID, *, by: uuid.UUID, note: str) -> SeoRecommendation:
    note = (note or "").strip()
    if len(note) < 5:
        raise SeoError("reason_required", "Indiquez le motif du rejet (5 caractères minimum).", 422)
    reco = _recommendation(db, reco_id)
    if reco.status == "applied":
        raise SeoError("already_applied", "Recommandation déjà appliquée : annulez-la d'abord.", 409)
    reco.status = "rejected"
    reco.decision_note = note
    reco.decided_by, reco.decided_at = by, datetime.now(UTC)
    _audit(db, reco, by, "reject", note)
    refresh_report_status(db, db.get(SeoReport, reco.report_pk))
    return reco


def current_override(db: Session, path: str, field: str, *, lock: bool = False) -> SeoPageOverride | None:
    stmt = select(SeoPageOverride).where(SeoPageOverride.page_path == path, SeoPageOverride.field == field)
    return db.scalar(stmt.with_for_update() if lock else stmt)


def apply(db: Session, reco_id: uuid.UUID, *, by: uuid.UUID) -> SeoChange:
    reco = _recommendation(db, reco_id)
    if reco.status != "validated":
        raise SeoError("not_validated", "Seule une recommandation validée peut être appliquée.", 409)
    ok, why = applicable(reco)
    if not ok:
        raise SeoError("not_applicable", why or "Application impossible.", 422)
    field = field_for(reco.category)
    new_value = clean_value(field, proposed_value(reco))
    override = current_override(db, reco.page_path, field, lock=True)
    old_value = override.value if override else None
    if old_value == new_value:
        raise SeoError("no_change", "Cette valeur est déjà en place sur la page.", 409)
    if override is None:
        db.add(SeoPageOverride(page_path=reco.page_path, field=field, value=new_value, updated_by=by))
    else:
        override.value, override.updated_by = new_value, by
    change = SeoChange(recommendation_id=reco.id, page_path=reco.page_path, field=field, old_value=old_value,
                       new_value=new_value, applied_by=by,
                       details={"category": reco.category, "page_url": reco.page_url})
    db.add(change)
    reco.status = "applied"
    reco.applied_by, reco.applied_at = by, datetime.now(UTC)
    reco.last_error = reco.last_error_at = None
    db.flush()
    _audit(db, reco, by, "apply", None, {"field": field, "from": (old_value or "")[:500], "to": new_value[:500]})
    refresh_report_status(db, db.get(SeoReport, reco.report_pk))
    return change


def record_error(db: Session, reco_id: uuid.UUID, message: str) -> None:
    reco = db.get(SeoRecommendation, reco_id)
    if reco is not None:
        reco.last_error, reco.last_error_at = message[:2000], datetime.now(UTC)


def revert(db: Session, change_id: uuid.UUID, *, by: uuid.UUID) -> SeoChange:
    change = db.scalar(select(SeoChange).where(SeoChange.id == change_id).with_for_update())
    if change is None:
        raise SeoError("not_found", "Modification introuvable.", 404)
    if change.reverted_at is not None:
        raise SeoError("already_reverted", "Cette modification a déjà été annulée.", 409)
    latest = db.scalar(select(SeoChange.id).where(
        SeoChange.page_path == change.page_path, SeoChange.field == change.field, SeoChange.reverted_at.is_(None),
    ).order_by(SeoChange.applied_at.desc()).limit(1))
    if latest != change.id:
        raise SeoError("newer_change", "Une modification plus récente existe sur cette balise : annulez-la d'abord.", 409)
    override = current_override(db, change.page_path, change.field, lock=True)
    if change.old_value is None:
        if override is not None:
            db.delete(override)
    elif override is None:
        db.add(SeoPageOverride(page_path=change.page_path, field=change.field, value=change.old_value, updated_by=by))
    else:
        override.value, override.updated_by = change.old_value, by
    change.reverted_by, change.reverted_at = by, datetime.now(UTC)
    if change.recommendation_id:
        reco = _recommendation(db, change.recommendation_id)
        reco.status = "reverted"
        _audit(db, reco, by, "revert", None, {"field": change.field, "restored": (change.old_value or "")[:500]})
        refresh_report_status(db, db.get(SeoReport, reco.report_pk))
    db.flush()
    return change


# ---------------------------------------------------------------- lecture


def overrides_for(db: Session, path: str) -> dict[str, str]:
    rows = db.execute(select(SeoPageOverride.field, SeoPageOverride.value).where(SeoPageOverride.page_path == path))
    return {field: value for field, value in rows}


def counts_by_report(db: Session, report_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not report_ids:
        return {}
    rows = db.execute(select(SeoRecommendation.report_pk, func.count()).where(
        SeoRecommendation.report_pk.in_(report_ids)).group_by(SeoRecommendation.report_pk))
    return {k: int(v) for k, v in rows}
