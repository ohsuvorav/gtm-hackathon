"""Stage 8 — put a draft in Surfer Content Editor and return its score."""

from __future__ import annotations

import time
from typing import Any

from .common import source_for

WORKSPACE_ID = 1385655


def _wait_for_editor(
    client: Any,
    workspace_id: int,
    content_editor_id: int,
    timeout: float = 150,
) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        editor = client.call_tool(
            "content_editor__get",
            {"workspace_id": workspace_id, "content_editor_id": content_editor_id},
        )
        state = editor.get("state")
        if state == "completed":
            return editor
        if state == "failed":
            raise RuntimeError(f"Surfer Content Editor {content_editor_id} failed")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Surfer Content Editor {content_editor_id} was not ready in time")
        time.sleep(3)


def _wait_for_score(
    client: Any,
    workspace_id: int,
    content_editor_id: int,
    timeout: float = 90,
) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        score = client.call_tool(
            "content_score__get",
            {"workspace_id": workspace_id, "content_editor_id": content_editor_id},
        )
        if score.get("total", {}).get("status") == "ready":
            return score
        if time.monotonic() >= deadline:
            return score
        time.sleep(3)


def run(
    draft: str,
    keyword: str,
    *,
    client: Any | None = None,
    workspace_id: int = WORKSPACE_ID,
    location: str | None = None,
    content_editor_id: int | None = None,
) -> dict | None:
    """Create/reuse an editor, replace its content, and wait for its score.

    Creating a new editor consumes one Surfer Content Editor credit. Callers keep
    this stage in fixture mode unless the user explicitly opts into that action.
    """
    if source_for(8) != "live":
        return None
    if client is None:
        raise RuntimeError("Stage 8 live mode requires a connected Surfer MCP client")

    if content_editor_id is None:
        arguments: dict[str, Any] = {
            "workspace_id": workspace_id,
            "main_keyword": keyword,
            "use_brand_knowledge": True,
            "surfer_template": "blog_post",
        }
        if location:
            arguments["location"] = location
        editor = client.call_tool("content_editor__create", arguments)
        content_editor_id = int(editor["id"])

    _wait_for_editor(client, workspace_id, content_editor_id)
    client.call_tool(
        "content__update",
        {
            "workspace_id": workspace_id,
            "content_editor_id": content_editor_id,
            "format": "markdown",
            "content": draft,
        },
    )
    score = _wait_for_score(client, workspace_id, content_editor_id)
    return {"content_editor_id": content_editor_id, **score}
