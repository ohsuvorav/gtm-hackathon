"""Validate, score, rank, and persist model-proposed content opportunities."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import dump_models, fail, load_json_input, normalized_text, stable_id, unwrap_list, validate_many
from models import ContentInsight, ContentOpportunity, WebsiteDNA
from state import artifact_path, read_json, resolve_state_dir, write_json


def evidence_strength(insights: list[ContentInsight]) -> float:
    mentions = sum(insight.occurrence_count for insight in insights)
    return min(mentions / 10.0, 1.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        state_dir = resolve_state_dir(args.state_dir)
        insights = validate_many(ContentInsight, read_json(artifact_path(state_dir, "insights")))
        WebsiteDNA.model_validate(read_json(artifact_path(state_dir, "website_dna")))
        by_id = {item.id: item for item in insights}
        candidates = validate_many(
            ContentOpportunity,
            unwrap_list(load_json_input(args.candidates), "opportunities"),
        )
        if not 3 <= len(candidates) <= 5:
            raise ValueError("Provide 3 to 5 content opportunities")

        seen_titles: set[str] = set()
        result: list[ContentOpportunity] = []
        for candidate in candidates:
            title_key = normalized_text(candidate.title)
            if title_key in seen_titles:
                raise ValueError(f"Duplicate opportunity title: {candidate.title!r}")
            seen_titles.add(title_key)
            insight_ids = list(dict.fromkeys(candidate.insight_ids))
            missing = sorted(set(insight_ids) - set(by_id))
            if missing:
                raise ValueError(f"Opportunity {candidate.title!r} has unknown insight IDs: {missing}")
            supporting = [by_id[identifier] for identifier in insight_ids]
            result.append(
                candidate.model_copy(
                    update={
                        "id": stable_id("opp", candidate.title, candidate.angle),
                        "insight_ids": insight_ids,
                        "evidence_strength": evidence_strength(supporting),
                    }
                )
            )
        result.sort(key=lambda item: (-item.evidence_strength, item.title.casefold()))
        output = write_json(artifact_path(state_dir, "opportunities"), dump_models(result))
    except (ValueError, OSError) as error:
        fail(str(error))
    print(f"Saved {len(result)} ranked opportunities to {output}")
    for index, item in enumerate(result, start=1):
        print(f"{index}. [{item.id}] {item.title} ({item.evidence_strength:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
