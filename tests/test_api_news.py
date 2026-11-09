import unittest
from datetime import datetime, timezone

from api.news import categorize, date_value, rank, clean


class FeedParsingTests(unittest.TestCase):
    def test_rfc822_date_is_normalized_to_utc(self):
        parsed = date_value("Mon, 09 Nov 2026 10:30:00 +0530")
        self.assertEqual(parsed.tzinfo, timezone.utc)
        self.assertEqual(parsed.hour, 5)
        self.assertEqual(parsed.minute, 0)

    def test_iso_date_is_supported(self):
        parsed = date_value("2026-11-09T10:30:00Z")
        self.assertEqual(parsed, datetime(2026, 11, 9, 10, 30, tzinfo=timezone.utc))

    def test_invalid_date_returns_none(self):
        self.assertIsNone(date_value("not a date"))

    def test_html_is_removed_from_feed_snippets(self):
        self.assertEqual(clean("<p>New <b>model</b> update</p>"), "New model update")

    def test_categories_are_deterministic(self):
        self.assertEqual(categorize("A new reasoning model release"), "Models")
        self.assertEqual(categorize("New benchmark research paper"), "Research")
        self.assertEqual(categorize("GPU inference infrastructure update"), "Infrastructure")

    def test_rank_adds_explainable_fields(self):
        item = {
            "title": "Open source model release with reasoning benchmark",
            "summary": "Research results and model evaluation",
            "source_type": "Primary",
            "date": datetime.now(timezone.utc).isoformat(),
        }
        result = rank(item)
        self.assertIn(result["priority"], {"High", "Medium", "Emerging"})
        self.assertGreaterEqual(result["priority_score"], 0)
        self.assertLessEqual(result["priority_score"], 100)
        self.assertIn("Research", result["topics"])
        self.assertIn("Models", result["topics"])


if __name__ == "__main__":
    unittest.main()
