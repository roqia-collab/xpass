"""SEO : réception des rapports externes, validation par l'administration, application des balises.

- POST /admin/seo/reports : réservé à l'outil SEO, authentifié par le secret partagé SEO_REPORT_WEBHOOK_SECRET
  (en-tête « Authorization: Bearer … »). Le secret n'est jamais journalisé ni renvoyé.
- Tout le reste de /admin/seo exige un compte administrateur XPASS (platform_admin).
- GET /seo/pages : lecture publique des balises en vigueur d'une page (utilisée par les portails).
"""
import hmac
import json
import logging
import uuid
from datetime import date, datetime, time, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from app.api.deps import CurrentPrincipal, DbSession
from app.core.config import get_settings
from app.modules.identity.models import User
from app.modules.ops import service as ops
from app.modules.seo import service as seo
from app.modules.seo.models import REPORT_STATUS, SeoChange, SeoRecommendation, SeoReport
from app.modules.seo.schemas import ReportIn

router = APIRouter(tags=["seo"])
log = logging.getLogger("xpass.seo")
PARIS = ZoneInfo("Europe/Paris")


def _err(status: int, code: str, message: str, headers: dict | None = None) -> HTTPException:
    return HTTPException(status, {"code": code, "message": message}, headers=headers)


def _admin(principal) -> None:
    try:
        ops.require(principal, ops.ADMIN)
    except ops.OpsError as exc:
        raise _err(exc.status, exc.code, exc.message) from exc


def _run(db, fn):
    try:
        result = fn()
        db.commit()
        return result
    except seo.SeoError as exc:
        db.rollback()
        raise _err(exc.status, exc.code, exc.message) from exc


# ---------------------------------------------------------------- réception (outil SEO externe)


