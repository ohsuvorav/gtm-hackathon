# Sponsor MCP Plan — Woodpecker / Surfer / Mentic

Separate from PRD.md (the brand-asset build). This tracks the sponsor-tool angle: what each sponsor's MCP actually exposes, access status, and the alternative "GTM Signal Router" concept that leans on all three.

## Why this matters

All three named sponsors (Woodpecker, Surfer, Mentic) now ship MCP servers, not just REST APIs. That means one orchestrating agent (Codex) can hold live connections to multiple sponsor tools without custom integration glue — the protocol does the connecting, the hackathon build is the routing logic on top.

## MCP status (checked 2026-09-03/04 — reconfirm before building)

| Tool | MCP confirmed real? | Source | Access |
|---|---|---|---|
| **Woodpecker** | Yes — official, documented, Docker image, GitHub repo (`Woodpeckerco/woodpecker-mcp-server`) | `developers.woodpecker.co/docs/mcp/` | Self-serve — free trial account gets API/MCP access tonight, no add-on needed |
| **Surfer** | Yes — official | `docs.surferseo.com/en/articles/12944186-surfer-mcp` | Gated to Pro/Peace of Mind/Enterprise tier, no self-serve trial — ask sponsor rep at check-in |
| **Mentic** | Yes — live endpoint, returns 401 unauthenticated (confirms it's real, not vaporware) | `app.mentic.io/api/mcp` | **Self-serve via OAuth connector** — add as a custom connector in Claude (Settings → Connectors → Add custom connector, name "Mentic", URL `https://app.mentic.io/api/mcp`), sign in with a Mentic account, Allow access. Needs Claude Pro/Team/Enterprise. Create a Mentic account at app.mentic.io first if you don't have one — no sales call required. |

## Tool surfaces (what each MCP actually exposes)

**Woodpecker** — campaign create/update/run/pause/delete; add/update/delete/search prospects; add prospects to global list without enrolling; add follow-up steps to sequences; A/B testing; modify campaign settings (mailboxes, daily limits, timezone); campaign stats/performance.

**Surfer** — create Content Editors for target keywords; write articles via Surfer AI (outline approval step); optimize existing content / run Auto-Optimize; check SEO, AI Search, and total content scores; view/adjust guidelines (terms, topics, structure, competitors); optimization + topic recommendations; manage branded workspaces/voices/templates; fetch AI Visibility data from AI Tracker; run built-in "skills" (ready-made workflows).

**Mentic** — surface unconfirmed beyond the live 401 endpoint. No public docs found anywhere (checked mentic.io/docs — 404; checked mcp.so, glama.ai, Pipedream, Composio, GitHub/npm — nothing listed). Marketing copy claims: writes ad strategy, generates creative, buys media placements across Search/Meta/display/video/retargeting, qualifies leads, syncs to CRM (HubSpot/Salesforce/Pipedrive). **Unverified whether any of this is callable read-only/draft-only vs. triggers real spend.** Access is self-serve (OAuth connector, see table above) — so the actual tool list is discoverable by connecting and running `tools/list`, but do not call any write/launch-shaped tool until you've confirmed with their team (or by inspecting each tool's description carefully) that it can't trigger real ad spend.

## Concrete use cases per tool (from deep-dive research, 2026-09-04)

**Woodpecker** — exact tools confirmed from GitHub README (`Woodpeckerco/woodpecker-mcp-server`):
Campaign: `createCampaign`, `createAdvancedCampaign`, `listCampaigns`, `retrieveCampaignDetails`, `retrieveCampaignStatistics`, `updateCampaignSettings`, `buildCampaignUrl`, `runCampaign`, `pauseCampaign`, `stopCampaign`, `deleteCampaign`, `makeCampaignEditable`.
Steps: `addStep`, `updateCampaignStep`, `updateStepVersion`, `deleteCampaignStep`.
Prospects: `addProspectsToDatabase`, `addProspectsToCampaign`, `updateProspectsInDatabase`, `updateProspectsInCampaign`, `listProspectsInDatabase`, `listProspectsInCampaign`, `searchProspects`, `deleteProspects`.
Accounts: `listMailboxes`.

Best pick: **signal → `addProspectsToCampaign`**, objection/language folded into the prospect's custom fields for personalization. Low difficulty, single call, real write.
Other options: live stats digest (`retrieveCampaignStatistics`, low difficulty); objection-driven step injection via `addStep` (medium — payload shape not documented, needs a live `tools/list` check); building a campaign from scratch via `createCampaign` (high difficulty — avoid in the time box).

**Surfer** — no exact tool names published; capabilities confirmed via docs: Content Editor creation, Surfer AI article writing (outline-approval gate), Auto-Optimize, SEO/AI-Search/content scoring, guideline/competitor data, workspace/brand-voice management, AI Visibility (AI Tracker) fetch.

Best pick: **content score audit** — read-only, checks existing marketing pages' SEO/AI-Search scores, needs no write access, safe to run live regardless of tier. Low difficulty.
Other options: objection → Content Editor creation for the matching keyword gap (low-medium, single call but outline-approval adds a round trip); full objection-to-article pipeline (high — outline approval + generation + optimize is multi-turn, budget several minutes).

**Mentic** — no tool names discoverable without connecting live. Best case (if a draft/brief-only tool exists): feed an objection or competitor mention → get back a drafted ad angle for human review. Worst case (nothing safely callable): keep fully narrated in the demo, zero live calls.

## Cross-tool synergy (confirmed by all three research passes independently)

The signal extracted from a sales call — objection, competitor, buyer's exact phrasing — should be **one shared object**, generated once, not re-derived per tool. It becomes:
- the personalization line in Woodpecker's `addProspectsToCampaign` payload
- the keyword target in Surfer's content audit / Content Editor
- (if safe) the brief fed to Mentic for an ad angle

Surfer's content score audit is the best pre-flight companion to either outbound or ads — read-only, fast, no tier risk, good live-demo material even if nothing else is wired.

## Action items before/at the hackathon

- [ ] Tonight: set up Woodpecker trial account, generate API key, confirm MCP server connects
- [ ] Confirm Codex can connect to a local/Docker-hosted MCP server via stdio (Woodpecker's isn't a hosted HTTP endpoint) — harness question, check before the build clock starts
- [ ] At 14:30 check-in: ask Surfer rep for hackathon MCP access (Pro-tier gated)
- [ ] At 14:30 check-in: ask Mentic rep for hackathon MCP access + explicitly ask whether any action can trigger real spend — do not assume draft-only without their confirmation

## Alternative concept: GTM Signal Router

If sponsor access lands for 2–3 of these, the stronger build (vs. the brand-asset PRD) is a **signal router**: agent reads a sales call transcript, extracts structured signal (objection, competitor mentioned, buyer's exact language, deal stage), and routes draft actions to whichever MCPs are live:

- **Woodpecker** → add prospect to a matching campaign, opening line using the buyer's own phrasing
- **Surfer** → content brief / keyword gap matching the objection
- **Mentic** → ad angle addressing the same objection (draft/brief only, never auto-launch)

Every write action requires per-item human approval — the agent never sends/spends/publishes unapproved. This is the stronger pitch if 2+ sponsor MCPs are actually reachable tomorrow; the brand-asset PRD is the fallback if Paper MCP is the only reliable write target.

**Decision point:** pick between this and the brand-asset PRD once Woodpecker's connection is verified tonight and sponsor access is known at check-in — don't build both.
