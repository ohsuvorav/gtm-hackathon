# InfoToContent Codex plugin

InfoToContent finds one named customer call in Fyxer, compares its evidence with an existing Surfer SEO website audit, and creates one reviewable Markdown draft when the call matches a viable missing-content recommendation. With explicit approval, it then saves that validated draft into Surfer Drafts.

The authoritative v2 behavior is defined in [SPEC.md](SPEC.md).

```text
existing Surfer gaps + connected call
                ↓
grounded insights → best match or no match
                ↓
          brief → draft → human review
                            ↓ approved
                     Surfer Drafts
```

Surfer is an upstream requirement, not optional post-selection enrichment. The website must already be connected and audited. The plugin reads current `write` recommendations; it never starts an audit or publishes content to a website.

## Requirements

- Codex or ChatGPT with local plugin support
- Python 3.11+
- `uv` or an environment with `requirements.txt` installed
- A connected and audited Surfer workspace
- A separately connected call source such as Fyxer, or a supplied transcript

Codex performs semantic extraction, relevance assessment, and drafting. Pydantic helpers validate raw-source provenance, exact quotes, Surfer IDs and metrics, and every cross-artifact reference.

## Demo

With Fyxer connected to the session and a recording named `call_transcript`, invoke:

```text
$info-to-content:info-to-content call_transcript
```

The positional argument is the Fyxer recording title. The skill reads Surfer first, resolves exactly one exact-title recording, and either stops with an explicit no-match reason or returns one validated draft with a visible `Surfer gap → call quote → insight → draft` chain.

After successful validation, the skill asks whether to **Publish to Surfer Drafts**. Creating a new Content Editor consumes one credit; reusing an editor replaces its current document body. Only an explicit confirmation permits either mutation. This handoff saves to Surfer's Content Editor and does not publish to the website.

## State

State is versioned and written atomically under the active workspace:

```text
.infotocontent/
├── state.json
├── website_dna.json
├── keyword_gaps.json
├── insights.json
├── sources/<source_id>.{json,txt}
├── surfer/{brand_raw,recommendations_raw,custom_voice}.json
├── matches/<source_id>.json
├── opportunities.json
├── briefs/<opportunity_id>.json
└── drafts/<opportunity_id>.md
```

Validate a run with:

```bash
UV_PROJECT_ENVIRONMENT="$PWD/.infotocontent/.venv" \
  uv run --project /path/to/info-to-content \
  python /path/to/info-to-content/scripts/validate.py
```

Legacy unversioned state is rejected instead of silently mixed with the Surfer-first contract.

## Development

```bash
uv sync
uv run python -m unittest discover -s tests -v
```
