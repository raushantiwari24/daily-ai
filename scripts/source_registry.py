"""Curated first-party AI publisher feeds and deterministic evidence scoring."""
from __future__ import annotations
import re, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from weekly_ai_digest import request, clean_text, parse_date, WINDOW_DAYS

SOURCES = [
    ("OpenAI", "https://openai.com/news/rss.xml", "primary"),
    ("Google AI", "https://blog.google/technology/ai/rss/", "primary"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml", "primary"),
    ("Google Research", "https://research.google/blog/rss/", "primary"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml", "primary"),
    ("NVIDIA", "https://blogs.nvidia.com/feed/", "primary"),
    ("AWS Machine Learning", "https://aws.amazon.com/blogs/machine-learning/feed/", "primary"),
    ("Microsoft Research", "https://www.microsoft.com/en-us/research/feed/", "primary"),
    ("arXiv cs.AI", "https://rss.arxiv.org/rss/cs.AI", "research"),
    ("arXiv cs.LG", "https://rss.arxiv.org/rss/cs.LG", "research"),
]
IMPORTANT_TERMS = {"release": 3, "launch": 3, "announces": 2, "model": 2, "benchmark": 3, "research": 2, "open-source": 3, "open source": 3, "safety": 2, "security": 2, "api": 2, "reasoning": 2, "agent": 2, "chip": 2, "funding": 1, "partnership": 1}

def _tag_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return found.text.strip()
    return ""

def fetch_official_sources() -> list[dict[str, str]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    records: list[dict[str, str]] = []
    for publisher, feed_url, tier in SOURCES:
        try:
            root = ET.fromstring(request(feed_url, timeout=25))
            nodes = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for node in nodes:
                title = clean_text(_tag_text(node, ("title", "{http://www.w3.org/2005/Atom}title")))
                link = _tag_text(node, ("link",))
                if not link:
                    atom_link = node.find("{http://www.w3.org/2005/Atom}link")
                    if atom_link is not None: link = atom_link.attrib.get("href", "")
                date_raw = _tag_text(node, ("pubDate", "published", "updated", "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated"))
                try: published = parsedate_to_datetime(date_raw) if date_raw else None
                except Exception: published = None
                if published is None:
                    published = parse_date(date_raw)
                if published is None: continue
                if published.tzinfo is None: published = published.replace(tzinfo=timezone.utc)
                published = published.astimezone(timezone.utc)
                if not title or not link or published < cutoff: continue
                description = clean_text(_tag_text(node, ("description", "summary", "{http://www.w3.org/2005/Atom}summary")))
                records.append({"company": publisher, "title": title, "date": published.strftime("%Y-%m-%d"), "description": description[:900], "url": link, "source_type": tier, "publisher": publisher})
            print(f"[SOURCE] {publisher}: {len(nodes)} feed entries scanned.")
        except Exception as exc:
            print(f"[WARN] Official feed unavailable for {publisher}: {exc}")
    return records

def enrich_and_rank(items: list[dict[str, str]]) -> list[dict[str, Any]]:
    # Cluster near-identical headlines; corroboration counts distinct publisher domains.
    def tokens(text: str) -> set[str]:
        return {w for w in re.findall(r"[a-z0-9]{3,}", text.lower()) if w not in {"the", "and", "for", "with", "from", "that", "this", "into", "after"}}
    token_sets = [tokens(x["title"]) for x in items]
    enriched = []
    for i, item in enumerate(items):
        peers = []
        for j, other in enumerate(items):
            if i == j: continue
            union = token_sets[i] | token_sets[j]
            similarity = len(token_sets[i] & token_sets[j]) / max(1, len(union))
            if similarity >= 0.55: peers.append(other)
        domains = {urllib.parse.urlsplit(x["url"]).netloc.lower().removeprefix("www.") for x in [item, *peers]}
        primary = item.get("source_type") == "primary"
        corroboration = len(domains)
        age = max(0, (datetime.now(timezone.utc).date() - datetime.strptime(item["date"], "%Y-%m-%d").date()).days)
        text = (item["title"] + " " + item.get("description", "")).lower()
        topic_score = sum(weight for term, weight in IMPORTANT_TERMS.items() if term in text)
        score = min(100, (35 if primary else 15 if item.get("source_type") == "research" else 5) + min(25, topic_score * 2) + min(20, (corroboration - 1) * 10) + max(0, 20 - age * 3))
        item.update({"source_host": urllib.parse.urlsplit(item["url"]).netloc, "evidence_level": "first-party" if primary else "research-source" if item.get("source_type") == "research" else "secondary", "corroboration_count": corroboration, "importance_score": score, "importance_band": "high" if score >= 65 else "medium" if score >= 40 else "emerging"})
        enriched.append(item)
    return sorted(enriched, key=lambda x: (x["importance_score"], x["date"]), reverse=True)

def collect_intelligence() -> list[dict[str, Any]]:
    items = fetch_official_sources()
    ranked = enrich_and_rank(items)
    # The existing Google News collector remains a discovery fallback, not primary evidence.
    try:
        from weekly_ai_digest import collect_updates
        secondary = collect_updates()
        known = {x["url"] for x in ranked}
        for item in secondary:
            if item["url"] not in known:
                item.update({"source_type": "secondary", "publisher": item.get("company", "News publisher")})
                ranked.append(item)
        ranked = enrich_and_rank(ranked)
    except Exception as exc:
        print(f"[WARN] Secondary discovery unavailable: {exc}")
    return ranked[:70]
