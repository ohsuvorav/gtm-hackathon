# Surfer audit input

Use this branch before retrieving or analyzing a call. Surfer provides the website context and the closed set of content gaps the call may match.

## Retrieve

Use the bundled Surfer MCP server. Trigger its normal OAuth flow when required; credentials remain in MCP and never enter Python or workspace files.

Resolve the workspace from an explicit user choice, the only available workspace, or reliable prior context. Ask when multiple workspaces remain ambiguous.

Inspect exposed tool schemas, then read:

- completed brand knowledge for the connected website;
- the selected/default custom voice when available;
- `recommendation__list` with `type="write"`, sorted by Surfer score.

These are read operations. Do not connect a website or start an audit.

## Persist and normalize

Save raw tool responses to temporary JSON files. Build a Website DNA candidate from brand knowledge and run `build_website_dna.py`; omit `--custom-voice` when none exists so the helper records the fallback.

Classify every returned recommendation as on-ICP or off-ICP with a short rationale grounded in Website DNA. Run `build_keyword_gaps.py` with the raw recommendations and complete relevance candidate. The helper copies Surfer metrics, converts difficulty basis points to `0–100`, applies the difficulty guard, and persists viable and rejected gaps.

Never invent missing keywords, metrics, recommendation IDs, terms, word counts, or scores.

## Stops

Surfer connection failure, incomplete brand knowledge, unreadable recommendations, and zero viable gaps are no-content outcomes. Stop and explain the condition instead of using transcript-only topics.

## Publish to Surfer Drafts

This is an optional handoff after a local draft passes `validate.py`. "Publish to Surfer Drafts" means save the draft into a Surfer Content Editor. It never means publish to the brand's website or CMS.

### Resolve the destination before asking

Use the selected viable gap's unchanged `workspace_id`, `target_keyword`, `location`, and `content_editor_id`.

- If `content_editor_id` exists, call `content_editor__get` and, when completed, `content__get` to establish that the handoff will replace the entire existing body. Never create a duplicate editor.
- If `content_editor_id` is absent, the handoff requires `content_editor__create` and one Content Editor credit.

These destination checks are read-only. Do not mutate Surfer yet.

### Approval gate

Ask exactly one clear question after presenting the validated local result and immediately before the first mutation:

- New editor: `Publish this validated draft to Surfer Drafts? This will create a Content Editor for "<target_keyword>" and consume one Content Editor credit. It will not publish to the website.`
- Existing editor: `Publish this validated draft to the existing Surfer Drafts editor <content_editor_id>? This will replace its entire current document body. It will not publish to the website.`

Proceed only on an explicit affirmative response. A refusal, ambiguity, or no response stops the handoff without changing Surfer. Approval from an earlier run or for another draft/editor does not carry over.

### Confirmed handoff

1. Re-read the saved local Markdown from `.infotocontent/drafts/<opportunity_id>.md`; do not regenerate it during the handoff.
2. If a linked editor exists, use it. Otherwise call `content_editor__create` once with the gap's `main_keyword` and `location`, `use_brand_knowledge: true`, and the selected/default `custom_voice_id` when available. Use a stable idempotency key derived from the opportunity ID, and reuse that key after a timeout or unclear failure.
3. Wait for `content_editor__get` to report `completed`. Stop on `failed` or after a bounded timeout, reporting the editor ID so the run can be resumed safely.
4. Call `content__update` with the full validated draft, `format: "markdown"`, the resolved `workspace_id`, and the resolved `content_editor_id`. This is the specific function that publishes the local draft to Surfer Drafts.
5. Call `content__get` with `format: "markdown"` and verify that Surfer stored a non-empty document representing the submitted draft. Surfer sanitizes and re-serializes content, so do not require byte-for-byte equality.
6. Call `content_score__get` once. Report scores whose status is ready and report calculating/unavailable statuses honestly; do not wait indefinitely or rewrite the draft to chase a score.
7. Return the Content Editor ID and an existing edit/comment URL from `permalink__list` when available.

Do not call `ai_article__generate`, Auto-Optimize, permalink creation, or any website/CMS publishing function in this handoff.
