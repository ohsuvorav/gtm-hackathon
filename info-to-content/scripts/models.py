"""Pydantic contracts for every persisted InfoToContent artifact."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvidenceRef(StrictModel):
    source_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    speaker: str | None = None
    timestamp: str | None = None


class ContentInsight(StrictModel):
    id: str = Field(min_length=1)
    type: Literal[
        "question",
        "pain",
        "objection",
        "use_case",
        "customer_language",
    ]
    statement: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)
    occurrence_count: int = Field(default=1, ge=1)


class WebsiteDNA(StrictModel):
    company_description: str = Field(min_length=1)
    target_audience: str | None = None
    products: list[str] = Field(default_factory=list)
    tone: list[str] = Field(default_factory=list)
    existing_topics: list[str] = Field(default_factory=list)


class SurferContext(StrictModel):
    available: bool = True
    target_keyword: str | None = None
    recommended_terms: list[str] = Field(default_factory=list)
    target_word_count: int | None = Field(default=None, ge=1)
    content_score: float | None = Field(default=None, ge=0, le=100)
    unavailable_reason: str | None = None

    @model_validator(mode="after")
    def check_availability(self) -> "SurferContext":
        if self.available and self.unavailable_reason:
            raise ValueError("available Surfer context cannot have unavailable_reason")
        if not self.available and not self.unavailable_reason:
            raise ValueError("unavailable Surfer context requires unavailable_reason")
        return self


class ContentOpportunity(StrictModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    target_audience: str = Field(min_length=1)
    insight_ids: list[str] = Field(min_length=1)
    evidence_strength: float = Field(ge=0, le=1)
    why_now: str = Field(min_length=1)


class ContentBrief(StrictModel):
    title: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    supporting_insight_ids: list[str] = Field(min_length=1)
    key_customer_pains_questions: list[str] = Field(min_length=1)
    required_points: list[str] = Field(min_length=1)
    seo_terms: list[str] = Field(default_factory=list)
    target_word_count: int | None = Field(default=None, ge=1)
    surfer_available: bool = False
