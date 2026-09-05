"""Validate and persist a brief for one automatically matched opportunity."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import fail, load_json_input, unique_strings, validate_many
from models import ContentBrief, ContentInsight, ContentOpportunity, KeywordGapReport, SurferContext
from state import artifact_path, read_json, require_state_v2, resolve_state_dir, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opportunity-id", required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--surfer-context", type=Path)
    parser.add_argument("--state-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        state_dir = resolve_state_dir(args.state_dir)
        require_state_v2(state_dir)
        insights = validate_many(ContentInsight, read_json(artifact_path(state_dir, "insights")))
        insight_ids = {item.id for item in insights}
        opportunities = validate_many(
            ContentOpportunity,
            read_json(artifact_path(state_dir, "opportunities")),
        )
        opportunity = next((item for item in opportunities if item.id == args.opportunity_id), None)
        if opportunity is None:
            raise ValueError(f"Unknown opportunity ID: {args.opportunity_id}")
        gaps = KeywordGapReport.model_validate(read_json(artifact_path(state_dir, "keyword_gaps")))
        gap = next((item for item in gaps.viable if item.id == opportunity.keyword_gap_id), None)
        if gap is None:
            raise ValueError("Opportunity no longer references a viable keyword gap")

        if args.surfer_context:
            surfer = SurferContext.model_validate(load_json_input(args.surfer_context))
            if surfer.target_keyword and surfer.target_keyword.casefold() != gap.target_keyword.casefold():
                raise ValueError("Surfer context keyword does not match the opportunity gap")
            surfer = surfer.model_copy(update={"target_keyword": gap.target_keyword})
        else:
            surfer = SurferContext(available=True, target_keyword=gap.target_keyword)

        payload = load_json_input(args.candidate)
        if not isinstance(payload, dict):
            raise ValueError("Brief candidate must be a JSON object")
        supporting = list(dict.fromkeys(payload.get("supporting_insight_ids") or []))
        missing = sorted(set(supporting) - insight_ids)
        outside_opportunity = sorted(set(supporting) - set(opportunity.insight_ids))
        if missing:
            raise ValueError(f"Brief has unknown supporting insight IDs: {missing}")
        if outside_opportunity:
            raise ValueError(f"Brief cites insights outside the opportunity: {outside_opportunity}")
        payload.update(
            {
                "source_id": opportunity.source_id,
                "keyword_gap_id": gap.id,
                "target_keyword": gap.target_keyword,
                "title": opportunity.title,
                "audience": opportunity.target_audience,
                "angle": opportunity.angle,
                "supporting_insight_ids": supporting,
                "seo_terms": unique_strings(surfer.recommended_terms),
                "target_word_count": surfer.target_word_count if surfer.available else None,
                "surfer_available": surfer.available,
            }
        )
        brief = ContentBrief.model_validate(payload).model_copy(
            update={
                "key_customer_pains_questions": unique_strings(payload["key_customer_pains_questions"]),
                "required_points": unique_strings(payload["required_points"]),
            }
        )
        brief_path = state_dir / "briefs" / f"{opportunity.id}.json"
        surfer_path = state_dir / "surfer" / f"{opportunity.id}.json"
        write_json(surfer_path, surfer.model_dump(mode="json"))
        write_json(brief_path, brief.model_dump(mode="json"))
    except (ValueError, OSError) as error:
        fail(str(error))
    print(f"Saved brief to {brief_path}")
    print(f"Saved topic Surfer context to {surfer_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
