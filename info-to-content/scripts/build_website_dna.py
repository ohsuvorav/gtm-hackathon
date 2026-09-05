"""Validate Surfer website context and persist normalized DNA plus voice state."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import fail, load_json_input, unique_strings
from models import VoiceContext, WebsiteDNA
from state import artifact_path, ensure_state_v2, resolve_state_dir, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--surfer-brand", type=Path, required=True)
    parser.add_argument("--custom-voice", type=Path)
    parser.add_argument("--workspace-id", type=int, required=True)
    parser.add_argument("--state-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        brand = load_json_input(args.surfer_brand)
        if not isinstance(brand, dict):
            raise ValueError("Surfer brand response must be a JSON object")
        knowledge = brand.get("knowledge")
        if not isinstance(knowledge, str) or not knowledge.strip():
            raise ValueError("Surfer brand response has no completed knowledge")
        if brand.get("gathering_data_status") != "completed":
            raise ValueError("Surfer brand knowledge is not in completed state")
        if brand.get("id") is None:
            raise ValueError("Surfer brand response has no brand id")
        candidate = load_json_input(args.candidate)
        if not isinstance(candidate, dict):
            raise ValueError("Website DNA candidate must be a JSON object")
        candidate.update(
            {
                "source": "surferseo",
                "workspace_id": args.workspace_id,
                "brand_id": str(brand["id"]),
                "brand_url": brand.get("url"),
                "gathering_data_status": brand.get("gathering_data_status"),
            }
        )
        dna = WebsiteDNA.model_validate(candidate)
        dna = dna.model_copy(
            update={
                "products": unique_strings(dna.products),
                "tone": unique_strings(dna.tone),
                "existing_topics": unique_strings(dna.existing_topics),
                "competitors": unique_strings(dna.competitors),
                "topics_to_cover": unique_strings(dna.topics_to_cover),
            }
        )
        if args.custom_voice:
            voice_raw = load_json_input(args.custom_voice)
            reference_text = voice_raw.get("reference_text") if isinstance(voice_raw, dict) else None
            if not isinstance(reference_text, str) or not reference_text.strip():
                raise ValueError("Surfer custom voice response has no reference_text")
            voice = VoiceContext(
                available=True,
                voice_id=str(voice_raw.get("id")) if voice_raw.get("id") is not None else None,
                name=str(voice_raw.get("name")) if voice_raw.get("name") else None,
                reference_text=reference_text,
            )
        else:
            voice_raw = {"available": False, "unavailable_reason": "Surfer custom voice was not available"}
            voice = VoiceContext.model_validate(voice_raw)
        state_dir = resolve_state_dir(args.state_dir)
        ensure_state_v2(state_dir)
        write_json(state_dir / "surfer" / "brand_raw.json", brand)
        write_json(state_dir / "surfer" / "custom_voice_raw.json", voice_raw)
        write_json(state_dir / "surfer" / "custom_voice.json", voice.model_dump(mode="json"))
        output = write_json(
            artifact_path(state_dir, "website_dna"),
            dna.model_dump(mode="json"),
        )
    except (ValueError, OSError) as error:
        fail(str(error))
    print(f"Saved website DNA to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
