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

## Stops and external writes

Surfer connection failure, incomplete brand knowledge, unreadable recommendations, and zero viable gaps are no-content outcomes. Stop and explain the condition instead of using transcript-only topics.

Creating a Content Editor or updating its content is outside the default run. Tell the user it may consume a credit and obtain explicit opt-in immediately before the action.
