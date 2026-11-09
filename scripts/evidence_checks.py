"""Conservative lexical checks between generated summaries and collected feed snippets.

This is a triage signal only. Token overlap cannot establish factual entailment or truth.
"""
from __future__ import annotations
import re

STOPWORDS = {"the", "and", "for", "with", "from", "that", "this", "into", "after", "have", "has", "had", "was", "were", "are", "is", "its", "their", "they", "them", "will", "would", "could", "should", "about", "over", "under", "than", "then", "also", "new", "more", "most", "some"}

def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{3,}", (text or "").lower()) if t not in STOPWORDS}

def assess_summary_support(summary: str, source_title: str, source_description: str) -> dict[str, int | str]:
    """Return overlap score and cautious triage label, never 'verified'."""
    summary_tokens = _tokens(summary)
    source_tokens = _tokens(f"{source_title} {source_description}")
    if not summary_tokens or not source_tokens:
        return {"score": 0, "status": "insufficient_source_text"}
    score = round(100 * len(summary_tokens & source_tokens) / len(summary_tokens))
    status = "strong_snippet_overlap" if score >= 45 else "partial_snippet_overlap" if score >= 20 else "weak_snippet_overlap"
    return {"score": score, "status": status}
