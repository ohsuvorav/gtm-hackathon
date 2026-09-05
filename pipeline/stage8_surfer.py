"""Stage 8 — push the draft into a Surfer Content Editor and read back its score.

Not wired. The Surfer MCP connection is unauthenticated in this workspace: the only
tools it exposes are `authenticate` and `complete_authentication`, so the Content Editor
tool names are unknown. This stage no-ops loudly rather than failing the run — losing
the Surfer score should never cost you the draft.
"""

from __future__ import annotations

from .common import source_for

WORKSPACE_ID = 1385655


def run(draft: str, keyword: str) -> dict | None:
    if source_for(8) != "live":
        return None
    raise SystemExit(
        "Stage 8 needs an authenticated Surfer MCP session. Run "
        "mcp__surferseo__authenticate first, then check the tool list for the "
        "Content Editor create/score tools — their names are not published."
    )
