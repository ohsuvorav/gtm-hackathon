"""Stage 4 — site DNA.

Live path is Surfer's MCP. The call shape is known:

    mcp__surferseo__brand__get({ workspace_id: 1385655 })

MCP tools are called by the agent, not by this process, so `live` mode here means
"an agent ran that call and wrote the result to the fixture path." Wiring this process
directly to an MCP client is deferred — see NEXT.md.

The six fields Surfer returns are the contract stage 2 and stage 6 read.
"""

from __future__ import annotations

from .common import FIXTURES, read_json, source_for

WORKSPACE_ID = 1385655

# Surfer's field labels -> our keys. Left side is what the MCP response uses.
FIELD_MAP = {
    "Business Type": "business_type",
    "Industry": "industry",
    "Products/Services description": "products_services",
    "Customer profile": "customer_profile",
    "Competitors": "competitors",
    "Topics to cover": "topics_to_cover",
}


def from_mcp_response(response: dict) -> dict:
    """Normalize a `brand__get` response into the fixture schema."""
    dna = {key: str(response.get(label, "")).strip() for label, key in FIELD_MAP.items()}
    dna["_meta"] = {
        "source": "surferseo-mcp",
        "mode": "live",
        "workspace_id": WORKSPACE_ID,
        "voice_available": False,  # brand__get returns no tone or style data
    }
    return dna


def run() -> dict:
    if source_for(4) == "live":
        raise SystemExit(
            "Stage 4 live mode needs an agent to call "
            f"mcp__surferseo__brand__get({{ workspace_id: {WORKSPACE_ID} }}) "
            "and write the result through from_mcp_response() to "
            f"{FIXTURES / 'site_dna.json'}"
        )
    return read_json(FIXTURES / "site_dna.json")
