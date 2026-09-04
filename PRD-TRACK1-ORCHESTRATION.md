# Track 1 — Orchestration: Raw Data → Webhook → Surfer Content

One of three parallel tracks (see PRD-TRACK2-MIRALITY-APP.md, PRD-TRACK3-MIRALITY-SITE.md). This is the standalone pipeline piece — it doesn't depend on the other two tracks shipping first.

Implements the Surfer half of the architecture defined in DATAFLOW.md — that doc is the source of truth for the overall shape (input sources, extraction contract, human-approval gate); this PRD is the scoped build against it, not a parallel spec.

## Problem

No automated bridge exists between real GTM signal (calls, Slack, notes) and content creation in Surfer. Today it's manual: someone reads a call transcript, someone separately opens Surfer and decides what to write. Nothing connects the two.

## Solution (what)

A webhook-triggered pipeline: raw data lands → gets extracted into structured signal → checked against Surfer's Topical Map for a matching content gap → a Content Editor doc gets created for that gap, scored by Surfer's own engine.

## Flow

1. Webhook receives raw input (file, pasted text, or a future push integration — source-agnostic, per DATAFLOW.md)
2. Extraction step: raw text → structured signal (topic, objection, buyer language, competitor, source/timestamp)
3. Read Surfer's Topical Map (read-only, no write API exists — confirmed via Surfer's own docs)
4. Match signal against an open gap in the map
5. If matched: call Surfer's Content Editor creation for that keyword
6. Return the doc + its SEO/AI-Search/total score
7. Surface for human approval (no auto-publish)

## Scope — in

- Webhook receiver (n8n, per PRD-1.5-DAYS-BUILD.md's decision)
- Extraction node (LLM-based, structured output)
- Surfer MCP calls: read Topical Map, create Content Editor doc, fetch score
- Human-approval surface (Slack message, email, or n8n's own approval node — pick fastest to wire)

## Scope — out

- Editing/generating the Topical Map itself (dashboard-only, confirmed no API)
- Auto-publishing content
- Any input source beyond file/pasted text for v1

## Constraints

- Agent-first, human approves every write
- Build on Surfer's existing MCP — no custom content-scoring logic
- One shared signal object — this track's extraction output should be reusable by Track 2, not a separate extraction implementation

## Risk

- Topical Map matching logic (step 4) has no confirmed automated approach yet — worth checking whether Surfer's own "recommendations" capability (get suggested pages to write) can substitute for manually reading the map and matching by hand
- Surfer workspace access already confirmed live (`1385655-ohsuvorav`) — no blocker here

## Build order

1. Confirm Surfer MCP tool calls work against the real workspace (Content Editor creation, score fetch)
2. Build extraction node, test on a real transcript/notes sample
3. Wire webhook → extraction → Surfer call chain
4. Add approval surface
5. End-to-end run, fix rough edges
