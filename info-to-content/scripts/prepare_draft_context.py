"""Print the validated Surfer-gap-to-call grounding bundle for drafting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import fail, validate_many
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
from state import artifact_path, read_json, require_state_v2, resolve_state_dir, write_text


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
        require_state_v2(state_dir)
        opportunities = validate_many(ContentOpportunity, read_json(artifact_path(state_dir, "opportunities")))
        opportunity = next((item for item in opportunities if item.id == args.opportunity_id), None)
        if opportunity is None:
            raise ValueError(f"Unknown opportunity ID: {args.opportunity_id}")
        all_insights = validate_many(ContentInsight, read_json(artifact_path(state_dir, "insights")))
        supporting = [item for item in all_insights if item.id in opportunity.insight_ids]
        if len(supporting) != len(set(opportunity.insight_ids)):
            raise ValueError("Opportunity has missing supporting insights")
        gaps = KeywordGapReport.model_validate(read_json(artifact_path(state_dir, "keyword_gaps")))
        gap = next((item for item in gaps.viable if item.id == opportunity.keyword_gap_id), None)
        if gap is None:
            raise ValueError("Opportunity has no viable keyword gap")
        source = SourceDocument.model_validate(
            read_json(state_dir / "sources" / f"{opportunity.source_id}.json")
        )
        match = OpportunityMatch.model_validate(
            read_json(state_dir / "matches" / f"{opportunity.source_id}.json")
        )
        dna = WebsiteDNA.model_validate(read_json(artifact_path(state_dir, "website_dna")))
        voice = VoiceContext.model_validate(read_json(state_dir / "surfer" / "custom_voice.json"))
        brief = ContentBrief.model_validate(read_json(state_dir / "briefs" / f"{opportunity.id}.json"))
        surfer = SurferContext.model_validate(read_json(state_dir / "surfer" / f"{opportunity.id}.json"))
        payload = {
            "source": source.model_dump(mode="json"),
            "website_dna": dna.model_dump(mode="json"),
            "voice": voice.model_dump(mode="json"),
            "keyword_gap": gap.model_dump(mode="json"),
            "match": match.model_dump(mode="json"),
            "opportunity": opportunity.model_dump(mode="json"),
            "brief": brief.model_dump(mode="json"),
            "supporting_insights": [item.model_dump(mode="json") for item in supporting],
            "surfer_context": surfer.model_dump(mode="json"),
        }
        rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            write_text(args.output, rendered)
            print(f"Saved draft context to {args.output}")
        else:
            print(rendered, end="")
    except (ValueError, OSError) as error:
        fail(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
