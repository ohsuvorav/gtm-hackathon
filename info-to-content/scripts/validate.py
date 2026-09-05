"""Validate v2 InfoToContent state and its complete evidence chain."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from common import fail, normalized_text, validate_many
from models import (
    ContentBrief,
    ContentInsight,
    ContentOpportunity,
    KeywordGapReport,
    OpportunityMatch,
    SourceDocument,
    SurferContext,
    VoiceContext,
    WebsiteDNA,
)
from state import artifact_path, load_optional, read_json, require_state_v2, resolve_state_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path)
    return parser


def validate_state(state_dir: Path) -> dict[str, int]:
    require_state_v2(state_dir)
    counts = {"sources": 0, "gaps": 0, "insights": 0, "matches": 0, "opportunities": 0, "briefs": 0, "drafts": 0}

    dna = WebsiteDNA.model_validate(read_json(artifact_path(state_dir, "website_dna")))
    VoiceContext.model_validate(read_json(state_dir / "surfer" / "custom_voice.json"))
    raw_brand = read_json(state_dir / "surfer" / "brand_raw.json")
    if not isinstance(raw_brand, dict) or str(raw_brand.get("id")) != dna.brand_id:
        raise ValueError("Website DNA does not match the raw Surfer brand")
    raw_recommendations = read_json(state_dir / "surfer" / "recommendations_raw.json")
    raw_rows = raw_recommendations.get("data") if isinstance(raw_recommendations, dict) else None
    if not isinstance(raw_rows, list):
        raise ValueError("Raw Surfer recommendations have no data array")
    gaps = KeywordGapReport.model_validate(read_json(artifact_path(state_dir, "keyword_gaps")))
    if gaps.workspace_id != dna.workspace_id:
        raise ValueError("Website DNA and keyword gaps use different Surfer workspaces")
    viable_by_id = {item.id: item for item in gaps.viable}
    report_recommendation_ids = {item.recommendation_id for item in gaps.viable + gaps.rejected}
    raw_recommendation_ids = {
        str(item.get("id")) for item in raw_rows if isinstance(item, dict) and item.get("id") is not None
    }
    if report_recommendation_ids != raw_recommendation_ids:
        raise ValueError("Keyword gap report does not cover the raw Surfer recommendations")
    counts["gaps"] = len(gaps.viable)

    sources: dict[str, tuple[SourceDocument, str]] = {}
    for metadata_path in sorted((state_dir / "sources").glob("*.json")):
        source = SourceDocument.model_validate(read_json(metadata_path))
        if source.source_id in sources:
            raise ValueError(f"Duplicate source ID: {source.source_id}")
        if metadata_path.stem != source.source_id or source.transcript_path != f"sources/{source.source_id}.txt":
            raise ValueError(f"Source paths are not canonical: {source.source_id}")
        transcript_path = state_dir / source.transcript_path
        transcript = transcript_path.read_text(encoding="utf-8")
        digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
        if digest != source.content_sha256:
            raise ValueError(f"Source transcript hash changed: {source.source_id}")
        sources[source.source_id] = (source, transcript)
    counts["sources"] = len(sources)

    insights = validate_many(ContentInsight, load_optional(artifact_path(state_dir, "insights"), []))
    by_insight = {item.id: item for item in insights}
    if len(by_insight) != len(insights):
        raise ValueError("Duplicate insight IDs")
    for insight in insights:
        for evidence in insight.evidence:
            if evidence.source_id not in sources:
                raise ValueError(f"Insight {insight.id} cites unknown source {evidence.source_id}")
            transcript = sources[evidence.source_id][1]
            if normalized_text(evidence.quote) not in normalized_text(transcript):
                raise ValueError(f"Insight {insight.id} quote is absent from {evidence.source_id}")
    counts["insights"] = len(insights)

    matches: dict[str, OpportunityMatch] = {}
    for match_path in sorted((state_dir / "matches").glob("*.json")):
        match = OpportunityMatch.model_validate(read_json(match_path))
        if match.source_id not in sources:
            raise ValueError(f"Match cites unknown source: {match.source_id}")
        if match.matched:
            gap = viable_by_id.get(match.keyword_gap_id or "")
            if gap is None or gap.recommendation_id != match.recommendation_id:
                raise ValueError(f"Match {match.source_id} has no viable Surfer gap")
            if normalized_text(gap.target_keyword) != normalized_text(match.target_keyword or ""):
                raise ValueError(f"Match {match.source_id} changed the Surfer keyword")
            if (match.confidence or 0) < 0.60:
                raise ValueError(f"Match {match.source_id} is below the confidence threshold")
            for insight_id in match.insight_ids:
                insight = by_insight.get(insight_id)
                if insight is None or not any(e.source_id == match.source_id for e in insight.evidence):
                    raise ValueError(f"Match {match.source_id} cites unrelated insight {insight_id}")
            quote = normalized_text(match.evidence_quote or "")
            linked_quotes = {
                normalized_text(e.quote)
                for identifier in match.insight_ids
                for e in by_insight[identifier].evidence
                if e.source_id == match.source_id
            }
            if quote not in linked_quotes:
                raise ValueError(f"Match {match.source_id} evidence is not linked to an insight")
        matches[match.source_id] = match
    counts["matches"] = len(matches)

    opportunities = validate_many(
        ContentOpportunity,
        load_optional(artifact_path(state_dir, "opportunities"), []),
    )
    by_opportunity = {item.id: item for item in opportunities}
    if len(by_opportunity) != len(opportunities):
        raise ValueError("Duplicate opportunity IDs")
    if len({item.source_id for item in opportunities}) != len(opportunities):
        raise ValueError("Only one opportunity is allowed per source")
    for opportunity in opportunities:
        match = matches.get(opportunity.source_id)
        gap = viable_by_id.get(opportunity.keyword_gap_id)
        if not match or not match.matched:
            raise ValueError(f"Opportunity {opportunity.id} has no successful match")
        if not gap or match.keyword_gap_id != gap.id:
            raise ValueError(f"Opportunity {opportunity.id} has no viable gap")
        if normalized_text(opportunity.target_keyword) != normalized_text(gap.target_keyword):
            raise ValueError(f"Opportunity {opportunity.id} changed the Surfer keyword")
        if match.confidence != opportunity.match_confidence:
            raise ValueError(f"Opportunity {opportunity.id} confidence is stale")
        if set(opportunity.insight_ids) != set(match.insight_ids):
            raise ValueError(f"Opportunity {opportunity.id} insights differ from its match")
        expected_strength = min(
            sum(by_insight[identifier].occurrence_count for identifier in opportunity.insight_ids) / 10.0,
            1.0,
        )
        if opportunity.evidence_strength != expected_strength:
            raise ValueError(f"Opportunity {opportunity.id} evidence strength is stale")
    counts["opportunities"] = len(opportunities)

    for brief_path in sorted((state_dir / "briefs").glob("*.json")):
        opportunity = by_opportunity.get(brief_path.stem)
        if opportunity is None:
            raise ValueError(f"Brief has no matching opportunity: {brief_path}")
        brief = ContentBrief.model_validate(read_json(brief_path))
        if (
            brief.source_id != opportunity.source_id
            or brief.keyword_gap_id != opportunity.keyword_gap_id
            or normalized_text(brief.target_keyword) != normalized_text(opportunity.target_keyword)
            or brief.title != opportunity.title
            or brief.audience != opportunity.target_audience
            or brief.angle != opportunity.angle
        ):
            raise ValueError(f"Brief {brief_path.stem} changed locked upstream fields")
        if not set(brief.supporting_insight_ids).issubset(opportunity.insight_ids):
            raise ValueError(f"Brief {brief_path.stem} cites unrelated insights")
        surfer = SurferContext.model_validate(read_json(state_dir / "surfer" / brief_path.name))
        if surfer.target_keyword and normalized_text(surfer.target_keyword) != normalized_text(opportunity.target_keyword):
            raise ValueError(f"Brief {brief_path.stem} has mismatched topic Surfer context")
        counts["briefs"] += 1

    for draft_path in sorted((state_dir / "drafts").glob("*.md")):
        if not (state_dir / "briefs" / f"{draft_path.stem}.json").is_file():
            raise ValueError(f"Draft has no matching brief: {draft_path}")
        if not draft_path.read_text(encoding="utf-8").strip().startswith("#"):
            raise ValueError(f"Draft is empty or lacks a Markdown heading: {draft_path}")
        counts["drafts"] += 1
    return counts


def main() -> int:
    args = build_parser().parse_args()
    try:
        counts = validate_state(resolve_state_dir(args.state_dir))
    except (ValueError, OSError) as error:
        fail(str(error))
    print("State valid: " + ", ".join(f"{name}={count}" for name, count in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
