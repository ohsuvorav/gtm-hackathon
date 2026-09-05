"""Workspace-local, atomic persistence and v2 state initialization."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_STATE_DIR = Path(".infotocontent")
SCHEMA_VERSION = 2


class StateError(ValueError):
    pass


def resolve_state_dir(raw: str | Path | None) -> Path:
    return Path(raw) if raw is not None else DEFAULT_STATE_DIR


def read_json(path: Path) -> Any:
    if not path.is_file():
        raise StateError(f"Required state file does not exist: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise StateError(f"Invalid JSON in {path}: {error}") from error


def write_json(path: Path, payload: Any) -> Path:
    return write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def write_text(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return path


def ensure_state_v2(state_dir: Path) -> None:
    marker = state_dir / "state.json"
    if marker.exists():
        require_state_v2(state_dir)
        return
    legacy_names = {"insights.json", "website_dna.json", "opportunities.json", "briefs", "drafts"}
    if state_dir.exists() and any((state_dir / name).exists() for name in legacy_names):
        raise StateError(
            f"Legacy unversioned state found in {state_dir}; use a clean state directory for v2"
        )
    write_json(marker, {"schema_version": SCHEMA_VERSION})


def require_state_v2(state_dir: Path) -> None:
    marker = state_dir / "state.json"
    payload = read_json(marker)
    if payload != {"schema_version": SCHEMA_VERSION}:
        raise StateError(f"Unsupported state schema in {marker}; expected v{SCHEMA_VERSION}")


def artifact_path(state_dir: Path, name: str) -> Path:
    known = {
        "insights": "insights.json",
        "website_dna": "website_dna.json",
        "keyword_gaps": "keyword_gaps.json",
        "opportunities": "opportunities.json",
    }
    try:
        return state_dir / known[name]
    except KeyError as error:
        raise StateError(f"Unknown artifact: {name}") from error


def load_optional(path: Path, default: Any) -> Any:
    return read_json(path) if path.is_file() else default
