---
name: info-to-content
description: Turn customer call transcripts into grounded customer insights, content opportunities, content briefs, and Markdown drafts, optionally enriched with website context and Surfer SEO. Use when the user provides sales or customer calls for content research, asks what to write based on customer evidence, wants website DNA captured, or asks to draft a selected evidence-backed content idea.
---

# InfoToContent

Run an evidence pipeline with a human choice between discovery and drafting:

`transcripts → insights → opportunities → selected opportunity → brief → draft`

Never skip an artifact. Never publish content.

## Setup

Find this skill's installed `SKILL.md`, then treat the directory two levels above it as `PLUGIN_ROOT`. Keep the Python environment inside the active workspace so an installed plugin can remain read-only. Run every helper with:

```bash
UV_PROJECT_ENVIRONMENT="$PWD/.infotocontent/.venv" \
  uv run --project <PLUGIN_ROOT> python <PLUGIN_ROOT>/scripts/<script>.py ...
```

If `uv` is unavailable, create a Python 3.11+ virtual environment and install `<PLUGIN_ROOT>/requirements.txt`. Keep state in the user's current workspace at `.infotocontent/` unless they name another directory.

Read [schemas.md](references/schemas.md) before producing a candidate JSON file. Read [surfer.md](references/surfer.md) only when the user requests SEO enrichment or Surfer is needed for a selected opportunity.

## Route

Choose the earliest incomplete stage implied by the request:

- Transcript files or pasted transcripts: run **Insights**.
- Website URL or supplied website copy: run **Website DNA**.
- “What should we write?” or equivalent: ensure insights and website DNA exist, then run **Opportunities**.
- A selected opportunity or “write #N”: run **Brief**, then **Draft**.
- A status or validation request: run `validate.py` and summarize the present artifacts.

When the user requests an end-to-end run and supplies everything, continue through discovery, present the opportunities, and stop for selection. Continue past selection in the same turn only when the user already identified one unambiguously.

## Insights

1. Give every transcript a short stable `source_id`. For pasted text, save it verbatim to a workspace file first.
2. Extract questions, pains, objections, use cases, and distinctive customer language. Each insight needs at least one exact quote copied from a transcript.
3. Semantically merge obvious paraphrases before creating candidate JSON. Preserve every supporting quote and source ID.
4. Run `extract_insights.py` with one `--transcript SOURCE_ID=PATH` per source. Omit `--replace` to merge with existing insights.
5. Load the saved `insights.json` and report the count plus a compact sample.

This stage is complete only when the helper exits successfully and every persisted insight has verified transcript evidence.

## Website DNA

1. For a URL, inspect the public homepage and the smallest useful set of product/about/resource pages. For supplied copy, use only that copy.
2. Capture what the company does, target audience, products, observable tone, and existing content topics. Use `null` or empty lists when evidence is absent.
3. Run `build_website_dna.py` and confirm the saved path.

This stage is complete only when `website_dna.json` validates. Describe uncertainty instead of filling gaps with guesses.

## Opportunities

1. Require both `.infotocontent/insights.json` and `.infotocontent/website_dna.json`.
2. Propose 3–5 distinct opportunities. Prioritize repeated evidence, company and audience relevance, and novelty against `existing_topics`.
3. Cite only persisted insight IDs. Supply a provisional score; Python recalculates it from occurrence counts and ranks the result.
4. Run `discover_opportunities.py`, then present its saved order with IDs, titles, angles, evidence scores, and a one-line rationale.
5. Ask the user which one to write.

This stage is complete when 3–5 opportunities validate and are persisted. Stop here unless selection was already explicit.

## Brief

1. Resolve a selection such as `#2` against the current persisted ordering and state its opportunity ID.
2. Load the selected opportunity and its supporting insights.
3. If requested, obtain Surfer context using [surfer.md](references/surfer.md). Always create a Surfer context record, including an explicit unavailable record on fallback.
4. Build a candidate brief grounded only in the selected opportunity. Required points must trace to supporting insights, website DNA, or clearly framed general explanation.
5. Run `build_brief.py` with `--surfer-context` when a context file exists. The helper locks title, audience, angle, SEO terms, and target length to validated upstream state.

This stage is complete only when both the brief and the Surfer availability record are persisted.

## Draft

1. Run `prepare_draft_context.py` and draft only from the returned bundle.
2. Follow the brief and website tone. Use SEO terms naturally. Treat customer quotes as grounding, not permission to expose identities or invent prevalence.
3. Audit every customer-specific claim: it must be supported by one of the bundled insights. Remove unsupported statistics, outcomes, testimonials, and claims of frequency.
4. Save Markdown to a staging file and run `save_draft.py`.
5. Return the draft path, the brief path, and any Surfer limitation. Leave publishing to the user.

This stage is complete when a non-empty Markdown draft beginning with a heading is saved and `validate.py` passes.

## Recovery

When a helper rejects a candidate, fix the candidate rather than editing persisted JSON by hand. When an upstream artifact changes, regenerate its downstream opportunities, briefs, and drafts before presenting them as current.
