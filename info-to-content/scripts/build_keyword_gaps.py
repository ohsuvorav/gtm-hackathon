"""Normalize Surfer write recommendations and persist viable/rejected keyword gaps."""

from __future__ import annotations

import argparse
from pathlib import Path

from pydantic import Field

from common import fail, load_json_input, stable_id, unique_strings, unwrap_list, validate_many
from models import KeywordGap, KeywordGapReport, StrictModel, WebsiteDNA
from state import artifact_path, ensure_state_v2, read_json, resolve_state_dir, write_json

MAX_VIABLE_DIFFICULTY = 65.0


class RelevanceJudgment(StrictModel):
    recommendation_id: str = Field(min_length=1)
    icp_relevant: bool
    rationale: str = Field(min_length=1)


def number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def integer(value: object) -> int | None:
    raw = number(value)
    return int(raw) if raw is not None and raw >= 0 and raw.is_integer() else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recommendations", type=Path, required=True)
    parser.add_argument("--relevance", type=Path, required=True)
    parser.add_argument("--workspace-id", type=int, required=True)
    parser.add_argument("--retrieved-at")
    parser.add_argument("--state-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        raw = load_json_input(args.recommendations)
        rows = raw.get("data") if isinstance(raw, dict) else None
        if not isinstance(rows, list):
            raise ValueError("Surfer recommendations must contain a data array")
        judgments = validate_many(
            RelevanceJudgment,
            unwrap_list(load_json_input(args.relevance), "relevance"),
        )
        by_id = {item.recommendation_id: item for item in judgments}
        if len(by_id) != len(judgments):
            raise ValueError("Duplicate relevance recommendation IDs")
        raw_ids = [str(row.get("id")) for row in rows if isinstance(row, dict) and row.get("id") is not None]
        if len(raw_ids) != len(set(raw_ids)):
            raise ValueError("Surfer recommendations contain duplicate IDs")
        if set(raw_ids) != set(by_id):
            missing = sorted(set(raw_ids) - set(by_id))
            unknown = sorted(set(by_id) - set(raw_ids))
            raise ValueError(f"Relevance judgments must cover every recommendation; missing={missing}, unknown={unknown}")

        state_dir = resolve_state_dir(args.state_dir)
        WebsiteDNA.model_validate(read_json(artifact_path(state_dir, "website_dna")))
        viable: list[KeywordGap] = []
        rejected: list[KeywordGap] = []
        for row in rows:
            if not isinstance(row, dict) or row.get("id") is None:
                raise ValueError("Every Surfer recommendation requires an id")
            if row.get("workspace_id") is not None and row.get("workspace_id") != args.workspace_id:
                raise ValueError("Surfer recommendation belongs to a different workspace")
            recommendation_id = str(row["id"])
            judgment = by_id[recommendation_id]
            keyword = str(row.get("main_keyword") or "").strip()
            title = str(row.get("title") or keyword or f"Recommendation {recommendation_id}").strip()
            raw_difficulty = number(row.get("avg_difficulty"))
            difficulty = round(raw_difficulty / 100.0, 2) if raw_difficulty is not None else None
            search_volume = integer(row.get("search_volume"))
            rejected_for: list[str] = []
            if row.get("type") != "write":
                rejected_for.append("not-write-recommendation")
            if not keyword:
                rejected_for.append("missing-keyword")
            if difficulty is None or difficulty > 100 or search_volume is None:
                rejected_for.append("invalid-metrics")
            elif difficulty >= MAX_VIABLE_DIFFICULTY:
                rejected_for.append("too-difficult")
            if not judgment.icp_relevant:
                rejected_for.append("off-icp")
            gap = KeywordGap(
                id=stable_id("gap", str(args.workspace_id), recommendation_id),
                recommendation_id=recommendation_id,
                title=title,
                topic=str(row.get("topic_title") or "").strip() or None,
                target_keyword=keyword,
                location=str(row.get("location") or "").strip() or None,
                search_volume=search_volume,
                difficulty=difficulty,
                surfer_score=number(row.get("score")),
                reasons=unique_strings(
                    str(item) for item in (
                        row.get("reasons") if isinstance(row.get("reasons"), list) else []
                    )
                ),
                content_editor_id=str(row["content_editor_id"]) if row.get("content_editor_id") is not None else None,
                icp_relevant=judgment.icp_relevant,
                relevance_rationale=judgment.rationale,
                rejected_for=rejected_for,
            )
            (rejected if rejected_for else viable).append(gap)
        viable.sort(key=lambda item: (-(item.surfer_score or 0), -(item.search_volume or 0), item.title.casefold()))
        report = KeywordGapReport(
            source="surferseo-recommendations-mcp",
            workspace_id=args.workspace_id,
            retrieved_at=args.retrieved_at,
            viable=viable,
            rejected=rejected,
        )
        ensure_state_v2(state_dir)
        raw_path = write_json(state_dir / "surfer" / "recommendations_raw.json", raw)
        report_path = write_json(
            artifact_path(state_dir, "keyword_gaps"),
            report.model_dump(mode="json"),
        )
    except (ValueError, OSError) as error:
        fail(str(error))
    print(f"Saved raw Surfer recommendations to {raw_path}")
    print(f"Saved keyword gaps to {report_path}: viable={len(viable)}, rejected={len(rejected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
