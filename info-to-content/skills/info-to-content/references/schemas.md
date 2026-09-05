# Candidate schemas

Candidate files are temporary model output. The Python helpers validate and canonicalize them before state is written. Extra fields are rejected.

## Insights

Use a JSON array or `{ "insights": [...] }`:

```json
[
  {
    "id": "candidate-1",
    "type": "pain",
    "statement": "Teams cannot see why retrieval quality changed.",
    "topic": "RAG observability",
    "evidence": [
      {
        "source_id": "call-acme-2026-09-01",
        "quote": "We have no idea why retrieval got worse last week.",
        "speaker": "Customer",
        "timestamp": "18:42"
      }
    ],
    "occurrence_count": 1
  }
]
```

Allowed `type` values are `question`, `pain`, `objection`, `use_case`, and `customer_language`. Candidate IDs are required but replaced with stable `ins_...` IDs. Quotes must occur verbatim apart from whitespace and typographic quote normalization in the named transcript.

## Website DNA

```json
{
  "company_description": "Acme helps AI teams evaluate retrieval systems.",
  "target_audience": "AI platform and ML engineering teams",
  "products": ["RAG evaluation platform"],
  "tone": ["technical", "direct", "evidence-led"],
  "existing_topics": ["RAG evaluation basics", "retrieval metrics"]
}
```

Keep this lightweight and observable. Empty lists and a `null` audience are valid.

## Opportunities

Use a JSON array or `{ "opportunities": [...] }` with 3–5 items:

```json
[
  {
    "id": "candidate-1",
    "title": "How to Debug Retrieval Quality Regressions",
    "angle": "A practical diagnostic workflow grounded in the visibility gaps customers describe.",
    "target_audience": "ML engineers operating RAG systems",
    "insight_ids": ["ins_123456789abc"],
    "evidence_strength": 0,
    "why_now": "Multiple calls show that production visibility is blocking reliable evaluation."
  }
]
```

Candidate IDs and evidence scores are replaced deterministically. Every insight ID must already exist.

## Surfer context

Available:

```json
{
  "available": true,
  "target_keyword": "rag observability",
  "recommended_terms": ["retrieval quality", "production monitoring"],
  "target_word_count": 1800,
  "content_score": null,
  "unavailable_reason": null
}
```

Unavailable:

```json
{
  "available": false,
  "target_keyword": null,
  "recommended_terms": [],
  "target_word_count": null,
  "content_score": null,
  "unavailable_reason": "Surfer authentication was not completed"
}
```

Never infer missing SEO terms, word counts, or scores.

## Brief

```json
{
  "title": "How to Debug Retrieval Quality Regressions",
  "audience": "ML engineers operating RAG systems",
  "angle": "A practical diagnostic workflow grounded in customer visibility gaps.",
  "supporting_insight_ids": ["ins_123456789abc"],
  "key_customer_pains_questions": ["Teams cannot see why retrieval quality changed."],
  "required_points": [
    "Define the observable symptoms of a retrieval regression",
    "Show a step-by-step diagnostic workflow"
  ],
  "seo_terms": [],
  "target_word_count": null,
  "surfer_available": false
}
```

The helper overwrites title, audience, angle, SEO terms, word count, and Surfer availability from validated upstream state. All supporting IDs must belong to the selected opportunity.
