# InfoToContent v2 — Surfer-first connected-call specification

## Outcome

Given an existing Surfer website audit and one customer call in Fyxer or another connected source, InfoToContent creates exactly one local Markdown draft when—and only when—the call provides grounded evidence for a viable missing-content recommendation. After validation, it offers an explicitly approved handoff into Surfer Drafts.

```text
existing Surfer gaps + one connected call
                    ↓
           best grounded match
                    ↓
             brief → draft
```

No match is a successful outcome. Nothing writes to Surfer without explicit confirmation, and nothing publishes to a website.

## Required flow

1. Read completed brand knowledge and current `write` recommendations from the selected Surfer workspace. The skill does not connect a website or start an audit.
2. Normalize every recommendation into an inspectable viable/rejected gap report. Surfer IDs and metrics are copied, difficulty is converted from basis points, and ICP relevance is judged against Website DNA.
3. Resolve one user-identified recording from a connected source. Fyxer is the demo adapter. Retrieve only that transcript and persist it verbatim with provider provenance and a content hash.
4. Extract exact-quote customer insights independently from the transcript.
5. Select one best viable Surfer gap or persist an explicit no-match. A match requires current-call insights, one exact linked quote, and confidence of at least `0.60`.
6. A successful match automatically creates one opportunity, brief, and local Markdown draft. There is no opportunity list or selection gate.
7. Validate `Surfer gap → source quote → insight → match → opportunity → brief → draft`, then return the artifact paths and one visible evidence chain.
8. Ask whether to **Publish to Surfer Drafts**. Explain whether the handoff will consume one Content Editor credit or overwrite a linked editor's current body. No Surfer mutation occurs without explicit confirmation.
9. After confirmation, reuse the recommendation's linked editor or create one idempotently, write the validated Markdown with `content__update`, and verify the stored document with `content__get`.

Surfer unavailability, incomplete audit data, zero viable gaps, missing/ambiguous source data, and no strong match stop before drafting. Transcript-only ideation is not a fallback.

## Boundaries

- Surfer and the call source authenticate through their own MCP/app connections.
- Fyxer is not bundled as a mandatory plugin MCP server; the host session supplies it.
- Local or pasted transcripts remain supported through the same source-provenance helper.
- Custom voice is optional and has an explicit conservative fallback.
- Creating or updating a Surfer Content Editor requires separate opt-in. Creation consumes one Content Editor credit; updating replaces the editor's entire body.
- "Publish to Surfer Drafts" writes only to a Surfer Content Editor. Website and CMS publishing remain outside the product.

## State contract

State uses schema version 2 under `.infotocontent/`. It stores raw Surfer responses, normalized DNA and gaps, source metadata and verbatim transcripts, grounded insights, per-source match decisions, opportunities, briefs, and drafts.

At most one opportunity exists per source. Reprocessing that source replaces its evidence and invalidates its previous downstream content. Legacy unversioned state is rejected rather than silently mixed with v2.

## Acceptance

A demo passes when a clean ChatGPT/Codex session accepts `$info-to-content:info-to-content <recording-name>`, reads an existing Surfer audit before transcript analysis, resolves exactly one exact-title Fyxer recording, displays the unchanged missing keyword and exact customer quote, creates exactly one validated draft for a relevant call, creates none for an irrelevant call, performs no Surfer mutation without immediate explicit opt-in, and—when approved—writes and verifies that draft in one reused or idempotently created Surfer Content Editor without publishing to a website.
