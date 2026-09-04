# Brand Asset Refresher — PRD

Hackathon: Codex Build (2026-09-04, 15:30–17:15) — track: Reinvent Go-To-Market

## Problem

AI made it trivial to ship, so every solution's pitch sounds the same. Winning now takes going the extra mile with the customer — but in complex B2B, sales runs disconnected from marketing and product. Branded, demo-ready assets are rare. Keeping them up to date is rarer. Personalizing them per customer barely happens at all.

## Problem cost

- Reps walk into calls with materials that don't reflect the current product, a competitor's move, or the specific buyer in front of them — the pitch reads generic, credibility drops before the demo even starts.
- Nobody owns catching this before the call. The gap surfaces only after the deal is lost, as "not a fit" feedback — too late to fix.
- Cost compounds two ways: rep time wasted patching decks ad hoc (or not patching them, and eating the loss silently), and deals lost to a competitor who simply felt more "made for me."

## Solution (what)

Rep gives a customer domain → agent pulls that brand's colors/logo → updates a pre-built Paper.design demo template → regenerated, on-brand asset ready to use. No manual Figma/design work per demo.

## How it works — flow

1. Rep DMs the agent in Slack with the customer URL (this is the trigger — agent reads it via a Slack MCP connection, e.g. this workspace's `D06AE9JPUVB` DM as the test channel)
2. Agent fetches the site, extracts: primary color (theme-color meta tag or dominant CSS color), logo (favicon/og:image)
3. Agent calls Paper MCP → sets named layer values in the pre-built template (`brand.primary` color token, `logo.slot` image)
4. Paper re-renders the frame → export/screenshot as the "regenerated asset"

## Pre-work (before the build clock starts — do tonight)

- [ ] Build one Paper.design demo template with 2–3 clearly named, parameterized layers (color token + logo placeholder)
- [ ] Confirm Paper MCP can actually **set** those layer values programmatically (not just read) — this is the one unverified link in the whole plan
- [ ] Confirm Codex can read new messages from a Slack DM via MCP (second unverified link — trigger mechanism, not just the render step)

## Scope — in (the 60 min build)

- Color/logo extraction script (fast heuristic: theme-color tag → fallback to dominant color from favicon)
- MCP call to update the template
- One working end-to-end run on a real domain

## Scope — out

- Multiple templates, template picker, style variety
- Perfect color accuracy (heuristic is fine — "reads as branded," not pixel-exact)
- Any UI beyond Slack DM / terminal
- Undo/versioning, multi-user, auth

## Constraints (self-imposed, from GTM stakeholder analysis)

- Agent-first
- Build on top of existing platforms (Paper.design, not a custom design engine)
- Don't delegate decision-making to the agent — rep triggers it, rep uses/discards the result, agent never sends/publishes
- Lean on structured data (color tokens, named layers) over freeform generation

## Risk

Paper MCP's write capability is unverified. Test it tonight before committing the whole hour to this flow.
**Fallback:** if Paper MCP can't set layer values programmatically, swap the render target for a plain SVG/HTML template you control directly — loses the "cool tool" demo factor but keeps the pipeline working end to end.

## Demo script (2 min)

1. DM a real prospect's domain to the agent in Slack
2. Watch it fetch colors/logo live
3. Cut to Paper canvas — frame updates in front of the room
4. Line: "This is what used to be a 20-minute Figma job before every big demo."

## Build order (the 60 min)

1. Verify Paper MCP write works (5 min gut-check, should already be confirmed from tonight's pre-work)
2. Color/logo extraction script — standalone, testable on 2–3 real domains (15–20 min)
3. Wire extraction → Paper MCP call (15–20 min)
4. End-to-end run, fix rough edges (10–15 min)
5. Rehearse the 2-min demo script once (5 min)
