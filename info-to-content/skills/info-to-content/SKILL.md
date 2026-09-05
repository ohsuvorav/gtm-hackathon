---
name: info-to-content
description: Find a customer call in Fyxer or another connected source, compare grounded call insights with an existing Surfer SEO content-gap audit, and create one evidence-backed Markdown draft when a strong match exists. Use for connected-call content creation, Surfer gap matching, or validating InfoToContent state.
---

# InfoToContent

Run a Surfer-first evidence pipeline:

`existing Surfer gaps + named Fyxer recording → insights → one match or no match → brief → draft → optional Surfer Drafts handoff`

Surfer gap data is required. A strong match drafts automatically and stops for human review before any Surfer write. Never publish to a website or CMS.

## Invocation

The expected explicit invocation is:

```text
$info-to-content:info-to-content <recording-name>
```

Treat the single positional argument as the title of a Fyxer recording, not as transcript text or a local path. Require a non-empty recording name. Do not reinterpret an unmatched name as another source unless the user explicitly supplies that source or transcript.

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

### 2. Retrieve one call by recording name

Read [sources.md](references/sources.md). Pass the positional recording name to Fyxer `find_recordings`, resolve exactly one exact-title match, retrieve its transcript, save the tool response verbatim to a staging file, and run `save_source.py`.

Access only the requested recording. Ask the user to choose when more than one exact-title match remains. Stop when no exact-title match exists. A local or pasted transcript follows the same helper path with provider `local` only when the user explicitly supplies it instead of using the positional Fyxer form.

### 3. Extract grounded insights

Extract questions, pains, objections, use cases, and distinctive customer language. Every insight needs an exact transcript quote and the current `source_id`.

Run `extract_insights.py` against the persisted transcript at `.infotocontent/sources/<source_id>.txt`. Reprocessing a source replaces its old evidence while preserving other sources.

### 4. Match the best gap

Compare the current call's insights with only the viable gaps in `keyword_gaps.json`. Produce one best match or an explicit no-match candidate, then run `match_opportunity.py`.

A match must use an unchanged viable gap ID, recommendation ID, and keyword; cite current-call insights; include one of their exact quotes; and score at least `0.60`. The helper converts lower confidence to a persisted no-match result.

Stop successfully when no match survives. Do not create speculative alternatives.

### 5. Draft locally and validate

For a successful match, create a brief candidate and run `build_brief.py`. Run `prepare_draft_context.py` and draft only from its output. Follow the custom voice when available; otherwise use a conservative, direct style and state that fallback in the handoff.

Audit every customer-specific claim against the bundled insights. Save Markdown beginning with a heading through `save_draft.py`, then run `validate.py`. Do not offer the Surfer handoff unless validation succeeds.

### 6. Offer to publish to Surfer Drafts

Read the "Publish to Surfer Drafts" section of [surfer.md](references/surfer.md). After showing the validated result, ask for explicit confirmation immediately before the first Surfer mutation. Use the phrase **Publish to Surfer Drafts** and clarify that this saves into a Surfer Content Editor; it does not publish to the website.

- When the matched recommendation has no `content_editor_id`, state that confirmation will create a Content Editor and consume one Content Editor credit.
- When it already has a `content_editor_id`, state that confirmation will replace that editor's entire current document body and does not create another editor.
- A refusal, ambiguous response, or no response performs no Surfer mutation and leaves the local draft available.

After affirmative confirmation, reuse the linked editor or create exactly one idempotently, write the validated Markdown with Surfer `content__update`, and verify the stored body with `content__get`. Never call Surfer AI Article generation: the locally grounded draft is the content being handed off.

Return the matched keyword, confidence and rationale, draft and brief paths, validation result, one `Surfer gap → transcript quote → insight → draft claim` chain, and—only after a successful handoff—the Content Editor ID, link, and score status.

## Recovery

Fix rejected candidate files and rerun their helper; persisted JSON is validator-owned. Upstream source or match changes invalidate that source's older opportunity, brief, draft, and topic-level Surfer context.
