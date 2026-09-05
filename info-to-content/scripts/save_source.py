"""Persist a transcript retrieved from a connected source with provenance."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from common import dump_models, fail, validate_many
from models import ContentInsight, ContentOpportunity, SourceDocument
from state import (
    artifact_path,
    ensure_state_v2,
    load_optional,
    read_json,
    resolve_state_dir,
    write_json,
    write_text,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--external-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--retrieved-at")
    parser.add_argument("--state-dir", type=Path)
    return parser


def invalidate_changed_source(state_dir: Path, source_id: str) -> None:
    insights = validate_many(
        ContentInsight,
        load_optional(artifact_path(state_dir, "insights"), []),
    )
    retained_insights: list[ContentInsight] = []
    for insight in insights:
        evidence = [item for item in insight.evidence if item.source_id != source_id]
        if evidence:
            retained_insights.append(
                insight.model_copy(update={"evidence": evidence, "occurrence_count": len(evidence)})
            )
    if (artifact_path(state_dir, "insights")).exists():
        write_json(artifact_path(state_dir, "insights"), dump_models(retained_insights))

    opportunities = validate_many(
        ContentOpportunity,
        load_optional(artifact_path(state_dir, "opportunities"), []),
    )
    stale = [item for item in opportunities if item.source_id == source_id]
    retained = [item for item in opportunities if item.source_id != source_id]
    if artifact_path(state_dir, "opportunities").exists():
        write_json(artifact_path(state_dir, "opportunities"), dump_models(retained))
    for opportunity in stale:
        for path in (
            state_dir / "briefs" / f"{opportunity.id}.json",
            state_dir / "drafts" / f"{opportunity.id}.md",
            state_dir / "surfer" / f"{opportunity.id}.json",
        ):
            path.unlink(missing_ok=True)
    (state_dir / "matches" / f"{source_id}.json").unlink(missing_ok=True)


def main() -> int:
    args = build_parser().parse_args()
    try:
        transcript = args.transcript.read_text(encoding="utf-8")
        if not transcript.strip():
            raise ValueError("Transcript must not be empty")
        state_dir = resolve_state_dir(args.state_dir)
        relative_path = f"sources/{args.source_id}.txt"
        source = SourceDocument(
            source_id=args.source_id,
            provider=args.provider,
            external_id=args.external_id,
            title=args.title,
            transcript_path=relative_path,
            content_sha256=hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
            retrieved_at=args.retrieved_at,
        )
        ensure_state_v2(state_dir)
        previous_path = state_dir / "sources" / f"{source.source_id}.json"
        changed = False
        if previous_path.exists():
            previous = SourceDocument.model_validate(read_json(previous_path))
            changed = previous.content_sha256 != source.content_sha256
        transcript_path = write_text(state_dir / relative_path, transcript)
        metadata_path = write_json(
            state_dir / "sources" / f"{source.source_id}.json",
            source.model_dump(mode="json"),
        )
        if changed:
            invalidate_changed_source(state_dir, source.source_id)
    except (ValueError, OSError) as error:
        fail(str(error))
    print(f"Saved {source.provider} transcript to {transcript_path}")
    print(f"Saved source metadata to {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
