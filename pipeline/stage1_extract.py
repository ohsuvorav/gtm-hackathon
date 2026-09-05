"""Stage 1 — primed extraction.

One pass. The content plan is in context, so extraction and gap-matching happen in the
same call. Guards against the known failure of primed extraction — a model that always
finds a match because the gap list is in front of it — live in code, not the prompt:
confidence is thresholded here, and the matched cluster is checked against the viable set.
"""

from __future__ import annotations

import json

import os

from .common import FIXTURES, OPENAI_MODEL, PROMPTS, openai_client, read_json, source_for

MIN_CONFIDENCE = 0.6


def build_prompt(dna: dict, gaps: dict, transcript: str) -> str:
    business = (
        f"Sells: {dna['products_services']}\n"
        f"To: {dna['customer_profile']}\n"
        f"Industry: {dna['industry']}\n"
        f"Competes with: {dna['competitors']}"
    )
    clusters = "\n".join(
        f"- {c['cluster']} ({c['volume']:,}/mo, difficulty {c['avg_difficulty']}): "
        + ", ".join(k["keyword"] for k in c["keywords"][:5])
        for c in gaps["viable"]
    )
    template = (PROMPTS / "extract_primed.md").read_text()
    return template.format(business=business, clusters=clusters, transcript=transcript)


def enforce_guards(signal: dict, gaps: dict) -> dict:
    """Drop a match the model should not have made. Always record why."""
    match = signal.get("match")
    if not match:
        return signal

    viable = {c["cluster"] for c in gaps["viable"]}
    reason = None
    if match.get("cluster") not in viable:
        reason = f"cluster {match.get('cluster')!r} is not in the viable set"
    elif float(match.get("confidence", 0)) < MIN_CONFIDENCE:
        reason = f"confidence {match.get('confidence')} below {MIN_CONFIDENCE}"
    elif not (match.get("evidence") or "").strip():
        reason = "no verbatim evidence quote"

    if reason:
        signal["match"] = None
        signal.setdefault("_meta", {})["match_rejected"] = reason
    return signal


def run(dna: dict, gaps: dict, transcript: str) -> dict:
    if source_for(1) != "live":
        fixture = os.environ.get("SIGNAL_FIXTURE", "signal.json")
        return enforce_guards(read_json(FIXTURES / fixture), gaps)

    response = openai_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": build_prompt(dna, gaps, transcript)}],
        response_format={"type": "json_object"},
    )
    signal = json.loads(response.choices[0].message.content)
    signal.setdefault("_meta", {}).update({"mode": "live", "model": OPENAI_MODEL})
    return enforce_guards(signal, gaps)
