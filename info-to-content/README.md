# InfoToContent Codex plugin

InfoToContent turns customer call transcripts into evidence-backed content opportunities, a selected content brief, and a Markdown draft. It keeps every transition inspectable in workspace-local JSON and can optionally enrich a selected idea through Surfer SEO's MCP server.

The plugin follows one deliberate pipeline:

```text
transcripts → insights → opportunities → human selection → brief → draft
```

It never publishes content and does not put an OpenAI API key in Python. Codex performs the semantic work; the bundled Pydantic helpers validate evidence, references, scoring, and state before persistence.

## Requirements

- Codex or ChatGPT with local plugin support
- Python 3.11+
- `uv` (recommended), or a virtual environment with `requirements.txt` installed
- A Surfer account only for optional SEO enrichment; OAuth is handled by the bundled MCP connection

## Local development

From this plugin directory:

```bash
uv sync
uv run python -m unittest discover -s tests -v
```

The skill normally runs the scripts for you. To inspect a workspace manually:

```bash
UV_PROJECT_ENVIRONMENT=/path/to/project/.infotocontent/.venv \
  uv run --project . python scripts/validate.py \
  --state-dir /path/to/project/.infotocontent
```

## State

The plugin writes only inside the active project by default:

```text
.infotocontent/
├── insights.json
├── website_dna.json
├── opportunities.json
├── surfer/<opportunity_id>.json
├── briefs/<opportunity_id>.json
└── drafts/<opportunity_id>.md
```

Candidate JSON is validated before these files are replaced, and writes are atomic.

## Try it

After installing the plugin, start a new Codex conversation in a project containing transcript files and say:

> Analyze these customer call transcripts and show me what we should write about.

Then select one of the persisted opportunities:

> Write #2 using our website voice and Surfer.

Codex will stop for selection unless your request already names an opportunity.

## Packaging

The plugin root contains the required `.codex-plugin/plugin.json`, one model-invoked skill under `skills/`, deterministic Python helpers under `scripts/`, and an optional Surfer MCP declaration in `.mcp.json`. That is the complete installable package; generated workspace state is intentionally excluded.