@router.post("/admin/seo/reports", status_code=201)
async def receive_report(request: Request, db: DbSession,
                         authorization: Annotated[str | None, Header()] = None) -> dict:
    settings = get_settings()
    source = request.client.host if request.client else "inconnue"
    if not seo.limiter.allow(f"seo:{source}", settings.seo_report_rate_per_hour):
        raise _err(429, "too_many_requests", "Trop d'envois : réessayez plus tard.", {"Retry-After": "3600"})
    secret = settings.seo_report_webhook_secret
    if not secret:
        raise _err(503, "seo_reports_disabled", "Réception des rapports SEO non configurée.")
    token = authorization[7:].strip() if authorization and authorization[:7].lower() == "bearer " else ""
    if not token or not hmac.compare_digest(token.encode(), secret.encode()):
        log.warning("Rapport SEO refusé : authentification invalide (source %s).", source)
        raise _err(401, "unauthorized", "Jeton invalide.", {"WWW-Authenticate": "Bearer"})

    limit = settings.seo_report_max_bytes
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise _err(413, "payload_too_large", f"Rapport trop volumineux ({limit} octets maximum).")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            raise _err(413, "payload_too_large", f"Rapport trop volumineux ({limit} octets maximum).")
    try:
        raw = json.loads(bytes(body).decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise _err(400, "invalid_json", "Le corps de la requête n'est pas un JSON valide.") from exc
    try:
        data = ReportIn.model_validate(raw)
    except ValidationError as exc:
        errors = [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in exc.errors()[:20]]
        raise HTTPException(422, {"code": "invalid_report", "message": "Rapport SEO invalide.", "errors": errors}) from exc

    report = _run(db, lambda: seo.ingest(db, data, source=source))
    log.info("Rapport SEO reçu : %s (%d recommandations).", report.report_id, len(data.recommendations))
    return {"id": str(report.id), "reportId": report.report_id, "status": report.status,
            "recommendations": len(data.recommendations)}


# ---------------------------------------------------------------- consultation (admin)


class ReportRow(BaseModel):
    id: uuid.UUID
    report_id: str
    site_url: str
    report_created_at: datetime
    received_at: datetime
    status: str
    overall_score: int | None
    recommendation_count: int
    summary: str


class RecommendationOut(BaseModel):
    id: uuid.UUID
    external_id: str
    priority: str
    category: str
    field: str | None
    page_url: str
    page_path: str | None
    issue: str
    current_value: str | None
    suggested_value: str | None
    edited_value: str | None
    proposed_value: str | None
    live_value: str | None  # valeur enregistrée aujourd'hui pour cette balise (None = valeur par défaut du code)
    reason: str
    status: str
    applicable: bool
    not_applicable_reason: str | None
    decision_note: str | None
    decided_by_name: str | None
    decided_at: datetime | None
    applied_by_name: str | None
    applied_at: datetime | None
    last_error: str | None
    last_error_at: datetime | None
    active_change_id: uuid.UUID | None


class ReportDetail(ReportRow):
    source: str
    markdown_report: str
    recommendations: list[RecommendationOut]


def _names(db, ids) -> dict[uuid.UUID, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return dict(db.execute(select(User.id, User.display_name).where(User.id.in_(ids))).all())


def _row(r: SeoReport, count: int) -> ReportRow:
    return ReportRow(id=r.id, report_id=r.report_id, site_url=r.site_url, report_created_at=r.report_created_at,
                     received_at=r.received_at, status=r.status, overall_score=r.overall_score,
                     recommendation_count=count, summary=r.summary[:500])


@router.get("/admin/seo/reports", response_model=list[ReportRow])
def list_reports(principal: CurrentPrincipal, db: DbSession,
                 status: Annotated[Literal[REPORT_STATUS] | None, Query()] = None,  # type: ignore[valid-type]
                 date_from: date | None = None, date_to: date | None = None,
                 limit: Annotated[int, Query(ge=1, le=200)] = 100) -> list[ReportRow]:
    _admin(principal)
    stmt = select(SeoReport).order_by(SeoReport.report_created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(SeoReport.status == status)
    if date_from:
        stmt = stmt.where(SeoReport.report_created_at >= datetime.combine(date_from, time.min, PARIS))
    if date_to:
        stmt = stmt.where(SeoReport.report_created_at < datetime.combine(date_to + timedelta(days=1), time.min, PARIS))
    reports = db.scalars(stmt).all()
    counts = seo.counts_by_report(db, [r.id for r in reports])
    return [_row(r, counts.get(r.id, 0)) for r in reports]


def _report(db, report_id: uuid.UUID) -> SeoReport:
    report = db.get(SeoReport, report_id)
    if report is None:
        raise _err(404, "not_found", "Rapport introuvable.")
    return report


@router.get("/admin/seo/reports/{report_id}", response_model=ReportDetail)
def get_report(report_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> ReportDetail:
    _admin(principal)
    report = _report(db, report_id)
    recos = db.scalars(select(SeoRecommendation).where(SeoRecommendation.report_pk == report.id)
                       .order_by(SeoRecommendation.external_id)).all()
    names = _names(db, [x for r in recos for x in (r.decided_by, r.applied_by)])
    active = dict(db.execute(select(SeoChange.recommendation_id, SeoChange.id).where(
        SeoChange.recommendation_id.in_([r.id for r in recos]), SeoChange.reverted_at.is_(None))).all())
    out = []
    for r in recos:
        field = seo.field_for(r.category)
        ok, why = seo.applicable(r)
        live = seo.current_override(db, r.page_path, field) if ok else None
        out.append(RecommendationOut(
            id=r.id, external_id=r.external_id, priority=r.priority, category=r.category, field=field,
            page_url=r.page_url, page_path=r.page_path, issue=r.issue, current_value=r.current_value,
            suggested_value=r.suggested_value, edited_value=r.edited_value, proposed_value=seo.proposed_value(r),
            live_value=live.value if live else None, reason=r.reason, status=r.status, applicable=ok,
            not_applicable_reason=why, decision_note=r.decision_note, decided_by_name=names.get(r.decided_by),
            decided_at=r.decided_at, applied_by_name=names.get(r.applied_by), applied_at=r.applied_at,
            last_error=r.last_error, last_error_at=r.last_error_at, active_change_id=active.get(r.id),
        ))
    base = _row(report, len(recos))
    return ReportDetail(**base.model_dump(), source=report.source, markdown_report=report.markdown_report,
                        recommendations=out)


def markdown_filename(report: SeoReport) -> str:
    return f"rapport-seo-xpass-{report.report_created_at.astimezone(PARIS).date().isoformat()}.md"


@router.get("/admin/seo/reports/{report_id}/markdown")
def download_markdown(report_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> Response:
    _admin(principal)
    report = _report(db, report_id)
    return Response(report.markdown_report, media_type="text/markdown; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="{markdown_filename(report)}"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    })


# ---------------------------------------------------------------- décisions (admin)


class ValidateIn(BaseModel):
    note: str | None = Field(None, max_length=2000)
    value: str | None = Field(None, max_length=20_000)  # « Modifier avant validation »


class RejectIn(BaseModel):
    note: str = Field(max_length=2000)


class ApplyIn(BaseModel):
    confirm: Literal[True]


@router.post("/admin/seo/recommendations/{reco_id}/validate")
def validate_recommendation(reco_id: uuid.UUID, body: ValidateIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _admin(principal)
    reco = _run(db, lambda: seo.validate(db, reco_id, by=principal.user.id, note=body.note, value=body.value))
    return {"ok": True, "status": reco.status}


@router.post("/admin/seo/recommendations/{reco_id}/reject")
def reject_recommendation(reco_id: uuid.UUID, body: RejectIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _admin(principal)
    reco = _run(db, lambda: seo.reject(db, reco_id, by=principal.user.id, note=body.note))
    return {"ok": True, "status": reco.status}


@router.post("/admin/seo/recommendations/{reco_id}/apply")
def apply_recommendation(reco_id: uuid.UUID, body: ApplyIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _admin(principal)
    try:
        change = seo.apply(db, reco_id, by=principal.user.id)
        db.commit()
    except seo.SeoError as exc:
        db.rollback()
        if exc.status != 404:  # l'erreur reste visible sur la recommandation
            seo.record_error(db, reco_id, exc.message)
            db.commit()
        raise _err(exc.status, exc.code, exc.message) from exc
    return {"ok": True, "change_id": str(change.id), "page_path": change.page_path, "field": change.field}


# ---------------------------------------------------------------- historique et retour arrière (admin)


class ChangeOut(BaseModel):
    id: uuid.UUID
    recommendation_id: uuid.UUID | None
    report_id: uuid.UUID | None
    page_path: str
    field: str
    old_value: str | None
    new_value: str
    applied_by_name: str | None
    applied_at: datetime
    reverted_by_name: str | None
    reverted_at: datetime | None
    revertible: bool


@router.get("/admin/seo/history", response_model=list[ChangeOut])
def history(principal: CurrentPrincipal, db: DbSession, path: Annotated[str | None, Query(max_length=300)] = None,
            limit: Annotated[int, Query(ge=1, le=500)] = 200) -> list[ChangeOut]:
    _admin(principal)
    stmt = select(SeoChange, SeoRecommendation.report_pk).outerjoin(
        SeoRecommendation, SeoRecommendation.id == SeoChange.recommendation_id,
    ).order_by(SeoChange.applied_at.desc()).limit(limit)
    if path:
        stmt = stmt.where(SeoChange.page_path == path)
    rows = db.execute(stmt).all()
    names = _names(db, [x for c, _ in rows for x in (c.applied_by, c.reverted_by)])
    latest: dict[tuple[str, str], uuid.UUID] = {}
    for c, _ in db.execute(select(SeoChange, SeoChange.id).where(SeoChange.reverted_at.is_(None))
                           .order_by(SeoChange.applied_at)).all():
        latest[(c.page_path, c.field)] = c.id
    return [ChangeOut(id=c.id, recommendation_id=c.recommendation_id, report_id=report_pk, page_path=c.page_path,
                      field=c.field, old_value=c.old_value, new_value=c.new_value,
                      applied_by_name=names.get(c.applied_by), applied_at=c.applied_at,
                      reverted_by_name=names.get(c.reverted_by), reverted_at=c.reverted_at,
                      revertible=c.reverted_at is None and latest.get((c.page_path, c.field)) == c.id)
            for c, report_pk in rows]


@router.post("/admin/seo/changes/{change_id}/revert")
def revert_change(change_id: uuid.UUID, body: ApplyIn, principal: CurrentPrincipal, db: DbSession) -> dict:
    _admin(principal)
    change = _run(db, lambda: seo.revert(db, change_id, by=principal.user.id))
    return {"ok": True, "page_path": change.page_path, "field": change.field}


# ---------------------------------------------------------------- lecture publique (portails)


@router.get("/seo/pages")
def page_overrides(db: DbSession, path: Annotated[str, Query(min_length=1, max_length=300)]) -> dict:
    """Balises en vigueur d'une page publique. Aucune donnée interne : seulement les valeurs publiées."""
    if path not in seo.PAGES:
        return {"path": path, "values": {}}
    return {"path": path, "values": seo.overrides_for(db, path)}
