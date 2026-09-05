# Track 4 — Landing Site: The Public Front Door

One of four parallel tracks (Track 1 = orchestration pipeline, Track 2 = Mirality model-agnostic backend, Track 3 = Mirality site as publish target). This is the newest track and the one Oleg is building himself.

## TL;DR

Build a public landing page whose only job is: explain the pipeline in plain language, then let a visitor pick their path — **Codex** (install the GitHub skill) or **ChatGPT** (connect the app — stretch, may ship as "coming soon"). Built as an actual **ChatGPT Site**, not a hand-coded page — that satisfies the hackathon submission form's "link to the ChatGPT site" field honestly, and doubles as the real distribution surface.

## Why a ChatGPT Site specifically

The submission form asks for "Link to the ChatGPT site where it was created" — a literal reference to OpenAI's **ChatGPT Sites** feature (public beta since 2026-07-09, Plus/Pro/Work): describe a page to ChatGPT, it generates and hosts a working site at a `chatgpt.com/s/...` URL, no separate deploy step. Building the landing page there instead of hand-rolling one makes the submission real, not a workaround — and it's fast, since the whole page is one generation prompt plus edits.

Build it at: `chatgpt.com` → Sites → describe the page (spec below) → publish → copy the `chatgpt.com/s/...` URL into the submission form.

## Audience + goal

Two visitor types, one page:
- **Codex users** — want to run the raw-signal → Surfer pipeline themselves. CTA: "Connect with Codex."
- **ChatGPT users** — want the same thing without leaving a ChatGPT conversation. CTA: "Connect with ChatGPT."

Goal: a visitor understands what this does and picks a path within ~10 seconds. Not a sales page — a functional router.

## Page content spec

Write in plain, functional product copy — state what it does, no pathos, no dramatic framing, don't over-claim the mechanism (this is the opposite register from LinkedIn brand voice; see `wiki/career/brand/strategy.md` for that voice — don't use it here).

1. **Headline** — one sentence, states the function: e.g. "Turn a sales call into SEO-scored content, automatically." (Oleg to finalize exact wording — this is a direction, not final copy.)
2. **One-paragraph explainer** — raw signal in (a call, notes, a transcript) → structured extraction → checked against Surfer's real content gaps → a scored Content Editor draft → a human approves before anything ships. Name the human-approval gate explicitly — it's the credibility line, not a footnote.
3. **Two-path picker**:
   - **Codex** → "Connect with Codex" button/link → points to the GitHub repo's skill folder (Track 1, once Anton packages it — see open item below). Label honestly if the skill isn't packaged yet: link to the repo with a short "how to run it" note instead of a polished install flow.
   - **ChatGPT** → "Connect with ChatGPT" — if the Apps SDK / MCP-backed app isn't built by demo time, label this **"Coming soon"** rather than a dead or fake link. Don't fabricate a working connector.
4. **How it works (short)** — 3-4 steps max, plain language, matches the real pipeline (drop a file → extraction → Surfer match → human approves).
5. **Link back to GitHub repo** — `github.com/ohsuvorav/gtm-hackathon`, visible regardless of which path someone picks.

## Scope — in

- One ChatGPT Site, one URL, live before the demo
- Both CTAs visible; at least one (Codex → GitHub) actually functional
- Plain, accurate copy — no claims the pipeline can't back up yet

## Scope — out

- A hand-coded site (defeats the point — must be a real ChatGPT Site)
- Building the ChatGPT App/Plugin (Apps SDK, MCP-backed) itself — that's a separate, heavier track; this page only needs to link to it or mark it "coming soon"
- Any account creation, auth, or signup flow on the page itself
- Polishing beyond what a single ChatGPT Sites generation + a couple of edit passes produces

## Constraints

- Copy must stay accurate to what's actually built at demo time — if the Codex skill isn't packaged yet, say "here's the repo" not "click to install"
- No auto-publish claims — the human-approval gate is a stated feature, not a caveat buried at the bottom

## Open items (depend on the other tracks)

- [ ] Track 1's GitHub skill packaging (Anton, later) — once it exists, swap the "Connect with Codex" link from "here's the repo" to a real install step
- [ ] ChatGPT App/Plugin (Apps SDK) — stretch; page ships with "Coming soon" if it doesn't land in time
- [ ] Final headline + explainer copy — draft above is a direction, not locked

## Build steps (Oleg, in ChatGPT directly)

1. Open ChatGPT → Sites → new site
2. Paste the page content spec above as the generation prompt (adapt headline/copy as needed)
3. Review the generated page — check it didn't invent claims beyond what's in this spec
4. Publish, grab the `chatgpt.com/s/...` URL
5. Paste that URL into the hackathon submission form's "Link to the ChatGPT site" field
6. Add the URL to this repo's README so it's discoverable alongside the GitHub artifact

## Demo tie-in

This page is the opening beat of the demo: "here's where anyone starts" → then walk through Track 1's pipeline live → close back on this page's human-approval framing.
