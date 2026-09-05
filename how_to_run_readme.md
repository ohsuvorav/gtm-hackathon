# How to run

Turns one raw conversation into one SEO-targeted draft, grounded in what a buyer actually
said, and stops for a human. Nothing publishes, ever.

## Quick start

```bash
python3 run.py
```

No API keys, no dependencies, no network. Every stage reads a fixture. Takes under a second
and writes four files to `data/out/`.

To see the pipeline correctly refuse to produce content:

```bash
SIGNAL_FIXTURE=signal_nomatch.json python3 run.py
```

Requires Python 3.10+ (uses `X | None`). Developed on 3.14.2. Standard library only in
fixture mode; `openai` is imported lazily and only when a stage runs live.

## What runs, in what order

| # | Stage | Module | Reads | Writes |
|---|---|---|---|---|
| 0 | ingest | `run.py` | `data/inbox/*`, else `data/call_transcription.md` | — |
| 4 | site DNA | `stage4_dna.py` | `fixtures/site_dna.json` | — |
| 2 | content gaps | `stage2_gaps.py` | the Surfer CSV + DNA | `out/gaps.json` |
| 1 | primed extraction | `stage1_extract.py` | transcript + gaps + DNA | `out/signal.json` |
| 6 | compose | `stage6_compose.py` | DNA + gaps + signal | `out/system_prompt.md` |
| 7 | draft | `stage7_draft.py` | the system prompt | `out/draft.md` |
| 8 | Surfer push | `stage8_surfer.py` | — | — (no-op) |
| 9 | approval | `stage9_approve.py` | the draft | — |

**Stage 4 runs before stage 2 on purpose.** The gap filter needs the ICP to tell an on-topic
cluster from an off-topic one — metrics alone cannot. This inverts the order in
`PRD-TRACK1-ORCHESTRATION.md`.

Stage 1 is a single primed pass: extraction and gap-matching happen in one call, with the gap
list in context. There is no separate matching stage.

**Stages 3 and 5 do not exist.** 3 was the standalone matching stage, absorbed into 1. 5 is
past-post fetching, never built — see Known gaps.

## Fixture vs live

Every stage reads `STAGE{n}_SOURCE`, falling back to `PIPELINE_SOURCE`, defaulting to
`fixture`. Flip one at a time so a broken live stage never costs you the rest of the run.

```bash
STAGE7_SOURCE=live python3 run.py                    # only generation is real
STAGE1_SOURCE=live STAGE7_SOURCE=live python3 run.py # extraction and generation
PIPELINE_SOURCE=live python3 run.py                  # everything (stages 4 and 8 will refuse)
```

For live stages 1 and 7:

```bash
pip install openai
export OPENAI_API_KEY=...
export OPENAI_MODEL=gpt-5   # optional, this is the default
```

Stages 4 and 8 have no live path from this process — see Assumptions → Surfer MCP.

---

# Assumptions about the data

Everything below is a constraint the code depends on. Break one and the pipeline misbehaves
quietly rather than loudly.

## The Surfer Content Planner CSV

Live file: `data/fixtures/surfer-content-planner-growth product manager-05-09-2026.csv`.
This is a **real export**, not a mock. Its schema was observed, not guessed.

```
Cluster Name, Keyword, Search Volume, Total Cluster Search Volume,
Total Cluster Traffic, Difficulty, Average Cluster Difficulty
```

Four things the parser depends on:

1. **Rows are ragged.** The header declares 9 columns; every data row carries 7. `Relative
   difficulty` and `Relative Cluster Difficulty` are declared and never populated. Unpacking
   positionally against the header raises — `stage2_gaps.py` pads to 7 instead.
2. **There is no gap flag and no URL column.** Surfer's Content Planner does not mark what is
   already covered. "Gap" is *derived* here, not read. The original design in
   `PRD-TRACK1-ORCHESTRATION.md` — match a signal against a flagged gap — has no field to
   match on and could not be built as written.
