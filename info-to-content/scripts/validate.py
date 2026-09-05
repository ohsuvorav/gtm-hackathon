"""Validate all present InfoToContent state and its cross-file references."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import fail, validate_many
from models import ContentBrief, ContentInsight, ContentOpportunity, SurferContext, WebsiteDNA
from state import artifact_path, read_json, resolve_state_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path)
    return parser


def validate_state(state_dir: Path) -> dict[str, int]:
    counts = {"insights": 0, "opportunities": 0, "briefs": 0, "drafts": 0}
    insight_path = artifact_path(state_dir, "insights")
    opportunity_path = artifact_path(state_dir, "opportunities")
    dna_path = artifact_path(state_dir, "website_dna")

    insights = validate_many(ContentInsight, read_json(insight_path)) if insight_path.exists() else []
    insight_ids = {item.id for item in insights}
    if len(insight_ids) != len(insights):
        raise ValueError("Duplicate insight IDs")
    counts["insights"] = len(insights)

    if dna_path.exists():
        WebsiteDNA.model_validate(read_json(dna_path))

    opportunities = (
        validate_many(ContentOpportunity, read_json(opportunity_path))
        if opportunity_path.exists()
        else []
    )
    opportunity_ids = {item.id for item in opportunities}
    if len(opportunity_ids) != len(opportunities):
        raise ValueError("Duplicate opportunity IDs")
    if opportunities and not dna_path.exists():
        raise ValueError("Opportunities exist without website_dna.json")
    if opportunities and not 3 <= len(opportunities) <= 5:
        raise ValueError("State must contain 3 to 5 opportunities")
    for opportunity in opportunities:
        missing = sorted(set(opportunity.insight_ids) - insight_ids)
        if missing:
            raise ValueError(f"Opportunity {opportunity.id} has missing insight IDs: {missing}")
        mentions = sum(
            item.occurrence_count
            for item in insights
            if item.id in opportunity.insight_ids
        )
        expected_strength = min(mentions / 10.0, 1.0)
        if opportunity.evidence_strength != expected_strength:
            raise ValueError(
                f"Opportunity {opportunity.id} has stale evidence_strength "
                f"{opportunity.evidence_strength}; expected {expected_strength}"
            )
    counts["opportunities"] = len(opportunities)

    for brief_path in sorted((state_dir / "briefs").glob("*.json")):
        if brief_path.stem not in opportunity_ids:
            raise ValueError(f"Brief has no matching opportunity: {brief_path}")
        brief = ContentBrief.model_validate(read_json(brief_path))
        opportunity = next(item for item in opportunities if item.id == brief_path.stem)
        outside = sorted(set(brief.supporting_insight_ids) - set(opportunity.insight_ids))
        if outside:
            raise ValueError(f"Brief {brief_path.stem} cites unrelated insights: {outside}")
        surfer_path = state_dir / "surfer" / brief_path.name
        if not surfer_path.is_file():
            raise ValueError(f"Brief is missing Surfer availability record: {surfer_path}")
        SurferContext.model_validate(read_json(surfer_path))
        counts["briefs"] += 1

    for draft_path in sorted((state_dir / "drafts").glob("*.md")):
        if not (state_dir / "briefs" / f"{draft_path.stem}.json").is_file():
            raise ValueError(f"Draft has no matching brief: {draft_path}")
        if not draft_path.read_text(encoding="utf-8").strip():
            raise ValueError(f"Draft is empty: {draft_path}")
        counts["drafts"] += 1
    return counts


def main() -> int:
    args = build_parser().parse_args()
    try:
        state_dir = resolve_state_dir(args.state_dir)
        counts = validate_state(state_dir)
    except (ValueError, OSError) as error:
        fail(str(error))
    print(
        "State valid: "
        + ", ".join(f"{name}={count}" for name, count in counts.items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
