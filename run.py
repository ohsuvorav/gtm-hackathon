"""End-to-end runner: a transcript becomes a draft awaiting human approval.

Order matters and is not the order in the original spec. Stage 4 (DNA) runs before
stage 2 (gaps) because the gap filter needs the ICP to tell an on-topic cluster from
an off-topic one — metrics alone cannot.

    python3 run.py                                      # fixture demo
    python3 run.py call.md --live --workspace-id 1385655
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from main import DEFAULT_SERVER_URL, StdioMcpClient, fetch_dna_data
from pipeline import stage1_extract, stage4_dna, stage6_compose, stage7_draft, stage8_surfer, stage9_approve
from pipeline.common import DATA, FIXTURES, INBOX, OUT, source_for, write_json
from pipeline.stage2_gaps import (
    from_recommendations,
    icp_terms,
    icp_terms_from_dna,
    parse,
    to_gaps,
)


DNA = DATA / "dna"


def stage0_ingest(explicit_path: Path | None = None) -> tuple[Path, str]:
    """Read the oldest unprocessed file in the inbox, else the checked-in sample."""
    if explicit_path:
        if not explicit_path.is_file():
            raise FileNotFoundError(f"Transcript not found: {explicit_path}")
        return explicit_path, explicit_path.read_text(encoding="utf-8")
    files = sorted(p for p in INBOX.glob("*") if p.is_file() and not p.name.startswith("."))
    path = files[0] if files else DATA / "call_transcription.md"
    return path, path.read_text(encoding="utf-8")


def step(number: int, name: str, source: str | None = None) -> None:
    print(f"\n[{number}] {name}  (source={source or source_for(number)})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "transcript",
        type=Path,
        nargs="?",
        help="UTF-8 call transcript; defaults to the oldest data/inbox file",
    )
    parser.add_argument("--live", action="store_true", help="Fetch Surfer inputs and use OpenAI")
    parser.add_argument(
        "--workspace-id",
        type=int,
        default=int(os.environ.get("SURFER_WORKSPACE_ID", stage4_dna.WORKSPACE_ID)),
    )
    parser.add_argument("--voice-id", type=int, help="Custom voice; defaults to workspace default")
    parser.add_argument(
        "--server-url",
        default=os.environ.get("SURFER_MCP_URL", DEFAULT_SERVER_URL),
    )
    parser.add_argument("--recommendation-limit", type=int, default=100)
    parser.add_argument(
        "--push-to-surfer",
        action="store_true",
        help="Create/update a Content Editor and score the draft; may consume one credit",
    )
    return parser


def fetch_live_inputs(args: argparse.Namespace, client: StdioMcpClient) -> tuple[dict, dict, Path]:
    """Fetch and persist every non-transcript input needed by the live pipeline."""
    brand, voice = fetch_dna_data(client, args.workspace_id, voice_id=args.voice_id)
    knowledge = brand.get("knowledge")
    reference_text = voice.get("reference_text")
    if not isinstance(knowledge, str) or not knowledge.strip():
        raise RuntimeError("Surfer brand knowledge is empty or not ready")
    if not isinstance(reference_text, str) or not reference_text.strip():
        raise RuntimeError("Surfer custom voice reference text is empty")

    DNA.mkdir(parents=True, exist_ok=True)
    site_path = DNA / "site_dna.md"
    voice_path = DNA / "mirality-positioning.md"
    site_path.write_text(knowledge, encoding="utf-8")
    voice_path.write_text(reference_text, encoding="utf-8")

    dna = stage4_dna.from_mcp_response(brand, args.workspace_id)
    write_json(DNA / "site_dna.json", dna)

    recommendations = client.call_tool(
        "recommendation__list",
        {
            "workspace_id": args.workspace_id,
            "type": "write",
            "sort": "score",
            "order": "desc",
            "limit": args.recommendation_limit,
            "page": 1,
            "page_size": args.recommendation_limit,
        },
    )
    write_json(DNA / "keyword_recommendations.json", recommendations)
    gaps = from_recommendations(recommendations, icp_terms_from_dna(dna))
    if not gaps["viable"]:
        raise RuntimeError("Surfer returned no viable, on-ICP write recommendations")
    return dna, gaps, voice_path


def run_pipeline(args: argparse.Namespace, client: StdioMcpClient | None = None) -> int:
    path, transcript = stage0_ingest(args.transcript)
    step(0, "ingest")
    try:
        display_path = path.relative_to(DATA.parent)
    except ValueError:
        display_path = path
    print(f"    {display_path} — {len(transcript):,} chars")

    step(4, "site DNA + custom voice", "surferseo-mcp" if args.live else None)
    if args.live:
        if client is None:
            raise RuntimeError("Live mode requires a connected Surfer MCP client")
        dna, gaps, voice_path = fetch_live_inputs(args, client)
    else:
        dna = stage4_dna.run()
        voice_path = None
    print(f"    {dna['products_services']} -> {dna['customer_profile']}")

    step(2, "content gaps", "surferseo-mcp" if args.live else None)
    if not args.live:
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
    prompt = stage6_compose.compose(
        dna,
        gaps,
        signal,
        FIXTURES / "past_posts.jsonl",
        voice_path=voice_path,
    )
    (OUT / "system_prompt.md").write_text(prompt)
    print(f"    {len(prompt):,} chars -> data/out/system_prompt.md")

    step(7, "generate draft")
    draft = stage7_draft.run(prompt)
    (OUT / "draft.md").write_text(draft)
    print(f"    {len(draft.split()):,} words -> data/out/draft.md")

    step(8, "Surfer Content Editor")
    selected = next(c for c in gaps["viable"] if c["cluster"] == match["cluster"])
    score = stage8_surfer.run(
        draft,
        match["keyword"],
        client=client,
        workspace_id=args.workspace_id,
        location=selected.get("location"),
        content_editor_id=selected.get("content_editor_id"),
    )
    print(f"    {'score ' + str(score) if score else 'skipped — pass --push-to-surfer to enable'}")

    step(9, "human approval")
    stage9_approve.run(draft, match["keyword"], score)
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.push_to_surfer and not args.live:
        raise SystemExit("--push-to-surfer requires --live")
    if args.live:
        os.environ["STAGE1_SOURCE"] = "live"
        os.environ["STAGE7_SOURCE"] = "live"
        os.environ["STAGE8_SOURCE"] = "live" if args.push_to_surfer else "fixture"
        with StdioMcpClient(args.server_url) as client:
            return run_pipeline(args, client)
    return run_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
