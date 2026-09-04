# Track 3 — Mirality Site: Real Target for Surfer's Content Work

One of three parallel tracks (see PRD-TRACK1-ORCHESTRATION.md, PRD-TRACK2-MIRALITY-APP.md). Grounds Track 1's Surfer output somewhere real instead of a hypothetical site.

## Problem

Track 1 creates Content Editor docs against Surfer's Topical Map — but that only matters if there's a real site to publish onto. `apps/mirality-site` exists (confirmed: a separate Next.js app in design-monorepo, distinct from the `mirality` app itself) but its current structure and whether it has any content/blog surface at all is unconfirmed.

## Solution (what)

Connect Track 1's Surfer-scored content output to `mirality-site` as its actual publish target — most likely a blog/docs section that doesn't fully exist yet, built to receive whatever Track 1 generates.

## Open questions to resolve first (nothing below is scoped until these are answered)

- [ ] Audit `apps/mirality-site/app` structure — what pages exist today, is there already a blog/content route, or does one need to be built from scratch
- [ ] Confirm what `apps/mirality-site` currently is — a static landing page, or does it already pull dynamic content from somewhere
- [ ] Decide the publish mechanism: a CMS-style content collection (MDX files, a `content/` directory) vs. a database-backed post model like `apps/mirality` already has for LinkedIn drafts

## Scope — in (pending the audit above)

- One real page/route on `mirality-site` that can receive a Track-1-generated content draft
- A minimal publish path (even manual: Track 1's output lands as a file, someone commits it) — v1 does not need a full CMS

## Scope — out

- A full blog/CMS rebuild if one doesn't exist — start with the smallest surface that can hold one real piece of content
- Auto-publish — same human-approval constraint as Track 1

## Constraints

- Same as Track 1: agent drafts, human approves before it goes live on the real public site
- Don't duplicate Mirality-app's post infrastructure — this is the company site, not the LinkedIn product

## Build order

1. Audit `apps/mirality-site/app` — read its actual current structure before assuming anything
2. Based on the audit, decide: extend an existing content surface, or build a minimal new one
3. Wire one real Track-1-generated doc through to a page on the live site (or a preview build of it)
4. Confirm the human-approval step actually gates the publish
