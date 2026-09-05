"""Stage 4 — normalize Surfer brand knowledge into the pipeline DNA contract."""

from __future__ import annotations

import re

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


def _knowledge_sections(markdown: str) -> dict[str, str]:
    """Parse Surfer's ``**Heading**`` brand-knowledge Markdown sections."""
    matches = list(re.finditer(r"^\*\*(.+?)\*\*\s*$", markdown, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections[match.group(1).strip()] = markdown[start:end].strip()
    return sections


def from_mcp_response(response: dict, workspace_id: int = WORKSPACE_ID) -> dict:
    """Normalize a live ``brand__get`` response into the pipeline's JSON schema."""
    knowledge = response.get("knowledge")
    source = _knowledge_sections(knowledge) if isinstance(knowledge, str) else response
    dna = {key: str(source.get(label, "")).strip() for label, key in FIELD_MAP.items()}
    missing = [key for key, value in dna.items() if not value]
    if missing:
        raise ValueError(f"Surfer brand knowledge is missing DNA fields: {', '.join(missing)}")
    if source.get("Problem solved"):
        dna["problem_solved"] = str(source["Problem solved"]).strip()
    dna["_meta"] = {
        "source": "surferseo-mcp",
        "mode": "live",
        "workspace_id": workspace_id,
        "brand_id": response.get("id"),
        "brand_url": response.get("url"),
        "gathering_data_status": response.get("gathering_data_status"),
    }
    return dna


def run() -> dict:
    if source_for(4) == "live":
        raise SystemExit(
            "Use 'python3 run.py TRANSCRIPT --live' for live Surfer DNA fetching; "
            "stage4_dna.run() is the fixture-only adapter"
        )
    return read_json(FIXTURES / "site_dna.json")
