"""Stage 6 — compose the system prompt for draft generation.

This is the core of the workflow. Everything upstream exists to fill this template:
Surfer supplies who the business is and what to write about, the transcript supplies
what an actual buyer actually said. Nothing here calls a model.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "data" / "fixtures"

# Surfer returns no voice or tone data, so when no past posts exist there is nothing to
# derive style from. These are conservative defaults that fail toward plainness — stated
# in the prompt as defaults so a reader knows they were not observed.
DEFAULT_VOICE = [
    "Plain declarative sentences. No hooks, no call to action, no rhetorical-question opener.",
    "Concrete over abstract: a number, a quote, or a specific failure beats a claim.",
    "No hype adjectives. Never 'unlock', 'game-changing', 'supercharge', 'in today's landscape'.",
    "Short paragraphs, one idea each.",
]


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def voice_section(posts_path: Path) -> tuple[str, list[str]]:
    """Voice comes from past posts. Say so plainly when there are none."""
    if not posts_path.exists():
        return (
            "No past posts were available, and Surfer's site analysis returns no voice or "
            "tone data. The rules below are conservative defaults, not observed style.",
            DEFAULT_VOICE,
        )
    posts = [json.loads(line) for line in posts_path.read_text().splitlines() if line.strip()]
    return f"Derived from {len(posts)} past posts.", DEFAULT_VOICE


def compose(dna: dict, gaps: dict, signal: dict, posts_path: Path) -> str:
    match = signal.get("match")
    if not match:
        raise SystemExit("signal has no match — stage 6 should not have been reached")

    cluster = next(
        (c for c in gaps["viable"] if c["cluster"] == match["cluster"]),
        None,
    )
    if cluster is None:
        raise SystemExit(
            f"matched cluster {match['cluster']!r} is not in the viable set — "
            "stage 1 matched against a rejected or invented cluster"
        )

    voice_note, voice_rules = voice_section(posts_path)
    core = signal["core"]

    supporting = "\n".join(
        f"- {k['keyword']} ({k['volume']}/mo, difficulty {k['difficulty']})"
        for k in cluster["keywords"][:6]
    )
    quotes = "\n".join(f'- "{q}"' for q in core["buyer_language"])

    competitor = core.get("competitor") or "None named."
    if core.get("competitor_note"):
        competitor += f" {core['competitor_note']}"

    return f"""# System prompt — draft generation

You are writing one piece of content for the business described below. It is grounded in a
real conversation, not a topic brief. Everything specific in the draft must trace back to
something in the Source signal section.

## The business

- **Sells:** {dna['products_services']}
- **To:** {dna['customer_profile']}
- **Industry:** {dna['industry']}
- **Competes with:** {dna['competitors']}

Surfer reports this site as `{dna['business_type']}`, so the fields above are thin inferences
from a small crawl. Treat them as boundaries — do not invent products, results, customers, or
credentials that are not stated here.

## Target

**Primary keyword:** {match['keyword']}
**Cluster:** {cluster['cluster']} — {cluster['volume']:,} searches/mo, average difficulty \
{cluster['avg_difficulty']}, currently capturing {cluster['capture_rate']:.0%} of it.

Supporting keywords to cover naturally. Do not stuff them:

{supporting}

## Source signal

**Topic:** {core['topic']}

**Objection raised:** {core['objection']}

**Competitor:** {competitor}

**Why this target was chosen** (confidence {match['confidence']}):
> {match['evidence']}

{match.get('rationale', '')}

### The buyer's own words — verbatim

Use these. Quoting the buyer's phrasing is the entire reason this draft is worth more than a
keyword brief. Do not smooth them out.

{quotes}

## Voice

{voice_note}

{chr(10).join(f'- {rule}' for rule in voice_rules)}

## Hard rules

- Every specific claim traces to the Source signal or the business description. If you want to
  assert something neither supports, cut it.
- Never invent a statistic, case study, customer name, or result.
- Never claim the business has done something the DNA does not state.
- Write for the reader searching `{match['keyword']}`. They have the problem the buyer above
  described; they have not had that conversation.
- Open on the buyer's actual problem. No throat-clearing, no "in today's fast-paced".
- This draft goes to a human for approval. Nothing publishes automatically.
"""


if __name__ == "__main__":
    dna, gaps, signal = load("site_dna.json"), load("gaps.json"), load("signal.json")
    prompt = compose(dna, gaps, signal, FIXTURES / "past_posts.jsonl")

    out = ROOT / "data" / "out" / "system_prompt.md"
    out.write_text(prompt)
    print(prompt)
    print(f"\n--- wrote {out} ({len(prompt)} chars) ---")