3. **Cluster-level figures repeat on every row of the cluster.** The parser overwrites rather
   than accumulates them. 301 rows collapse to 28 clusters.
4. **Numeric fields may be blank.** Anything non-numeric parses as 0.

The file is found by glob (`surfer-content-planner-*.csv`), so a new export drops in without a
code change. Only one such file should exist in `data/fixtures/` at a time.

### The data is noisy, and that is expected

Roughly a third of clusters in a real export are unusable. Actual examples from this file:

- `products` — 444,010 searches, difficulty 86–99, second keyword is `define and`
- `ai vs ai` — highest-volume keyword is `marques brownlee` (27,100), a YouTuber
- `linkedin french` — contains `lindin restaurant`, `tango changan`, `sur rup`
- `manager software` — entirely accounting software
- `maturity phase` — mostly macOS Stage Manager
- `udacity`, `contentsquare` — brand-navigational

**Assume any export contains this much garbage.** The filter is not optional cleanup; without
it the top-ranked target is frequently wrong.

## The Surfer brand DNA

Live file: `data/fixtures/site_dna.json`, with a human-readable twin at `data/dna/site_dna.md`.

Six fields, and the key names are the contract that stages 2 and 6 read:

```
business_type, industry, products_services, customer_profile, competitors, topics_to_cover
```

These come from `mcp__surferseo__brand__get({ workspace_id: 1385655 })`.
`stage4_dna.py::from_mcp_response` maps Surfer's labels onto these keys.

Three assumptions that shape everything downstream:

1. **Surfer returns no voice, tone, or style data.** `brand__get` has no such field. Style rules
   in the generated prompt are `stage6_compose.DEFAULT_VOICE` — conservative defaults that were
   invented, not observed. The composer says so in its own output rather than implying the
   voice was derived.
2. **`business_type` currently reads `Unknown / Possibly online presence (inactive)`.** That is
   Surfer reporting a thin crawl. Every other field is a low-confidence inference from it —
   `competitors: Other growth product managers` names no company, `topics_to_cover: Growth
   Product Management` names no subtopic. The composer passes these through as *boundaries*
   ("do not invent beyond this"), not as researched facts.
3. **The ICP vocabulary is derived from three of these fields** — `products_services`,
   `topics_to_cover`, `customer_profile`. Change the DNA and the gap filter changes with it.
   This is the stage 4 → stage 2 dependency, and it is real, not decorative.

## The transcript

Live file: `data/call_transcription.md`. **This is a mock**, hand-authored to match the DNA's
business. Replace it with a real export before the numbers mean anything.

- Any UTF-8 text file works. Format is not parsed — the whole file goes into the prompt.
- YAML frontmatter, speaker labels and timestamps are conventions for humans, not requirements.
- Elided sections (`[00:05:10 – 00:19:30 — comp bands ... Omitted.]`) are deliberate. Real
  exports have gaps; extraction should tolerate them.
- Files in `data/inbox/` take precedence, oldest first.

**Two traps are planted in the mock**, and a working pipeline must survive both:

- The buyer names **Contentsquare**, which is also a real cluster in the CSV. It is unused
  tooling they already pay for, not a competitor and not a content target. The extraction
  prompt forbids treating a merely-mentioned vendor as competitive signal.
- The opening discusses hiring volume in terms that superficially resemble several clusters.
  A keyword-overlap matcher takes the bait; a correct one asks what the buyer meant.

## The signal contract (`signal.json`)

```jsonc
{
  "core":   { "topic", "objection", "buyer_language": [], "competitor" },
  "match":  { "cluster", "keyword", "confidence", "evidence", "rationale" },
  "alternates": []
}
```

- **`core` is map-independent by design.** It describes the conversation and never references a
  keyword. This is what keeps the extraction output reusable by another consumer that does not
  care about Surfer — a constraint carried from `PRD-TRACK1-ORCHESTRATION.md`.
- **`buyer_language` is verbatim quotes only.** Paraphrasing destroys the entire value; the
  specific phrasing is the reason the draft beats a keyword brief.
