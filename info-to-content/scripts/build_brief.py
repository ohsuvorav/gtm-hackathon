"""Validate and persist a brief for one selected opportunity."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import fail, load_json_input, unique_strings, validate_many
from models import ContentBrief, ContentInsight, ContentOpportunity, SurferContext, WebsiteDNA
from state import artifact_path, read_json, resolve_state_dir, write_json


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
        insights = validate_many(ContentInsight, read_json(artifact_path(state_dir, "insights")))
        insight_ids = {item.id for item in insights}
        WebsiteDNA.model_validate(read_json(artifact_path(state_dir, "website_dna")))
        opportunities = validate_many(
            ContentOpportunity,
            read_json(artifact_path(state_dir, "opportunities")),
        )
        opportunity = next((item for item in opportunities if item.id == args.opportunity_id), None)
        if opportunity is None:
            raise ValueError(f"Unknown opportunity ID: {args.opportunity_id}")

        if args.surfer_context:
            surfer = SurferContext.model_validate(load_json_input(args.surfer_context))
        else:
            surfer = SurferContext(
                available=False,
                unavailable_reason="Surfer context was not requested or available",
            )

        brief = ContentBrief.model_validate(load_json_input(args.candidate))
        supporting = list(dict.fromkeys(brief.supporting_insight_ids))
        missing = sorted(set(supporting) - insight_ids)
        outside_opportunity = sorted(set(supporting) - set(opportunity.insight_ids))
        if missing:
            raise ValueError(f"Brief has unknown supporting insight IDs: {missing}")
        if outside_opportunity:
            raise ValueError(
                "Brief cites insights outside the selected opportunity: "
                f"{outside_opportunity}"
            )

        seo_terms = surfer.recommended_terms if surfer.available else []
        brief = brief.model_copy(
            update={
                "title": opportunity.title,
                "audience": opportunity.target_audience,
                "angle": opportunity.angle,
                "supporting_insight_ids": supporting,
                "key_customer_pains_questions": unique_strings(
                    brief.key_customer_pains_questions
                ),
                "required_points": unique_strings(brief.required_points),
                "seo_terms": unique_strings(seo_terms),
                "target_word_count": surfer.target_word_count if surfer.available else None,
                "surfer_available": surfer.available,
            }
        )
        brief_path = state_dir / "briefs" / f"{opportunity.id}.json"
        surfer_path = state_dir / "surfer" / f"{opportunity.id}.json"
        write_json(surfer_path, surfer.model_dump(mode="json"))
        write_json(brief_path, brief.model_dump(mode="json"))
    except (ValueError, OSError) as error:
        fail(str(error))
    print(f"Saved brief to {brief_path}")
    print(f"Saved Surfer context to {surfer_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
