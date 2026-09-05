# Surfer enrichment

Use this branch only after an opportunity is selected and the user requested SEO or Surfer enrichment.

## Connect

Use the Surfer MCP tools bundled with this plugin. If they expose only authentication tools, trigger the normal OAuth flow and let the user complete browser consent. Resume when the data tools appear. Credentials stay in the MCP OAuth flow; never request, read, or persist them in Python or workspace files.

If authentication is declined, unavailable, or fails, write an unavailable `SurferContext` candidate and continue without SEO enrichment.

## Retrieve

Inspect the currently exposed Surfer tool names and schemas rather than assuming an operation exists. Prefer read-only operations that can return:

- keyword recommendations relevant to the selected title and angle;
- an existing Content Editor for the target topic;
- recommended/NLP terms and target word count;
- a current content score when content already exists in Surfer.

Use the user's selected Surfer workspace. If more than one exists and no reliable prior selection is available, ask which workspace to use.

Create a new Content Editor only when it is necessary for requested enrichment and after telling the user that it may consume a Surfer credit. Updating an editor with a draft is a separate opt-in action; it is never required to create the local brief or draft.

## Normalize

Translate only fields returned by Surfer into the `SurferContext` schema in [schemas.md](schemas.md). Deduplicate terms, preserve numeric values, and use `null` for data Surfer did not return. A pre-draft score is often `null`.

Save the candidate in a temporary file and pass it to `build_brief.py --surfer-context <path>`. The helper persists an inspectable copy under `.infotocontent/surfer/<opportunity_id>.json`.
