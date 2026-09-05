"""Validate, ground, deduplicate, and persist model-proposed customer insights."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    dump_models,
    fail,
    load_json_input,
    normalized_text,
    stable_id,
    unwrap_list,
    validate_many,
)
from models import ContentInsight, EvidenceRef
from state import artifact_path, load_optional, resolve_state_dir, write_json


def parse_transcripts(items: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items:
        source_id, separator, raw_path = item.partition("=")
        if not separator or not source_id.strip() or not raw_path.strip():
            raise ValueError("--transcript must use SOURCE_ID=PATH")
        path = Path(raw_path)
        if not path.is_file():
            raise ValueError(f"Transcript does not exist: {path}")
        source_id = source_id.strip()
        if source_id in result:
            raise ValueError(f"Duplicate transcript source ID: {source_id}")
        result[source_id] = path.read_text(encoding="utf-8")
    if not result:
        raise ValueError("At least one --transcript SOURCE_ID=PATH is required")
    return result


def ground(insights: list[ContentInsight], transcripts: dict[str, str]) -> None:
    normalized_sources = {key: normalized_text(value) for key, value in transcripts.items()}
    for insight in insights:
        for evidence in insight.evidence:
            if evidence.source_id not in normalized_sources:
                raise ValueError(
                    f"Insight {insight.id!r} cites unknown source {evidence.source_id!r}"
                )
            if normalized_text(evidence.quote) not in normalized_sources[evidence.source_id]:
                raise ValueError(
                    f"Insight {insight.id!r} contains a quote not found in "
                    f"source {evidence.source_id!r}: {evidence.quote!r}"
                )


def canonicalize(insight: ContentInsight) -> ContentInsight:
    evidence_seen: set[tuple[str, str, str | None, str | None]] = set()
    evidence: list[EvidenceRef] = []
    for item in insight.evidence:
        key = (
            item.source_id,
            normalized_text(item.quote),
            item.speaker,
            item.timestamp,
        )
        if key not in evidence_seen:
            evidence_seen.add(key)
            evidence.append(item)
    return insight.model_copy(
        update={
            "id": stable_id("ins", insight.type, insight.topic, insight.statement),
            "evidence": evidence,
            "occurrence_count": max(insight.occurrence_count, len(evidence)),
        }
    )


def merge(insights: list[ContentInsight]) -> list[ContentInsight]:
    merged: dict[str, ContentInsight] = {}
    for raw in insights:
        insight = canonicalize(raw)
        previous = merged.get(insight.id)
        if previous is None:
            merged[insight.id] = insight
            continue
        previous_evidence = {
            (item.source_id, normalized_text(item.quote), item.speaker, item.timestamp)
            for item in previous.evidence
        }
        incoming_evidence = {
            (item.source_id, normalized_text(item.quote), item.speaker, item.timestamp)
            for item in insight.evidence
        }
        evidence = previous.evidence + insight.evidence
        combined = canonicalize(previous.model_copy(update={"evidence": evidence}))
        merged[insight.id] = combined.model_copy(
            update={
                "occurrence_count": max(
                    combined.occurrence_count,
                    insight.occurrence_count,
                    previous.occurrence_count + len(incoming_evidence - previous_evidence),
                )
            }
        )
    return sorted(merged.values(), key=lambda item: (item.topic.casefold(), item.id))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument(
        "--transcript",
        action="append",
        default=[],
        metavar="SOURCE_ID=PATH",
    )
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--replace", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        transcripts = parse_transcripts(args.transcript)
        candidates = validate_many(
            ContentInsight,
            unwrap_list(load_json_input(args.candidates), "insights"),
        )
        ground(candidates, transcripts)
        state_dir = resolve_state_dir(args.state_dir)
        existing = [] if args.replace else validate_many(
            ContentInsight,
            load_optional(artifact_path(state_dir, "insights"), []),
        )
        combined = merge(existing + candidates)
        output = write_json(artifact_path(state_dir, "insights"), dump_models(combined))
    except ValueError as error:
        fail(str(error))
    print(f"Saved {len(combined)} grounded insights to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
