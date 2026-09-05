"""Shared plumbing: paths, the fixture/live switch, and JSON helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
FIXTURES = DATA / "fixtures"
OUT = DATA / "out"
INBOX = DATA / "inbox"
PROMPTS = Path(__file__).parent / "prompts"

OUT.mkdir(parents=True, exist_ok=True)

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")


def source_for(stage: int) -> str:
    """`fixture` or `live`, per stage. STAGE7_SOURCE beats PIPELINE_SOURCE."""
    return os.environ.get(f"STAGE{stage}_SOURCE", os.environ.get("PIPELINE_SOURCE", "fixture"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2))
    return path


def openai_client():
    """Import lazily so the whole pipeline runs in fixture mode with no SDK installed."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set — run this stage with SOURCE=fixture")
    from openai import OpenAI

    return OpenAI()
