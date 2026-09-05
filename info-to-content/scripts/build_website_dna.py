"""Validate and persist lightweight website context proposed by Codex."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import fail, load_json_input, unique_strings
from models import WebsiteDNA
from state import artifact_path, resolve_state_dir, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        dna = WebsiteDNA.model_validate(load_json_input(args.candidate))
        dna = dna.model_copy(
            update={
                "products": unique_strings(dna.products),
                "tone": unique_strings(dna.tone),
                "existing_topics": unique_strings(dna.existing_topics),
            }
        )
        output = write_json(
            artifact_path(resolve_state_dir(args.state_dir), "website_dna"),
            dna.model_dump(mode="json"),
        )
    except (ValueError, OSError) as error:
        fail(str(error))
    print(f"Saved website DNA to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
