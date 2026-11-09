import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from intelligence_graph import build_ecosystem_signals, event_key, topic_tags

class IntelligenceGraphTests(unittest.TestCase):
    def test_topic_tags_are_deterministic(self):
        self.assertEqual(topic_tags("Open-weight reasoning model"), ["open_models", "reasoning"])

    def test_event_key_is_stable(self):
        item = {"company": "OpenAI", "title": "New reasoning model!"}
        self.assertEqual(event_key(item), event_key(dict(item)))

    def test_convergence_requires_multiple_companies(self):
        items = [
            {"company": "OpenAI", "title": "Reasoning model launch", "url": "https://openai.com/a"},
            {"company": "Anthropic", "title": "Reasoning system update", "url": "https://anthropic.com/b"},
            {"company": "NVIDIA", "title": "New GPU architecture", "url": "https://nvidia.com/c"},
        ]
        result = build_ecosystem_signals(items)
        reasoning = next(x for x in result["topic_company_convergence"] if x["topic"] == "reasoning")
        self.assertEqual(reasoning["company_count"], 2)
        self.assertEqual(len(result["event_nodes"]), 3)

    def test_publisher_aliases_do_not_fake_cross_company_convergence(self):
        items = [
            {"publisher": "Google AI", "title": "Reasoning model update", "url": "https://blog.google/a"},
            {"publisher": "Google DeepMind", "title": "Reasoning research update", "url": "https://deepmind.google/b"},
        ]
        result = build_ecosystem_signals(items)
        self.assertEqual(result["topic_company_convergence"], [])

    def test_empty_input_is_valid(self):
        self.assertEqual(build_ecosystem_signals([])["items_analyzed"], 0)

if __name__ == "__main__":
    unittest.main()
