"""Format JSON reçu de l'outil SEO externe (champs en camelCase, comme envoyés).

Validation stricte : champs inconnus refusés, longueurs bornées, nombre de recommandations limité.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_RECOMMENDATIONS = 300
_ID = r"^[A-Za-z0-9][A-Za-z0-9._:\-]{0,99}$"
PRIORITIES = ("critical", "high", "medium", "low")


class RecommendationIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(pattern=_ID)
    priority: str = Field(max_length=16)
    category: str = Field(min_length=1, max_length=40)
    pageUrl: str = Field(min_length=1, max_length=500)
    issue: str = Field(min_length=1, max_length=5_000)
    currentValue: str | None = Field(None, max_length=20_000)
    suggestedValue: str | None = Field(None, max_length=20_000)
    reason: str = Field("", max_length=5_000)
    status: str | None = Field(None, max_length=40)

    @field_validator("priority")
    @classmethod
    def _priority(cls, v: str) -> str:
        v = v.lower()
        if v not in PRIORITIES:
            raise ValueError(f"priority doit valoir {', '.join(PRIORITIES)}")
        return v

    @field_validator("category")
    @classmethod
    def _category(cls, v: str) -> str:
        v = v.strip().lower().replace("-", "_").replace(" ", "_")
        if not all(c.isalnum() or c in "_:" for c in v):
            raise ValueError("catégorie invalide")
        return v

    @field_validator("pageUrl")
    @classmethod
    def _url(cls, v: str) -> str:
        if not (v.startswith("https://") or v.startswith("http://")):
            raise ValueError("pageUrl doit être une adresse http(s)")
        return v


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reportId: str = Field(pattern=_ID)
    siteUrl: str = Field(min_length=1, max_length=300)
    createdAt: datetime
    summary: str = Field("", max_length=20_000)
    overallScore: int | None = Field(None, ge=0, le=100)
    recommendations: list[RecommendationIn] = Field(default_factory=list, max_length=MAX_RECOMMENDATIONS)
    markdownReport: str = Field("", max_length=800_000)

    @field_validator("siteUrl")
    @classmethod
    def _site(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("siteUrl doit être une adresse https")
        return v

    @field_validator("createdAt")
    @classmethod
    def _aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("createdAt doit préciser le fuseau horaire (ex. 2026-11-17T06:00:00Z)")
        return v

    @field_validator("recommendations")
    @classmethod
    def _unique_ids(cls, v: list[RecommendationIn]) -> list[RecommendationIn]:
        ids = [r.id for r in v]
        if len(ids) != len(set(ids)):
            raise ValueError("chaque recommandation doit avoir un id unique dans le rapport")
        return v
