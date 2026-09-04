# Track 2 — Mirality App: Raw Data → Drafted Posts, Model-Agnostic

One of three parallel tracks (see PRD-TRACK1-ORCHESTRATION.md, PRD-TRACK3-MIRALITY-SITE.md). Two sub-goals, not one:
(a) wire the same raw-signal pipeline from Track 1 into Mirality's draft generation
(b) make the generation backend model-agnostic — Codex as a first-class alternative to Claude, not just Claude Agent SDK

## Problem

**(a) No automated feed.** Mirality's `/api/generate` (`apps/mirality/app/api/generate/route.ts`) already takes an `input` string and generates a draft — but only from manual composer input. Nothing feeds it from an external signal source yet.

**(b) Locked to Claude.** Confirmed in the route itself: `ALLOWED_MODELS = Set(["opus", "sonnet", "haiku"])`, Node runtime spawning a local Claude Agent SDK process on Oleg's own Claude Code subscription. A Codex user can't run Mirality's generation today — it's not a UI gap, it's a hardcoded backend dependency.

This isn't starting from zero: BYOA (server/thin-client split) already shipped 2026-07-27 — `apps/mirality-agent` + a public `mirality-client` repo already exist. Open-source distribution infrastructure is real; what's missing is the model-agnostic backend piece specifically.

## Solution (what)

(a) Wire Track 1's extraction output as a valid `input` payload to `/api/generate`, so a real signal (not manual typing) can trigger a draft.
(b) Add a Codex-compatible generation path alongside the existing Claude Agent SDK path — abstract the "run an agent, get a post draft" step behind an interface that either backend can satisfy.

## Scope — in

- A minimal adapter: given the same `input`/prompt contract `/api/generate` already expects, call it programmatically (not through the UI) — this is Track 1's actual hookup point into Mirality
- Investigate `runGeneration` / `startAgentTurn` (`lib/agent-turn.ts`) to find the actual seam where "which agent runs this" is decided — that's where a Codex branch gets added
- A working Codex-backed generation path for at least the `write` mode (not every mode — `ask`/`agent`/`refine` can stay Claude-only for v1)

## Scope — out

- Full multi-model support across every mode (ask, agent, refine, hunk-mode) — v1 is `write` mode only
- Any UI work beyond what's needed to prove the backend swap works
- Rebuilding BYOA/open-source infra that already shipped

## Constraints

- Don't break the existing Claude Agent SDK path — this is additive, not a replacement
- Model-agnostic means a real abstraction (an interface both backends implement), not an if/else hack that only works once

## Open questions to resolve first

- [ ] Read `lib/agent-turn.ts` and `lib/jobs.ts` to find the exact seam between `/api/generate` and the agent runtime — this determines how invasive the Codex integration is
- [ ] Does Codex expose an SDK/API comparable to `@anthropic-ai/claude-agent-sdk` (spawn a local process, stream results) or does it need a different integration shape entirely?
- [ ] Confirm whether this needs to run live in the hackathon demo, or whether "here's the abstraction, here's Claude working, here's the Codex branch stubbed" is enough to show the direction

## Build order

1. Read `lib/agent-turn.ts`, `lib/jobs.ts`, `lib/prompt.ts` to map the real generation seam
2. Design the minimal backend-agnostic interface (probably: `runGeneration(input, backend: "claude" | "codex")`)
3. Wire Track 1's extraction output into `/api/generate` as a real (not manual) input source
4. Build the Codex branch — even a narrow, single-mode version proves the direction
5. Test both backends produce a real draft from the same signal
