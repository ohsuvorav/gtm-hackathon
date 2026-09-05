---
name: info-to-content
description: Find a customer call in Fyxer or another connected source, compare grounded call insights with an existing Surfer SEO content-gap audit, and create one evidence-backed Markdown draft when a strong match exists. Use for connected-call content creation, Surfer gap matching, or validating InfoToContent state.
---

# InfoToContent

Run a Surfer-first evidence pipeline:

`existing Surfer gaps + connected call → insights → one match or no match → brief → draft`

Surfer gap data is required. A strong match drafts automatically and stops for human review. Never publish.

## Setup

Treat the directory two levels above this file as `PLUGIN_ROOT`. Keep the Python environment inside the active workspace and run helpers with:

```bash
UV_PROJECT_ENVIRONMENT="$PWD/.infotocontent/.venv" \
  uv run --project <PLUGIN_ROOT> python <PLUGIN_ROOT>/scripts/<script>.py ...
```

Use a clean state directory when `.infotocontent/state.json` is missing but legacy artifacts exist. Read [schemas.md](references/schemas.md) before producing candidate JSON.

## Run

### 1. Read the existing Surfer audit

Read [surfer.md](references/surfer.md), then retrieve the selected workspace's completed brand knowledge, optional custom voice, and current `write` recommendations. The website must already be connected and audited in Surfer; this workflow reads that state.

Normalize website DNA with `build_website_dna.py`. Assess every recommendation against that DNA, then run `build_keyword_gaps.py`. Rejected recommendations remain inspectable.

Stop when Surfer is unavailable, brand knowledge is incomplete, recommendations cannot be read, or no viable gaps remain. Report the persisted reason or artifact; transcript-only ideation is outside this workflow.

### 2. Retrieve one call

Read [sources.md](references/sources.md). Resolve exactly one recording from the source named by the user, retrieve its transcript, save the tool response verbatim to a staging file, and run `save_source.py`.

Access only the requested recording. Ask the user to choose when the lookup is ambiguous. A local or pasted transcript follows the same helper path with provider `local`.

### 3. Extract grounded insights

Extract questions, pains, objections, use cases, and distinctive customer language. Every insight needs an exact transcript quote and the current `source_id`.

Run `extract_insights.py` against the persisted transcript at `.infotocontent/sources/<source_id>.txt`. Reprocessing a source replaces its old evidence while preserving other sources.

### 4. Match the best gap

Compare the current call's insights with only the viable gaps in `keyword_gaps.json`. Produce one best match or an explicit no-match candidate, then run `match_opportunity.py`.

A match must use an unchanged viable gap ID, recommendation ID, and keyword; cite current-call insights; include one of their exact quotes; and score at least `0.60`. The helper converts lower confidence to a persisted no-match result.

Stop successfully when no match survives. Do not create speculative alternatives.

### 5. Draft automatically

For a successful match, create a brief candidate and run `build_brief.py`. Run `prepare_draft_context.py` and draft only from its output. Follow the custom voice when available; otherwise use a conservative, direct style and state that fallback in the handoff.

Audit every customer-specific claim against the bundled insights. Save Markdown beginning with a heading through `save_draft.py`, then run `validate.py`.

Return the matched keyword, confidence and rationale, draft and brief paths, validation result, and one `Surfer gap → transcript quote → insight → draft claim` chain.

Creating or updating a Surfer Content Editor is a separate opt-in action because it may consume a credit. Local drafting never requires it.

## Recovery

Fix rejected candidate files and rerun their helper; persisted JSON is validator-owned. Upstream source or match changes invalidate that source's older opportunity, brief, draft, and topic-level Surfer context.
