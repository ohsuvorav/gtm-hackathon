from __future__ import annotations

import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import run as runner
from pipeline import stage4_dna, stage6_compose, stage8_surfer
from pipeline.stage2_gaps import from_recommendations, icp_terms_from_dna


BRAND = {
    "id": 14148,
    "url": "https://example.com",
    "gathering_data_status": "completed",
    "knowledge": """**Business Type**

Professional services

**Industry**

B2B SaaS

**Products/Services description**

Growth product management

**Problem solved**

Slow activation

**Customer profile**

Post-PMF startup hiring managers

**Competitors**

Growth consultants

**Topics to cover**

Product management and activation
""",
}


class FakeSurfer:
    def __init__(self) -> None:
        self.calls = []

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        responses = {
            "content_editor__create": {"id": 77, "state": "scheduled"},
            "content_editor__get": {"id": 77, "state": "completed"},
            "content__update": {},
            "content_score__get": {
                "seo": {"score": 81, "status": "ready"},
                "ai_search": {"score": 72, "status": "ready"},
                "total": {"score": 78, "status": "ready"},
            },
        }
        return responses[name]


class LivePipelineTests(unittest.TestCase):
    def test_live_input_fetch_writes_all_three_surfer_sources(self):
        class InputSurfer:
            def call_tool(self, name, arguments):
                return {
                    "brand__get": BRAND,
                    "custom_voice__list": {
                        "data": [{"id": 12, "name": "Voice", "default": True}]
                    },
                    "custom_voice__get": {"id": 12, "reference_text": "Direct voice."},
                    "recommendation__list": {
                        "data": [{
                            "id": 10,
                            "title": "Product Manager Recruitment",
                            "main_keyword": "product manager headhunters",
                            "topic_title": "Hiring",
                            "location": "United States",
                            "search_volume": 2720,
                            "avg_difficulty": 216,
                            "score": 7.44,
                        }]
                    },
                }[name]

        args = Namespace(workspace_id=1385655, voice_id=None, recommendation_limit=100)
        old_dna = runner.DNA
        with tempfile.TemporaryDirectory() as tmp:
            runner.DNA = Path(tmp)
            try:
                dna, gaps, voice_path = runner.fetch_live_inputs(args, InputSurfer())
            finally:
                runner.DNA = old_dna
            self.assertEqual(voice_path.read_text(), "Direct voice.")
            self.assertTrue((Path(tmp) / "site_dna.md").exists())
            self.assertTrue((Path(tmp) / "site_dna.json").exists())
            self.assertTrue((Path(tmp) / "keyword_recommendations.json").exists())
            self.assertEqual(dna["industry"], "B2B SaaS")
            self.assertEqual(len(gaps["viable"]), 1)

    def test_brand_markdown_is_normalized(self):
        dna = stage4_dna.from_mcp_response(BRAND, workspace_id=1385655)
        self.assertEqual(dna["products_services"], "Growth product management")
        self.assertEqual(dna["problem_solved"], "Slow activation")
        self.assertEqual(dna["_meta"]["brand_id"], 14148)

    def test_recommendations_replace_the_legacy_csv_contract(self):
        dna = stage4_dna.from_mcp_response(BRAND)
        payload = {
            "data": [
                {
                    "id": 10,
                    "title": "Product Manager Recruitment",
                    "main_keyword": "product manager headhunters",
                    "topic_title": "Hiring",
                    "location": "United States",
                    "search_volume": 2720,
                    "avg_difficulty": 216,
                    "score": 7.44,
                    "reasons": ["gap", "low_difficulty"],
                    "content_editor_id": None,
                }
            ]
        }
        gaps = from_recommendations(payload, icp_terms_from_dna(dna))
        self.assertEqual(len(gaps["viable"]), 1)
        self.assertEqual(gaps["viable"][0]["avg_difficulty"], 2.16)
        self.assertEqual(gaps["viable"][0]["keywords"][0]["keyword"], "product manager headhunters")

    def test_custom_voice_is_injected_into_the_system_prompt(self):
        dna = stage4_dna.from_mcp_response(BRAND)
        gaps = {
            "viable": [{
                "cluster": "Product Manager Recruitment",
                "volume": 2720,
                "avg_difficulty": 2.16,
                "capture_rate": 0,
                "keywords": [{
                    "keyword": "product manager headhunters",
                    "volume": 2720,
                    "difficulty": 2.16,
                }],
            }]
        }
        signal = {
            "core": {
                "topic": "Hiring",
                "objection": "The role is unclear",
                "buyer_language": ["we do not know what this person owns"],
                "competitor": None,
            },
            "match": {
                "cluster": "Product Manager Recruitment",
                "keyword": "product manager headhunters",
                "confidence": 0.9,
                "evidence": "we do not know what this person owns",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            voice = Path(tmp) / "voice.md"
            voice.write_text("Never use a rhetorical question.")
            prompt = stage6_compose.compose(
                dna, gaps, signal, Path(tmp) / "posts.jsonl", voice_path=voice
            )
        self.assertIn("Never use a rhetorical question.", prompt)
        self.assertIn("custom voice reference text from Surfer", prompt)

    def test_surfer_push_creates_updates_and_scores(self):
        old_source = os.environ.get("STAGE8_SOURCE")
        os.environ["STAGE8_SOURCE"] = "live"
        try:
            client = FakeSurfer()
            score = stage8_surfer.run(
                "# Draft",
                "product manager headhunters",
                client=client,
                workspace_id=1385655,
                location="United States",
            )
        finally:
            if old_source is None:
                os.environ.pop("STAGE8_SOURCE", None)
            else:
                os.environ["STAGE8_SOURCE"] = old_source

        self.assertEqual(score["content_editor_id"], 77)
        self.assertEqual(score["total"]["score"], 78)
        self.assertEqual(
            [name for name, _ in client.calls],
            [
                "content_editor__create",
                "content_editor__get",
                "content__update",
                "content_score__get",
            ],
        )


if __name__ == "__main__":
    unittest.main()
