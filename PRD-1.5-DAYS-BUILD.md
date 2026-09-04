# GTM Content on Auto-Pilot — 1.5-Day Build v1

Separate scope from PRD.md (brand-asset build) and DATAFLOW.md (the standing architecture doc this is scoped down from). This is the committed, buildable version for the extended submission window (now until end of 2026-09-05).

## Problem

Mirality's own bottleneck — and every complex-B2B GTM team's bottleneck — is the same: content gets written from a blank page, disconnected from what buyers/audience actually say in real conversations. AI made shipping easy, so generic content is worthless; what's scarce is content grounded in real signal.

## Solution (what)

A scheduled pipeline: raw input (call/Slack/notes) → structured GTM signal → two drafts, one for Mirality (LinkedIn), one for the website (Surfer Content Editor, scoped against Surfer's own Topical Map gaps) → human approves before anything publishes.

## Decisions locked for v1 (resolving DATAFLOW.md's open questions)

1. **Orchestrator: n8n.** Chosen over an OpenAI cloud agent — better fit for wiring multiple future input sources without custom glue per source; extraction reasoning still runs through an LLM node inside the n8n flow.
2. **First input source: file upload / pasted text.** Not Slack/Teams yet — keeps v1 buildable without a new integration dependency. Slack/Teams/auto-push are v2 extensions once the core pipeline proves out.
3. **Surfer scoping approach:** Codex/n8n reads the Topical Map read-only (no write access exists), matches extracted signal against a gap the map already flagged, then calls Content Editor creation for that specific keyword. No attempt to edit the map itself.
4. **Mirality entry point:** needs a programmatic draft-trigger check against `apps/mirality` before building — flagged as the first build task, not assumed to exist yet.

## Flow

1. Upload/paste a transcript or notes file into the n8n workflow's input trigger
2. Extraction node: pulls structured signal — topic, objection/question, buyer's language, competitor (if any)
3. Fan-out to two branches:
   - **Mirality branch** — signal → Mirality draft-trigger (pending verification it exists) → new post draft
   - **Surfer branch** — signal → check against Topical Map gaps (read) → Content Editor creation for a matching gap → Surfer score returned
4. Both drafts land somewhere for human review (Slack message, n8n's own approval node, or a simple email — pick whichever is fastest to wire)
5. Human approves → draft is marked ready to publish manually (v1 does not auto-publish either track)

## Scope — in

- n8n workflow: file/text input → extraction → two-branch fan-out
- Surfer branch: read Topical Map, create one Content Editor doc against a real gap, return its score
- Mirality branch: confirm/build the draft-trigger entry point, generate one real draft
- One human-approval checkpoint before either output is considered "done" (not published — approved as ready)

## Scope — out (v1)

- Auto-publish to LinkedIn or the live website — human still hits publish manually
- Slack/Teams/auto-push input sources — file upload only for v1
- Editing or generating the Topical Map itself (dashboard-only, no API)
- Woodpecker, Mentic — dropped from this build; this scope is Surfer + Mirality only

## Constraints (carried through every version of this idea)

- Agent-first, but never auto-publishes — human approves every draft
- Build on existing platforms (Surfer, Mirality, n8n) — no custom design/content engine
- Structured data over freeform generation where possible (Topical Map gaps, Surfer scores, not just LLM judgment)

## Build order

1. Verify Mirality has a programmatic draft-trigger (check `apps/mirality` for an API/webhook) — if none exists, build the minimal one needed
2. Verify Surfer MCP can create a Content Editor doc and return a score, using the already-connected workspace (`1385655-ohsuvorav`)
3. Build the n8n extraction node — raw text in, structured signal out
4. Wire the two-branch fan-out (Mirality + Surfer) off the extraction node's output
5. Add the human-approval checkpoint
6. End-to-end run on a real transcript/notes file, fix rough edges
7. Rehearse the demo: one input file → both drafts appear, both grounded in the same real signal
