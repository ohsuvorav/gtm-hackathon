# Candidate schemas

Candidate files are temporary model output. Helpers validate and canonicalize them before persistence; extra fields are rejected.

## Website DNA

Pass this candidate with the raw Surfer brand response to `build_website_dna.py`. The helper owns source, workspace, and brand metadata.

```json
{
  "company_description": "Acme helps AI teams evaluate retrieval systems.",
  "target_audience": "AI platform and ML engineering teams",
  "products": ["RAG evaluation platform"],
  "tone": ["technical", "direct"],
  "existing_topics": ["RAG evaluation basics"],
  "business_type": "B2B software",
  "industry": "AI infrastructure",
  "competitors": ["Evaluation platforms"],
  "topics_to_cover": ["RAG testing"],
  "problem_solved": "Unreliable retrieval quality"
}
```

## Recommendation relevance

Cover every ID in the raw Surfer `recommendation__list` response exactly once:

```json
{
  "relevance": [
    {
      "recommendation_id": "12602993",
      "icp_relevant": true,
      "rationale": "The topic concerns the product and its hiring-manager audience."
    }
  ]
}
```

## Insights

```json
[
  {
    "id": "candidate-1",
    "type": "pain",
    "statement": "Teams cannot see why retrieval quality changed.",
    "topic": "RAG evaluation",
    "evidence": [
      {
        "source_id": "fyxer-call-1",
        "quote": "We have no idea why retrieval got worse last week.",
        "speaker": "Customer",
        "timestamp": "18:42"
      }
    ],
    "occurrence_count": 1
  }
]
```

Allowed types are `question`, `pain`, `objection`, `use_case`, and `customer_language`. Quotes must occur verbatim in the persisted transcript.

## Best match

Available:

```json
{
  "source_id": "fyxer-call-1",
  "matched": true,
  "keyword_gap_id": "gap_123456789abc",
  "recommendation_id": "12602993",
  "target_keyword": "rag testing",
  "insight_ids": ["ins_123456789abc"],
  "evidence_quote": "How do we test retrieval before a release?",
  "confidence": 0.88,
  "rationale": "The buyer's unresolved release-testing question directly matches this gap.",
  "opportunity_title": "How to Test RAG Before a Release",
  "angle": "A practical release-readiness workflow grounded in the buyer's uncertainty.",
  "target_audience": "ML engineers",
  "no_match_reason": null
}
```

No match:

```json
{
  "source_id": "fyxer-call-1",
  "matched": false,
  "keyword_gap_id": null,
  "recommendation_id": null,
  "target_keyword": null,
  "insight_ids": [],
  "evidence_quote": null,
  "confidence": null,
  "rationale": null,
  "opportunity_title": null,
  "angle": null,
  "target_audience": null,
  "no_match_reason": "The call does not address any viable Surfer gap."
}
```

## Brief

The helper locks source, gap, keyword, title, audience, angle, SEO terms, and word count from upstream state. The candidate supplies only:

```json
{
  "supporting_insight_ids": ["ins_123456789abc"],
  "key_customer_pains_questions": ["Teams lack a pre-release retrieval test."],
  "required_points": ["Define release criteria", "Show the diagnostic workflow"]
}
```

Optional topic-level Surfer context retains the existing `SurferContext` shape. Its keyword must match the selected gap; unavailable NLP terms or word counts stay empty or `null`.
