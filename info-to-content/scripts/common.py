"""Shared CLI helpers and deterministic normalization."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def load_json_input(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Input file does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error


def unwrap_list(payload: Any, key: str) -> list[Any]:
    if isinstance(payload, dict) and key in payload:
        payload = payload[key]
    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON array or an object containing '{key}'")
    return payload


def validate_many(model: type[T], values: Iterable[Any]) -> list[T]:
    result: list[T] = []
    for index, value in enumerate(values):
        try:
            result.append(model.model_validate(value))
        except ValidationError as error:
            raise ValueError(f"Item {index} failed validation: {error}") from error
    return result


def normalized_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("“", '"').replace("”", '"').replace("’", "'")
    return re.sub(r"\s+", " ", value).strip().casefold()


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(normalized_text(part) for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def unique_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = value.strip()
        key = normalized_text(clean)
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def dump_models(values: Iterable[BaseModel]) -> list[dict[str, Any]]:
    return [value.model_dump(mode="json") for value in values]


def fail(message: str) -> "None":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)
