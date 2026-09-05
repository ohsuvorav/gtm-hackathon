"""Validate one call-to-gap match and create at most one content opportunity."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import dump_models, fail, load_json_input, normalized_text, stable_id, validate_many
from models import (
    ContentInsight,
    ContentOpportunity,
    KeywordGapReport,
    OpportunityMatch,
    SourceDocument,
)
from state import artifact_path, load_optional, read_json, require_state_v2, resolve_state_dir, write_json

MIN_MATCH_CONFIDENCE = 0.60


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path)
    return parser


def remove_downstream(state_dir: Path, opportunities: list[ContentOpportunity]) -> None:
    for opportunity in opportunities:
        for path in (
            state_dir / "briefs" / f"{opportunity.id}.json",
            state_dir / "drafts" / f"{opportunity.id}.md",
            state_dir / "surfer" / f"{opportunity.id}.json",
        ):
            path.unlink(missing_ok=True)


def main() -> int:
    args = build_parser().parse_args()
    try:
        state_dir = resolve_state_dir(args.state_dir)
        require_state_v2(state_dir)
        candidate = OpportunityMatch.model_validate(load_json_input(args.candidate))
        candidate = candidate.model_copy(update={"insight_ids": list(dict.fromkeys(candidate.insight_ids))})
        source = SourceDocument.model_validate(
            read_json(state_dir / "sources" / f"{candidate.source_id}.json")
        )
        transcript = (state_dir / source.transcript_path).read_text(encoding="utf-8")
        insights = validate_many(
            ContentInsight,
            read_json(artifact_path(state_dir, "insights")),
        )
        gaps = KeywordGapReport.model_validate(read_json(artifact_path(state_dir, "keyword_gaps")))
        viable_by_id = {item.id: item for item in gaps.viable}
        current = validate_many(
            ContentOpportunity,
            load_optional(artifact_path(state_dir, "opportunities"), []),
        )
        previous = [item for item in current if item.source_id == candidate.source_id]
        retained = [item for item in current if item.source_id != candidate.source_id]

        if candidate.matched and candidate.confidence is not None and candidate.confidence < MIN_MATCH_CONFIDENCE:
            candidate = OpportunityMatch(
                source_id=candidate.source_id,
                matched=False,
                no_match_reason=(
                    f"Best match confidence {candidate.confidence:.2f} is below "
                    f"the {MIN_MATCH_CONFIDENCE:.2f} threshold"
                ),
            )

        opportunity: ContentOpportunity | None = None
        if candidate.matched:
            gap = viable_by_id.get(candidate.keyword_gap_id or "")
            if gap is None:
                raise ValueError("Match must reference a viable keyword gap")
            if candidate.recommendation_id != gap.recommendation_id:
                raise ValueError("Match recommendation_id does not match the keyword gap")
            if normalized_text(candidate.target_keyword or "") != normalized_text(gap.target_keyword):
                raise ValueError("Match target_keyword does not match the keyword gap")
            by_id = {item.id: item for item in insights}
            missing = sorted(set(candidate.insight_ids) - set(by_id))
            if missing:
                raise ValueError(f"Match cites unknown insight IDs: {missing}")
            supporting = [by_id[identifier] for identifier in dict.fromkeys(candidate.insight_ids)]
            outside_source = [
                item.id
                for item in supporting
                if not any(evidence.source_id == source.source_id for evidence in item.evidence)
            ]
            if outside_source:
                raise ValueError(f"Match cites insights outside source {source.source_id}: {outside_source}")
            quote_key = normalized_text(candidate.evidence_quote or "")
            if quote_key not in normalized_text(transcript):
                raise ValueError("Match evidence quote does not occur in the source transcript")
            supporting_quotes = {
                normalized_text(evidence.quote)
                for item in supporting
                for evidence in item.evidence
                if evidence.source_id == source.source_id
            }
            if quote_key not in supporting_quotes:
                raise ValueError("Match evidence quote must belong to a cited insight")
            opportunity = ContentOpportunity(
                id=stable_id(
                    "opp",
                    source.source_id,
                    gap.id,
                    candidate.opportunity_title or "",
                    candidate.angle or "",
                ),
                source_id=source.source_id,
                keyword_gap_id=gap.id,
                target_keyword=gap.target_keyword,
                title=candidate.opportunity_title or "",
                angle=candidate.angle or "",
                target_audience=candidate.target_audience or "",
                insight_ids=[item.id for item in supporting],
                evidence_strength=min(sum(item.occurrence_count for item in supporting) / 10.0, 1.0),
                match_confidence=candidate.confidence or 0,
                why_now=candidate.rationale or "",
            )
            retained.append(opportunity)
            retained.sort(key=lambda item: (item.source_id.casefold(), item.id))

        remove_downstream(state_dir, previous)
        match_path = write_json(
            state_dir / "matches" / f"{source.source_id}.json",
            candidate.model_dump(mode="json"),
        )
        opportunities_path = write_json(
            artifact_path(state_dir, "opportunities"),
            dump_models(retained),
        )
    except (ValueError, OSError) as error:
        fail(str(error))
    if opportunity:
        print(f"Matched [{opportunity.id}] {opportunity.title} at {opportunity.match_confidence:.2f}")
    else:
        print(f"No content match: {candidate.no_match_reason}")
    print(f"Saved match to {match_path}")
    print(f"Saved opportunities to {opportunities_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
