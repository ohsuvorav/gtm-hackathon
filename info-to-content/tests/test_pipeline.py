from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def write_json(path: Path, payload) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run_script(name: str, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"{name} returned {result.returncode}, expected {expected}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def create_surfer_state(root: Path, *, viable: bool = True) -> Path:
    state = root / ".infotocontent"
    brand = write_json(
        root / "brand.json",
        {
            "id": 14148,
            "url": "https://example.com",
            "gathering_data_status": "completed",
            "knowledge": "**Business Type**\n\nB2B software\n",
        },
    )
    dna = write_json(
        root / "dna.json",
        {
            "company_description": "Acme helps teams evaluate RAG systems.",
            "target_audience": "ML engineers",
            "products": ["RAG evaluation"],
            "tone": ["technical", "direct"],
            "existing_topics": ["RAG basics"],
            "business_type": "B2B software",
            "industry": "AI infrastructure",
            "competitors": [],
            "topics_to_cover": ["RAG testing"],
            "problem_solved": "Unreliable retrieval quality",
        },
    )
    run_script(
        "build_website_dna.py",
        "--candidate", str(dna),
        "--surfer-brand", str(brand),
        "--workspace-id", "1385655",
        "--state-dir", str(state),
    )
    recommendations = write_json(
        root / "recommendations.json",
        {
            "data": [
                {
                    "id": 10,
                    "type": "write",
                    "title": "Testing RAG before release",
                    "main_keyword": "rag testing",
                    "topic_title": "RAG evaluation",
                    "location": "United States",
                    "search_volume": 1200,
                    "avg_difficulty": 216,
                    "score": 7.4,
                    "reasons": ["gap", "low_difficulty"],
                    "content_editor_id": None,
                },
                {
                    "id": 11,
                    "type": "write",
                    "title": "Hard keyword",
                    "main_keyword": "ai",
                    "topic_title": "AI",
                    "location": "United States",
                    "search_volume": 500000,
                    "avg_difficulty": 7000,
                    "score": 9.0,
                    "reasons": ["gap"],
                    "content_editor_id": None,
                },
            ]
        },
    )
    relevance = write_json(
        root / "relevance.json",
        {
            "relevance": [
                {
                    "recommendation_id": "10",
                    "icp_relevant": viable,
                    "rationale": "Directly concerns the product and audience.",
                },
                {
                    "recommendation_id": "11",
                    "icp_relevant": False,
                    "rationale": "Too broad for the product and audience.",
                },
            ]
        },
    )
    run_script(
        "build_keyword_gaps.py",
        "--recommendations", str(recommendations),
        "--relevance", str(relevance),
        "--workspace-id", "1385655",
        "--state-dir", str(state),
    )
    return state


def add_source_and_insights(root: Path, state: Path) -> tuple[Path, list[str]]:
    transcript = root / "fyxer-transcript.txt"
    transcript.write_text(
        "Customer: We cannot tell why retrieval got worse.\n"
        "Customer: How do we test retrieval before a release?\n",
        encoding="utf-8",
    )
    run_script(
        "save_source.py",
        "--source-id", "fyxer-call-1",
        "--provider", "fyxer",
        "--external-id", "recording-77",
        "--title", "call_transcript",
        "--transcript", str(transcript),
        "--state-dir", str(state),
    )
    candidates = write_json(
        root / "insights-candidate.json",
        [
            {
                "id": "one",
                "type": "pain",
                "statement": "Teams lack visibility into retrieval regressions.",
                "topic": "RAG evaluation",
                "evidence": [{
                    "source_id": "fyxer-call-1",
                    "quote": "We cannot tell why retrieval got worse.",
                    "speaker": "Customer",
                }],
                "occurrence_count": 1,
            },
            {
                "id": "two",
                "type": "question",
                "statement": "Teams want pre-release retrieval tests.",
                "topic": "RAG evaluation",
                "evidence": [{
                    "source_id": "fyxer-call-1",
                    "quote": "How do we test retrieval before a release?",
                    "speaker": "Customer",
                }],
                "occurrence_count": 1,
            },
        ],
    )
    saved_transcript = state / "sources" / "fyxer-call-1.txt"
    run_script(
        "extract_insights.py",
        "--candidates", str(candidates),
        "--transcript", f"fyxer-call-1={saved_transcript}",
        "--state-dir", str(state),
    )
    insights = json.loads((state / "insights.json").read_text())
    return saved_transcript, [item["id"] for item in insights]


class PipelineTests(unittest.TestCase):
    def test_rejects_quote_that_is_not_in_connected_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = create_surfer_state(root)
            transcript = root / "call.txt"
            transcript.write_text("The actual customer statement.", encoding="utf-8")
            run_script(
                "save_source.py",
                "--source-id", "fyxer-call-1",
                "--provider", "fyxer",
                "--external-id", "recording-77",
                "--title", "call_transcript",
                "--transcript", str(transcript),
                "--state-dir", str(state),
            )
            candidates = write_json(
                root / "insights.json",
                [{
                    "id": "candidate",
                    "type": "pain",
                    "statement": "A made-up pain.",
                    "topic": "Testing",
                    "evidence": [{"source_id": "fyxer-call-1", "quote": "This was never said."}],
                    "occurrence_count": 1,
                }],
            )
            result = run_script(
                "extract_insights.py",
                "--candidates", str(candidates),
                "--transcript", f"fyxer-call-1={state / 'sources' / 'fyxer-call-1.txt'}",
                "--state-dir", str(state),
                expected=2,
            )
            self.assertIn("quote not found", result.stderr)

    def test_complete_surfer_first_pipeline_persists_evidence_chain(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = create_surfer_state(root)
            _, insight_ids = add_source_and_insights(root, state)
            gap = json.loads((state / "keyword_gaps.json").read_text())["viable"][0]
            match = write_json(
                root / "match.json",
                {
                    "source_id": "fyxer-call-1",
                    "matched": True,
                    "keyword_gap_id": gap["id"],
                    "recommendation_id": gap["recommendation_id"],
                    "target_keyword": gap["target_keyword"],
                    "insight_ids": insight_ids,
                    "evidence_quote": "How do we test retrieval before a release?",
                    "confidence": 0.91,
                    "rationale": "The call asks for the exact capability represented by this gap.",
                    "opportunity_title": "How to Test RAG Before a Release",
                    "angle": "A release-readiness workflow grounded in customer uncertainty.",
                    "target_audience": "ML engineers",
                    "no_match_reason": None,
                },
            )
            run_script("match_opportunity.py", "--candidate", str(match), "--state-dir", str(state))
            opportunity = json.loads((state / "opportunities.json").read_text())[0]
            brief_candidate = write_json(
                root / "brief.json",
                {
                    "supporting_insight_ids": insight_ids,
                    "key_customer_pains_questions": ["Teams cannot verify retrieval before release."],
                    "required_points": ["Define a pre-release test", "Show a diagnostic workflow"],
                },
            )
            run_script(
                "build_brief.py",
                "--opportunity-id", opportunity["id"],
                "--candidate", str(brief_candidate),
                "--state-dir", str(state),
            )
            draft_context = root / "draft-context.json"
            run_script(
                "prepare_draft_context.py",
                "--opportunity-id", opportunity["id"],
                "--output", str(draft_context),
                "--state-dir", str(state),
            )
            context = json.loads(draft_context.read_text())
            self.assertEqual(context["source"]["provider"], "fyxer")
            self.assertEqual(context["keyword_gap"]["target_keyword"], "rag testing")
            draft = root / "draft.md"
            draft.write_text("# How to Test RAG\n\nGrounded article.", encoding="utf-8")
            run_script(
                "save_draft.py",
                "--opportunity-id", opportunity["id"],
                "--draft", str(draft),
                "--state-dir", str(state),
            )
            result = run_script("validate.py", "--state-dir", str(state))
            self.assertIn("sources=1", result.stdout)
            self.assertIn("opportunities=1", result.stdout)
            self.assertIn("drafts=1", result.stdout)

    def test_low_confidence_is_a_successful_no_match(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = create_surfer_state(root)
            _, insight_ids = add_source_and_insights(root, state)
            gap = json.loads((state / "keyword_gaps.json").read_text())["viable"][0]
            candidate = write_json(
                root / "match.json",
                {
                    "source_id": "fyxer-call-1",
                    "matched": True,
                    "keyword_gap_id": gap["id"],
                    "recommendation_id": gap["recommendation_id"],
                    "target_keyword": gap["target_keyword"],
                    "insight_ids": insight_ids,
                    "evidence_quote": "How do we test retrieval before a release?",
                    "confidence": 0.40,
                    "rationale": "Weak relationship.",
                    "opportunity_title": "Weak idea",
                    "angle": "Weak angle",
                    "target_audience": "ML engineers",
                },
            )
            result = run_script("match_opportunity.py", "--candidate", str(candidate), "--state-dir", str(state))
            self.assertIn("No content match", result.stdout)
            self.assertEqual(json.loads((state / "opportunities.json").read_text()), [])
            self.assertFalse(list((state / "briefs").glob("*.json")))

    def test_rejected_gap_cannot_be_matched(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = create_surfer_state(root)
            _, insight_ids = add_source_and_insights(root, state)
            gap = json.loads((state / "keyword_gaps.json").read_text())["rejected"][0]
            candidate = write_json(
                root / "match.json",
                {
                    "source_id": "fyxer-call-1",
                    "matched": True,
                    "keyword_gap_id": gap["id"],
                    "recommendation_id": gap["recommendation_id"],
                    "target_keyword": gap["target_keyword"],
                    "insight_ids": insight_ids,
                    "evidence_quote": "How do we test retrieval before a release?",
                    "confidence": 0.90,
                    "rationale": "Invalid target.",
                    "opportunity_title": "Invalid target",
                    "angle": "Invalid angle",
                    "target_audience": "ML engineers",
                },
            )
            result = run_script(
                "match_opportunity.py", "--candidate", str(candidate), "--state-dir", str(state), expected=2
            )
            self.assertIn("viable keyword gap", result.stderr)

    def test_changed_source_invalidates_its_insights_match_and_opportunity(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = create_surfer_state(root)
            _, insight_ids = add_source_and_insights(root, state)
            gap = json.loads((state / "keyword_gaps.json").read_text())["viable"][0]
            candidate = write_json(
                root / "match.json",
                {
                    "source_id": "fyxer-call-1",
                    "matched": True,
                    "keyword_gap_id": gap["id"],
                    "recommendation_id": gap["recommendation_id"],
                    "target_keyword": gap["target_keyword"],
                    "insight_ids": insight_ids,
                    "evidence_quote": "How do we test retrieval before a release?",
                    "confidence": 0.90,
                    "rationale": "Direct match.",
                    "opportunity_title": "Test RAG before release",
                    "angle": "A practical workflow.",
                    "target_audience": "ML engineers",
                },
            )
            run_script("match_opportunity.py", "--candidate", str(candidate), "--state-dir", str(state))
            replacement = root / "replacement.txt"
            replacement.write_text("Customer: This call is about procurement.", encoding="utf-8")
            run_script(
                "save_source.py",
                "--source-id", "fyxer-call-1",
                "--provider", "fyxer",
                "--external-id", "recording-77",
                "--title", "call_transcript",
                "--transcript", str(replacement),
                "--state-dir", str(state),
            )
            self.assertEqual(json.loads((state / "insights.json").read_text()), [])
            self.assertEqual(json.loads((state / "opportunities.json").read_text()), [])
            self.assertFalse((state / "matches" / "fyxer-call-1.json").exists())

    def test_no_viable_surfer_gaps_are_persisted_without_drafting(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = create_surfer_state(root, viable=False)
            report = json.loads((state / "keyword_gaps.json").read_text())
            self.assertEqual(report["viable"], [])
            self.assertEqual(len(report["rejected"]), 2)


if __name__ == "__main__":
    unittest.main()
