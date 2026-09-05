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


class PipelineTests(unittest.TestCase):
    def test_rejects_quote_that_is_not_in_transcript(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            transcript = root / "call.txt"
            transcript.write_text("The actual customer statement.", encoding="utf-8")
            candidates = write_json(
                root / "insights-candidate.json",
                [{
                    "id": "candidate",
                    "type": "pain",
                    "statement": "A made-up pain.",
                    "topic": "Testing",
                    "evidence": [{"source_id": "call-1", "quote": "This was never said."}],
                    "occurrence_count": 1,
                }],
            )
            result = run_script(
                "extract_insights.py",
                "--candidates", str(candidates),
                "--transcript", f"call-1={transcript}",
                "--state-dir", str(root / ".infotocontent"),
                expected=2,
            )
            self.assertIn("quote not found", result.stderr)
            self.assertFalse((root / ".infotocontent" / "insights.json").exists())

    def test_complete_pipeline_persists_valid_references(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = root / ".infotocontent"
            transcript = root / "call.txt"
            transcript.write_text(
                "Customer: We cannot tell why retrieval got worse.\n"
                "Customer: How do we test retrieval before a release?\n",
                encoding="utf-8",
            )
            insights_candidate = write_json(
                root / "insights.json",
                [
                    {
                        "id": "one",
                        "type": "pain",
                        "statement": "Teams lack visibility into retrieval regressions.",
                        "topic": "RAG evaluation",
                        "evidence": [{
                            "source_id": "call-1",
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
                            "source_id": "call-1",
                            "quote": "How do we test retrieval before a release?",
                            "speaker": "Customer",
                        }],
                        "occurrence_count": 1,
                    },
                ],
            )
            run_script(
                "extract_insights.py",
                "--candidates", str(insights_candidate),
                "--transcript", f"call-1={transcript}",
                "--state-dir", str(state),
            )
            insights = json.loads((state / "insights.json").read_text())
            insight_ids = [item["id"] for item in insights]
            self.assertTrue(all(identifier.startswith("ins_") for identifier in insight_ids))

            # Replaying the same transcript is idempotent and must not inflate evidence.
            run_script(
                "extract_insights.py",
                "--candidates", str(insights_candidate),
                "--transcript", f"call-1={transcript}",
                "--state-dir", str(state),
            )
            replayed = json.loads((state / "insights.json").read_text())
            self.assertEqual([item["occurrence_count"] for item in replayed], [1, 1])

            dna_candidate = write_json(
                root / "dna.json",
                {
                    "company_description": "Acme helps teams evaluate RAG systems.",
                    "target_audience": "ML engineers",
                    "products": ["RAG evaluation"],
                    "tone": ["Technical", "technical", "direct"],
                    "existing_topics": ["RAG basics"],
                },
            )
            run_script(
                "build_website_dna.py",
                "--candidate", str(dna_candidate),
                "--state-dir", str(state),
            )

            opportunities_candidate = write_json(
                root / "opportunities-candidate.json",
                [
                    {
                        "id": f"candidate-{index}",
                        "title": title,
                        "angle": angle,
                        "target_audience": "ML engineers",
                        "insight_ids": insight_ids,
                        "evidence_strength": 0,
                        "why_now": "Customer evidence shows an immediate operational gap.",
                    }
                    for index, (title, angle) in enumerate([
                        ("Debug RAG Regressions", "A diagnostic workflow."),
                        ("Test Retrieval Before Release", "A pre-release checklist."),
                        ("Make RAG Quality Visible", "An observability framework."),
                    ], start=1)
                ],
            )
            run_script(
                "discover_opportunities.py",
                "--candidates", str(opportunities_candidate),
                "--state-dir", str(state),
            )
            opportunity = json.loads((state / "opportunities.json").read_text())[0]
            self.assertEqual(opportunity["evidence_strength"], 0.2)

            surfer_candidate = write_json(
                root / "surfer.json",
                {
                    "available": True,
                    "target_keyword": "rag testing",
                    "recommended_terms": ["retrieval quality", "RAG testing"],
                    "target_word_count": 1500,
                    "content_score": None,
                    "unavailable_reason": None,
                },
            )
            brief_candidate = write_json(
                root / "brief.json",
                {
                    "title": "will be replaced",
                    "audience": "will be replaced",
                    "angle": "will be replaced",
                    "supporting_insight_ids": insight_ids,
                    "key_customer_pains_questions": [
                        "Teams lack visibility into retrieval regressions."
                    ],
                    "required_points": ["Explain detection", "Explain diagnosis"],
                    "seo_terms": [],
                    "target_word_count": None,
                    "surfer_available": False,
                },
            )
            run_script(
                "build_brief.py",
                "--opportunity-id", opportunity["id"],
                "--candidate", str(brief_candidate),
                "--surfer-context", str(surfer_candidate),
                "--state-dir", str(state),
            )
            brief = json.loads((state / "briefs" / f"{opportunity['id']}.json").read_text())
            self.assertEqual(brief["title"], opportunity["title"])
            self.assertEqual(brief["target_word_count"], 1500)
            self.assertTrue(brief["surfer_available"])

            draft = root / "draft.md"
            draft.write_text("# Draft\n\nGrounded article.", encoding="utf-8")
            run_script(
                "save_draft.py",
                "--opportunity-id", opportunity["id"],
                "--draft", str(draft),
                "--state-dir", str(state),
            )
            result = run_script("validate.py", "--state-dir", str(state))
            self.assertIn("briefs=1", result.stdout)
            self.assertIn("drafts=1", result.stdout)


if __name__ == "__main__":
    unittest.main()
