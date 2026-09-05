"""Stage 9 — human approval. Nothing publishes without it."""

from __future__ import annotations

import sys

from .common import OUT


def run(draft: str, keyword: str, score: dict | None, interactive: bool = True) -> str:
    print("\n" + "=" * 72)
    print(f"DRAFT READY — target keyword: {keyword}")
    print(f"Surfer score: {score if score else 'unavailable (stage 8 not authenticated)'}")
    print("=" * 72)
    print(draft[:1200] + ("\n\n[...truncated for review...]" if len(draft) > 1200 else ""))
    print("=" * 72)
    print(f"Full draft: {OUT / 'draft.md'}")

    if not interactive or not sys.stdin.isatty():
        print("\nNon-interactive run — left pending. Nothing published.")
        return "pending"

    answer = input("\nApprove for manual publishing? [y/N] ").strip().lower()
    decision = "approved" if answer == "y" else "rejected"
    print(f"-> {decision}. This pipeline never publishes; publishing stays manual.")
    return decision
