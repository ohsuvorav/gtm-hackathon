"""End-to-end runner: a file in data/inbox/ becomes a draft awaiting human approval.

Order matters and is not the order in the original spec. Stage 4 (DNA) runs before
stage 2 (gaps) because the gap filter needs the ICP to tell an on-topic cluster from
an off-topic one — metrics alone cannot.

    python3 run.py                     # fixture mode, no keys needed
    STAGE7_SOURCE=live python3 run.py  # generate for real
"""

from __future__ import annotations

import sys
from pathlib import Path

from pipeline import stage1_extract, stage4_dna, stage6_compose, stage7_draft, stage8_surfer, stage9_approve
from pipeline.common import DATA, FIXTURES, INBOX, OUT, source_for, write_json
from pipeline.stage2_gaps import icp_terms, parse, to_gaps


def stage0_ingest() -> tuple[Path, str]:
    """Read the oldest unprocessed file in the inbox, else the checked-in sample."""
    files = sorted(p for p in INBOX.glob("*") if p.is_file() and not p.name.startswith("."))
    path = files[0] if files else DATA / "call_transcription.md"
    return path, path.read_text()


def step(number: int, name: str) -> None:
    print(f"\n[{number}] {name}  (source={source_for(number)})")


def main() -> int:
    path, transcript = stage0_ingest()
    step(0, "ingest")
    print(f"    {path.relative_to(DATA.parent)} — {len(transcript):,} chars")

    step(4, "site DNA")
    dna = stage4_dna.run()
    print(f"    {dna['products_services']} -> {dna['customer_profile']}")

    step(2, "content gaps")
    terms = icp_terms(FIXTURES / "site_dna.json")
    clusters = parse(next(FIXTURES.glob("surfer-content-planner-*.csv")), terms)
    gaps = to_gaps(clusters, terms)
    write_json(OUT / "gaps.json", gaps)
    print(f"    {len(gaps['viable'])} viable, {len(gaps['rejected'])} rejected")

    step(1, "primed extraction")
    signal = stage1_extract.run(dna, gaps, transcript)
    write_json(OUT / "signal.json", signal)
    match = signal.get("match")
    if not match:
        reason = signal.get("_meta", {}).get("match_rejected", "no gap matched this conversation")
        print(f"    no match — {reason}")
        print("\nStopping. No content action. This is a correct outcome, not a failure.")
        return 0
    print(f"    {match['cluster']} -> {match['keyword']} (confidence {match['confidence']})")

    step(6, "compose system prompt")
    prompt = stage6_compose.compose(dna, gaps, signal, FIXTURES / "past_posts.jsonl")
    (OUT / "system_prompt.md").write_text(prompt)
    print(f"    {len(prompt):,} chars -> data/out/system_prompt.md")

    step(7, "generate draft")
    draft = stage7_draft.run(prompt)
    (OUT / "draft.md").write_text(draft)
    print(f"    {len(draft.split()):,} words -> data/out/draft.md")

    step(8, "Surfer Content Editor")
    score = stage8_surfer.run(draft, match["keyword"])
    print(f"    {'score ' + str(score) if score else 'skipped — MCP not authenticated'}")

    step(9, "human approval")
    stage9_approve.run(draft, match["keyword"], score)
    return 0


if __name__ == "__main__":
    sys.exit(main())
