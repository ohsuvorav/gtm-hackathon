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
    type: Literal["question", "pain", "objection", "use_case", "customer_language"]
    statement: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)
    occurrence_count: int = Field(default=1, ge=1)


class SourceDocument(StrictModel):
    source_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    provider: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    transcript_path: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrieved_at: str | None = None


class WebsiteDNA(StrictModel):
    company_description: str = Field(min_length=1)
    target_audience: str | None = None
    products: list[str] = Field(default_factory=list)
    tone: list[str] = Field(default_factory=list)
    existing_topics: list[str] = Field(default_factory=list)
    business_type: str | None = None
    industry: str | None = None
    competitors: list[str] = Field(default_factory=list)
    topics_to_cover: list[str] = Field(default_factory=list)
    problem_solved: str | None = None
    source: Literal["surferseo"] = "surferseo"
    workspace_id: int = Field(ge=1)
    brand_id: str = Field(min_length=1)
    brand_url: str | None = None
    gathering_data_status: str | None = None


class VoiceContext(StrictModel):
    available: bool
    voice_id: str | None = None
    name: str | None = None
    reference_text: str | None = None
    unavailable_reason: str | None = None

    @model_validator(mode="after")
    def check_availability(self) -> "VoiceContext":
        if self.available:
            if not self.reference_text:
                raise ValueError("available voice context requires reference_text")
            if self.unavailable_reason:
                raise ValueError("available voice context cannot have unavailable_reason")
        elif not self.unavailable_reason:
            raise ValueError("unavailable voice context requires unavailable_reason")
        return self


class KeywordGap(StrictModel):
    id: str = Field(min_length=1)
    recommendation_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    topic: str | None = None
    target_keyword: str = ""
    location: str | None = None
    search_volume: int | None = Field(default=None, ge=0)
    difficulty: float | None = Field(default=None, ge=0)
    surfer_score: float | None = None
    reasons: list[str] = Field(default_factory=list)
    content_editor_id: str | None = None
    icp_relevant: bool
    relevance_rationale: str = Field(min_length=1)
    rejected_for: list[str] = Field(default_factory=list)


class KeywordGapReport(StrictModel):
    source: Literal["surferseo-recommendations-mcp"]
    workspace_id: int = Field(ge=1)
    retrieved_at: str | None = None
    viable: list[KeywordGap] = Field(default_factory=list)
    rejected: list[KeywordGap] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_partitions(self) -> "KeywordGapReport":
        ids = [item.id for item in self.viable + self.rejected]
        if len(ids) != len(set(ids)):
            raise ValueError("keyword gap IDs must be unique")
        if any(item.rejected_for for item in self.viable):
            raise ValueError("viable keyword gaps cannot have rejection reasons")
        if any(not item.rejected_for for item in self.rejected):
            raise ValueError("rejected keyword gaps require rejection reasons")
        return self


class OpportunityMatch(StrictModel):
    source_id: str = Field(min_length=1)
    matched: bool
    keyword_gap_id: str | None = None
    recommendation_id: str | None = None
    target_keyword: str | None = None
    insight_ids: list[str] = Field(default_factory=list)
    evidence_quote: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    rationale: str | None = None
    opportunity_title: str | None = None
    angle: str | None = None
    target_audience: str | None = None
    no_match_reason: str | None = None

    @model_validator(mode="after")
    def check_match(self) -> "OpportunityMatch":
        matched_fields = {
            "keyword_gap_id": self.keyword_gap_id,
            "recommendation_id": self.recommendation_id,
            "target_keyword": self.target_keyword,
            "evidence_quote": self.evidence_quote,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "opportunity_title": self.opportunity_title,
            "angle": self.angle,
            "target_audience": self.target_audience,
        }
        if self.matched:
            missing = [name for name, value in matched_fields.items() if value is None or value == ""]
            if not self.insight_ids:
                missing.append("insight_ids")
            if missing:
                raise ValueError(f"matched opportunity is missing: {', '.join(missing)}")
            if self.no_match_reason:
                raise ValueError("matched opportunity cannot have no_match_reason")
        else:
            if not self.no_match_reason:
                raise ValueError("no-match result requires no_match_reason")
            populated = [name for name, value in matched_fields.items() if value is not None]
            if populated or self.insight_ids:
                raise ValueError("no-match result cannot contain match fields")
        return self


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
    source_id: str = Field(min_length=1)
    keyword_gap_id: str = Field(min_length=1)
    target_keyword: str = Field(min_length=1)
    title: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    target_audience: str = Field(min_length=1)
    insight_ids: list[str] = Field(min_length=1)
    evidence_strength: float = Field(ge=0, le=1)
    match_confidence: float = Field(ge=0, le=1)
    why_now: str = Field(min_length=1)


class ContentBrief(StrictModel):
    source_id: str = Field(min_length=1)
    keyword_gap_id: str = Field(min_length=1)
    target_keyword: str = Field(min_length=1)
    title: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    supporting_insight_ids: list[str] = Field(min_length=1)
    key_customer_pains_questions: list[str] = Field(min_length=1)
    required_points: list[str] = Field(min_length=1)
    seo_terms: list[str] = Field(default_factory=list)
    target_word_count: int | None = Field(default=None, ge=1)
    surfer_available: bool = True
