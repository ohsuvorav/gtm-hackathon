"""Persist a non-empty Markdown draft after its brief has been validated."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import fail
from models import ContentBrief
from state import read_json, resolve_state_dir, write_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opportunity-id", required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        state_dir = resolve_state_dir(args.state_dir)
        ContentBrief.model_validate(
            read_json(state_dir / "briefs" / f"{args.opportunity_id}.json")
        )
        draft = args.draft.read_text(encoding="utf-8").strip()
        if not draft:
            raise ValueError("Draft must not be empty")
        if not draft.startswith("#"):
            raise ValueError("Draft must be Markdown beginning with a heading")
        output = write_text(
            state_dir / "drafts" / f"{args.opportunity_id}.md",
            draft + "\n",
        )
    except (ValueError, OSError) as error:
        fail(str(error))
    print(f"Saved draft to {output}; publication remains a separate user action")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
