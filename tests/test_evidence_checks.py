import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evidence_checks import assess_summary_support

class SummaryEvidenceTests(unittest.TestCase):
    def test_high_overlap_is_not_verification(self):
        result = assess_summary_support("OpenAI releases a new reasoning model with coding performance", "OpenAI releases a new reasoning model", "The reasoning model is designed for coding tasks.")
        self.assertEqual(result["status"], "strong_snippet_overlap")
        self.assertNotEqual(result["status"], "verified")
    def test_unrelated_summary_is_weak(self):
        result = assess_summary_support("NVIDIA announces a GPU architecture", "Anthropic updates Claude", "A new assistant feature is available.")
        self.assertEqual(result["status"], "weak_snippet_overlap")
    def test_empty_source_is_insufficient(self):
        result = assess_summary_support("A model launches", "", "")
        self.assertEqual(result["status"], "insufficient_source_text")

if __name__ == "__main__":
    unittest.main()
