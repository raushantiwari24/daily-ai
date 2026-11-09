import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from source_registry import enrich_and_rank


class EvidenceScoringTests(unittest.TestCase):
    def test_first_party_item_gets_primary_evidence_label(self):
        item = {
            "company": "OpenAI",
            "title": "OpenAI announces a new reasoning model release",
            "date": "2026-11-09",
            "description": "New model and API release",
            "url": "https://openai.com/news/example",
            "source_type": "primary",
            "publisher": "OpenAI",
        }
        result = enrich_and_rank([item])[0]
        self.assertEqual(result["evidence_level"], "first-party")
        self.assertGreaterEqual(result["importance_score"], 35)
        self.assertLessEqual(result["importance_score"], 100)

    def test_research_item_is_not_mislabeled_as_first_party(self):
        item = {
            "company": "arXiv cs.AI",
            "title": "A new research benchmark for reasoning systems",
            "date": "2026-11-09",
            "description": "Research paper",
            "url": "https://arxiv.org/abs/2611.00001",
            "source_type": "research",
            "publisher": "arXiv cs.AI",
        }
        result = enrich_and_rank([item])[0]
        self.assertEqual(result["evidence_level"], "research-source")

    def test_score_is_bounded(self):
        item = {
            "company": "OpenAI",
            "title": "AI model launch benchmark research API safety security reasoning",
            "date": "2026-11-09",
            "description": "Open source model release",
            "url": "https://openai.com/news/example",
            "source_type": "primary",
            "publisher": "OpenAI",
        }
        result = enrich_and_rank([item])[0]
        self.assertGreaterEqual(result["importance_score"], 0)
        self.assertLessEqual(result["importance_score"], 100)


if __name__ == "__main__":
    unittest.main()
