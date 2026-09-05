"""Print the complete, validated grounding bundle for one selected opportunity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import fail, validate_many
from models import ContentBrief, ContentInsight, ContentOpportunity, SurferContext, WebsiteDNA
from state import artifact_path, read_json, resolve_state_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opportunity-id", required=True)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        state_dir = resolve_state_dir(args.state_dir)
        opportunities = validate_many(
            ContentOpportunity,
            read_json(artifact_path(state_dir, "opportunities")),
        )
        opportunity = next((item for item in opportunities if item.id == args.opportunity_id), None)
        if opportunity is None:
            raise ValueError(f"Unknown opportunity ID: {args.opportunity_id}")
        all_insights = validate_many(
            ContentInsight,
            read_json(artifact_path(state_dir, "insights")),
        )
        supporting = [item for item in all_insights if item.id in opportunity.insight_ids]
        if len(supporting) != len(set(opportunity.insight_ids)):
            raise ValueError("Selected opportunity has missing supporting insights")
        dna = WebsiteDNA.model_validate(read_json(artifact_path(state_dir, "website_dna")))
        brief = ContentBrief.model_validate(
            read_json(state_dir / "briefs" / f"{opportunity.id}.json")
        )
        surfer = SurferContext.model_validate(
            read_json(state_dir / "surfer" / f"{opportunity.id}.json")
        )
        payload = {
            "opportunity": opportunity.model_dump(mode="json"),
            "brief": brief.model_dump(mode="json"),
            "supporting_insights": [item.model_dump(mode="json") for item in supporting],
            "website_dna": dna.model_dump(mode="json"),
            "surfer_context": surfer.model_dump(mode="json"),
        }
        rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
            print(f"Saved draft context to {args.output}")
        else:
            print(rendered, end="")
    except (ValueError, OSError) as error:
        fail(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
