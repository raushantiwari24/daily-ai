"""Explainable AI ecosystem signal engine.

Builds a lightweight event graph from publisher feed records. It identifies
cross-company topic convergence and week-over-week capability emphasis.
Signals are descriptive discovery aids, not causal claims or predictions.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlsplit

TOPIC_RULES = {
    "reasoning": {"reasoning", "deliberation", "solver", "thinking"},
    "agents": {"agent", "agents", "tool-use", "tool use", "workflow"},
    "multimodal": {"multimodal", "image", "video", "audio", "speech"},
    "coding": {"coding", "code", "developer", "software", "programming"},
    "open_models": {"open-weight", "open weights", "open-source", "open source", "weights"},
    "infrastructure": {"gpu", "chip", "inference", "compute", "datacenter", "data center"},
    "safety": {"safety", "alignment", "security", "red-team", "red team"},
    "research": {"research", "paper", "arxiv", "benchmark", "evaluation"},
    "enterprise": {"enterprise", "business", "workspace", "deployment"},
    "robotics": {"robot", "robotics", "embodied", "physical ai"},
}

COMPANY_ALIASES = {
    "openai": "OpenAI", "anthropic": "Anthropic", "google": "Google",
    "deepmind": "Google", "hugging face": "Hugging Face", "nvidia": "NVIDIA",
    "microsoft": "Microsoft", "aws": "AWS", "arxiv": "Research community",
    "meta": "Meta", "xai": "xAI", "deepseek": "DeepSeek", "mistral": "Mistral",
}

def topic_tags(text: str) -> list[str]:
    normalized = (text or "").lower()
    return sorted(topic for topic, terms in TOPIC_RULES.items()
                  if any(term in normalized for term in terms))

def event_key(item: dict) -> str:
    title = re.sub(r"[^a-z0-9]+", " ", str(item.get("title", "")).lower()).strip()
    company = str(item.get("company") or item.get("publisher") or "unknown").lower()
    digest = hashlib.sha256(f"{company}|{title}".encode("utf-8")).hexdigest()[:20]
    return f"evt_{digest}"

def build_ecosystem_signals(items: list[dict]) -> dict:
    """Summarize current feed activity without implying causation."""
    company_topics = defaultdict(Counter)
    topic_companies = defaultdict(set)
    event_nodes = []
    for item in items:
        text = f"{item.get('title', '')} {item.get('description', '')}"
        tags = topic_tags(text)
        company = str(item.get("publisher") or item.get("company") or "Unknown")
        for tag in tags:
            company_topics[company][tag] += 1
            topic_companies[tag].add(company)
        host = urlsplit(str(item.get("url", ""))).netloc.lower()
        event_nodes.append({
            "event_key": event_key(item),
            "company": company,
            "title": str(item.get("title", ""))[:180],
            "date": str(item.get("date", "")),
            "topics": tags,
            "source_host": host,
        })

    convergence = [
        {"topic": topic, "company_count": len(companies),
         "companies": sorted(companies)}
        for topic, companies in topic_companies.items() if len(companies) >= 2
    ]
    convergence.sort(key=lambda x: (-x["company_count"], x["topic"]))

    shifts = []
    for company, counts in sorted(company_topics.items()):
        ranked = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
        if ranked:
            shifts.append({"company": company, "leading_topics": [
                {"topic": topic, "items": count} for topic, count in ranked[:3]
            ]})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items_analyzed": len(items),
        "topic_company_convergence": convergence[:8],
        "company_topic_profiles": shifts[:15],
        "event_nodes": event_nodes,
        "interpretation": (
            "Convergence means multiple monitored publishers had feed items tagged "
            "with the same topic in this collection window. It does not establish "
            "coordination, causation, market leadership, or future direction."
        ),
    }