- **`evidence` must be a verbatim transcript quote.** No quote, no match.
- **`match: null` is a valid, expected result.** Most conversations contain no content
  opportunity. The runner treats it as success and stops.

## Derived values and their thresholds

None of these come from Surfer. All are computed in `stage2_gaps.py` and tunable at the top.

```
opportunity = log10(volume + 1) × (100 − avg_difficulty)/100 × (1 − capture_rate)
capture_rate = cluster_traffic / cluster_volume
icp_relevance = volume-weighted share of keywords containing an ICP term
                and no off-domain term
```

| Constant | Value | Meaning |
|---|---|---|
| `MAX_VIABLE_DIFFICULTY` | 65 | above this, unwinnable without domain authority |
| `HEAD_TERM_DOMINANCE` | 0.6 | one keyword owning this much = head term, not a topic |
| `HEAD_TERM_VOLUME` | 50,000 | national-brand territory regardless of difficulty |
| `already-captured` | 0.5 | half the cluster's volume already landing on the site |
| `MIN_ICP_RELEVANCE` | 0.30 | below this, off-topic |
| `MIN_CONFIDENCE` | 0.6 | in `stage1_extract.py`; below this the match is discarded |

`MIN_ICP_RELEVANCE` is not finely tuned. On this export every legitimate cluster scores ≥ 0.88
and all noise scores ≤ 0.29, so anywhere in that gap works. **That separation is a property of
this dataset, not a guarantee.** Re-check it against a new export.

Current result: **18 viable, 10 rejected.** Rejected clusters are kept in `gaps.json` with a
`rejected_for` list — a filter you cannot inspect is a filter you cannot trust.

## Guards, and why they live in code

Single-pass primed extraction has one known failure: the gap list is in context, so the model
finds a match every time. Instructing it not to does not hold.

`stage1_extract.py::enforce_guards` discards a match on any of three counts and records which:

1. the cluster is not in the viable set (rejected or invented)
2. confidence below `MIN_CONFIDENCE`
3. the evidence quote is empty

`stage6_compose.py` re-checks membership independently and exits rather than composing against
a cluster that is not viable. Model proposes, code disposes.

---

# Known gaps

- **Stage 5 (past posts) does not exist**, so voice is guessed. This is the single largest
  quality gap in the output. 10–20 real posts would fix it.
- **Stage 0 does not track processed files.** It reads the oldest file in the inbox every run
  and neither moves nor marks it. Re-running reprocesses the same file. Fine for a demo,
  wrong for anything scheduled.
- **Stage 8 is unwired.** The Surfer MCP session is unauthenticated — the only tools exposed
  are `authenticate` and `complete_authentication`, so Content Editor tool names are unknown.
  The stage no-ops rather than failing: losing the score should never cost you the draft.
- **Stage 4 has no live path from this process.** MCP tools are called by an agent, not by
  Python. "Live" means an agent runs `brand__get` and writes the result through
  `from_mcp_response()` to the fixture path.
- **The off-domain stoplist is hand-written** against this one export. It will not generalize
  to a different business without editing.
- **`data/fixtures/draft.md` is hand-authored**, not model output. Stage 7 has never run live.
- **`data/dna/mirality-positioning.md` is stale.** Written before the real Surfer output
  arrived, describing a different business entirely. Nothing reads it. Delete it.
- **`PRD-1.5-DAYS-BUILD.md` is superseded** — it specifies n8n and a Mirality branch, both
  dropped. `PRD-TRACK1-ORCHESTRATION.md` is closer, but its stage order and its
  "match against a flagged gap" design are both contradicted by the real export.

# Outputs

| File | What it is |
|---|---|
| `data/out/gaps.json` | all 28 clusters, scored, with rejection reasons |
| `data/out/signal.json` | extracted signal and the match decision |
| `data/out/system_prompt.md` | **the core artifact** — DNA + keyword target + verbatim buyer language |
| `data/out/draft.md` | the draft, awaiting human approval |

Overwritten on every run. Nothing is published by any stage, in any mode.
