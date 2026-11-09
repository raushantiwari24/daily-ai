#!/usr/bin/env python3
"""Collect recent AI-company updates, summarize them with Gemini, and publish to Notion."""

from __future__ import annotations

import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from source_registry import collect_intelligence
from evidence_checks import assess_summary_support
from intelligence_graph import build_ecosystem_signals, event_key, canonical_company
from datetime import datetime, timedelta, timezone
from html import unescape
from typing import Any

NOTION_PARENT_PAGE_ID = "41362a3c60c981bfa39ae0849bd70975"
NOTION_VERSION = "2022-06-28"
NOTION_DATA_SOURCE_ID = "a82ad32c-1789-4260-874a-872cca0909be"
GEMINI_MODEL = "gemini-3.5-flash-lite"
WINDOW_DAYS = 7
MAX_PER_COMPANY = 6

COMPANIES = [
    ("OpenAI", "openai.com"),
    ("Anthropic", "anthropic.com"),
    ("Google / Gemini", "blog.google"),
    ("Google DeepMind", "deepmind.google"),
    ("xAI / Grok", "x.ai"),
    ("Meta / Llama", "ai.meta.com"),
    ("DeepSeek", "deepseek.com"),
    ("Mistral AI", "mistral.ai"),
    ("Microsoft", "blogs.microsoft.com"),
    ("NVIDIA", "blogs.nvidia.com"),
    ("Hugging Face", "huggingface.co"),
]

def request(url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None,
            method: str = "GET", timeout: int = 30) -> bytes:
    """HTTP helper with bounded retries and actionable API error messages."""
    retryable = {429, 500, 502, 503, 504}
    max_attempts = 5
    for attempt in range(max_attempts):
        req = urllib.request.Request(
            url, data=data, headers=headers or {"User-Agent": "WeeklyAIIntelligenceBot/3.0"},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1200]
            if exc.code in retryable and attempt < max_attempts - 1:
                retry_after = exc.headers.get("Retry-After")
                try:
                    delay = min(float(retry_after), 90) if retry_after else min(8 * (2 ** attempt), 60)
                except (TypeError, ValueError):
                    delay = min(8 * (2 ** attempt), 60)
                delay += random.uniform(0, min(3, delay * 0.15))
                print(f"[RETRY] HTTP {exc.code} from {urllib.parse.urlsplit(url).netloc}; "
                      f"attempt {attempt + 1}/{max_attempts}, waiting {delay:.1f}s.")
                time.sleep(delay)
                continue
            raise RuntimeError(
                f"HTTP {exc.code} from {urllib.parse.urlsplit(url).netloc}: {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == max_attempts - 1:
                raise RuntimeError(f"Network request failed for {urllib.parse.urlsplit(url).netloc}: {exc}") from exc
            delay = min(5 * (2 ** attempt), 45) + random.uniform(0, 2)
            print(f"[RETRY] Network issue for {urllib.parse.urlsplit(url).netloc}; "
                  f"attempt {attempt + 1}/{max_attempts}, waiting {delay:.1f}s.")
            time.sleep(delay)
    raise RuntimeError("HTTP request exhausted retries.")

def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", unescape(value or ""))
    return re.sub(r"\s+", " ", value).strip()

def fetch_company_feed(company: str, domain: str, cutoff: datetime) -> list[dict[str, str]]:
    query = f"site:{domain} (AI OR model OR research OR API OR product) when:{WINDOW_DAYS}d"
    params = urllib.parse.urlencode({"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
    url = "https://news.google.com/rss/search?" + params
    try:
        xml_data = request(url, headers={"User-Agent": "WeeklyAIIntelligenceBot/1.0"})
        root = ET.fromstring(xml_data)
    except Exception as exc:
        print(f"[WARN] Could not fetch {company} feed: {exc}", file=sys.stderr)
        return []

    items: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title", ""))
        link = (item.findtext("link", "") or "").strip()
        description = clean_text(item.findtext("description", ""))
        pub_date = parse_date(item.findtext("pubDate", ""))
        if not title or not link or not pub_date or pub_date < cutoff:
            continue
        items.append({
            "company": company,
            "title": title,
            "date": pub_date.strftime("%Y-%m-%d"),
            "description": description[:700],
            "url": link,
        })
    return items[:MAX_PER_COMPANY]

def collect_updates() -> list[dict[str, str]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    collected: list[dict[str, str]] = []
    for company, domain in COMPANIES:
        collected.extend(fetch_company_feed(company, domain, cutoff))
        time.sleep(0.15)

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in sorted(collected, key=lambda x: x["date"], reverse=True):
        key = re.sub(r"[^a-z0-9]", "", item["title"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique[:55]

def call_gemini(updates: list[dict[str, str]]) -> dict[str, Any]:
    api_key = os.environ["GEMINI_API_KEY"]
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={urllib.parse.quote(api_key)}"
    )
    prompt = """You are an exacting AI-industry news editor. Create a weekly digest using ONLY the supplied feed items.
Do not invent announcements, dates, quotes, links, metrics, or claims. Treat feed descriptions as snippets, not proof.
Prefer substantive model releases, product/API changes, research, benchmarks, safety/policy and business developments.
Merge duplicate coverage of the same announcement. Exclude weak, irrelevant, speculative, or promotional noise.
If there are few meaningful updates, say so rather than padding the report.
Return ONLY valid JSON with this schema:
{
 "headline": "short issue headline",
 "executive_summary": "2-4 factual sentences",
 "top_developments": [
   {"title":"...", "company":"exact supplied company label", "date":"YYYY-MM-DD",
    "summary":"2-3 clear sentences based only on supplied data",
    "why_it_matters":"one concrete implication, or state that implications are uncertain",
    "url":"EXACT URL from one supplied item", "evidence_level":"exact input value", "corroboration_count":0, "importance_score":0, "importance_band":"exact input value"}
 ],
 "company_notes": ["short concise notes for companies with relevant updates"],
 "watch_next_week": ["clearly labelled watch items; do not imply confirmed events"],
 "bottom_line":"one concise takeaway"
}
Use no more than 12 top developments. Each url MUST be copied exactly from a supplied item. Preserve each selected item's evidence_level, corroboration_count, importance_score, and importance_band exactly. Do not describe corroboration as proof or first-party provenance as independent fact-checking.
Feed items:
""" + json.dumps(updates, ensure_ascii=False)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    body = json.dumps(payload).encode("utf-8")
    raw = request(endpoint, data=body, method="POST",
                  headers={"Content-Type": "application/json"}, timeout=90)
    response = json.loads(raw)
    try:
        candidate_text = response["candidates"][0]["content"]["parts"][0]["text"]
        digest = json.loads(candidate_text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "Gemini returned an unexpected or invalid JSON response. "
            "Check model/API access and the response in the Actions log."
        ) from exc
    return validate_digest(digest, updates)


def validate_digest(digest: Any, updates: list[dict[str, str]]) -> dict[str, Any]:
    """Reject malformed model output and any citation URL not present in collected feeds."""
    if not isinstance(digest, dict):
        raise RuntimeError("Gemini output must be a JSON object.")
    required_text = ("headline", "executive_summary", "bottom_line")
    for field in required_text:
        if not isinstance(digest.get(field), str) or not digest[field].strip():
            raise RuntimeError(f"Gemini output is missing required text field: {field}")

    allowed_items = {item["url"]: item for item in updates}
    allowed_urls = set(allowed_items)
    entries = digest.get("top_developments", [])
    if not isinstance(entries, list):
        raise RuntimeError("Gemini top_developments must be a list.")
    if len(entries) > 12:
        entries = entries[:12]

    clean_entries = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue
        url = str(entry.get("url", "")).strip()
        if url not in allowed_urls:
            print(f"[WARN] Dropping development {index}: URL was not in the collected feed.", file=sys.stderr)
            continue
        date = str(entry.get("date", "")).strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            print(f"[WARN] Dropping development {index}: invalid date.", file=sys.stderr)
            continue
        if date != allowed_items[url]["date"]:
            print(f"[WARN] Dropping development {index}: date does not match its source item.", file=sys.stderr)
            continue
        title = str(entry.get("title", "")).strip()
        summary = str(entry.get("summary", "")).strip()
        if not title or not summary:
            continue
        clean_entries.append({
            "title": title[:240],
            "company": str(entry.get("company", "Unknown"))[:100],
            "date": date,
            "summary": summary[:900],
            "why_it_matters": str(entry.get("why_it_matters", "Implications are uncertain."))[:500],
            "url": url,
            "evidence_level": str(allowed_items[url].get("evidence_level", "unknown")),
            "corroboration_count": int(allowed_items[url].get("corroboration_count", 1)),
            "importance_score": int(allowed_items[url].get("importance_score", 0)),
            "importance_band": str(allowed_items[url].get("importance_band", "emerging")),
            **assess_summary_support(summary, allowed_items[url].get("title", ""), allowed_items[url].get("description", "")),
        })
    digest["top_developments"] = clean_entries
    for field in ("company_notes", "watch_next_week"):
        value = digest.get(field, [])
        digest[field] = [str(item)[:500] for item in value[:15]] if isinstance(value, list) else []
    print(f"Validated {len(clean_entries)} developments against {len(allowed_urls)} collected source URLs.")
    return digest

def notion_rich_text(text: str, url: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"type": "text", "text": {"content": str(text)[:1900]}}
    if url and url.startswith("https://"):
        item["text"]["link"] = {"url": url}
    return item

def paragraph(text: str, url: str | None = None) -> dict[str, Any]:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [notion_rich_text(text, url)]}}

def heading(text: str, level: int = 2) -> dict[str, Any]:
    kind = f"heading_{level}"
    return {"object": "block", "type": kind, kind: {"rich_text": [notion_rich_text(text)]}}

def bullet(text: str, url: str | None = None) -> dict[str, Any]:
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [notion_rich_text(text, url)]}}


def sync_tracker(entries: list[dict[str, Any]]) -> tuple[int, int]:
    """Upsert selected developments into the Notion event ledger by stable event key."""
    token = os.environ["NOTION_TOKEN"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2025-09-03",
        "Content-Type": "application/json",
    }
    created = updated = 0
    company_options = {
        "openai": "OpenAI", "anthropic": "Anthropic", "google": "Google",
        "google / gemini": "Google", "google deepmind": "Google", "google ai": "Google", "google research": "Google",
        "xai / grok": "xAI", "xai": "xAI", "meta / llama": "Meta",
        "meta": "Meta", "deepseek": "DeepSeek", "mistral ai": "Mistral",
        "mistral": "Mistral", "microsoft": "Microsoft", "hugging face": "Hugging Face", "nvidia": "NVIDIA", "aws machine learning": "AWS", "aws": "AWS", "research community": "Research community",
    }
    for entry in entries:
        source_item = next((item for item in CURRENT_UPDATES if item.get("url") == entry.get("url")), entry)
        key = event_key(source_item)
        company_raw = canonical_company(str(source_item.get("publisher") or source_item.get("company") or entry.get("company", "Other")))
        company = company_options.get(company_raw.lower(), "Other")
        text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
        if any(term in text for term in ("benchmark", "evaluation", "leaderboard")):
            category = "Benchmark"
        elif any(term in text for term in ("safety", "alignment", "security")):
            category = "Safety"
        elif any(term in text for term in ("pricing", "price", "cost")):
            category = "Pricing"
        elif "api" in text:
            category = "API change"
        elif any(term in text for term in ("model", "llm", "weights")):
            category = "Model release"
        elif "research" in text or entry.get("evidence_level") == "research-source":
            category = "Research"
        elif any(term in text for term in ("feature", "app", "product")):
            category = "Product feature"
        else:
            category = "Other"
        evidence = str(entry.get("evidence_level", "secondary"))
        evidence_status = "Primary source" if evidence == "first-party" else "Research source" if evidence == "research-source" else "Secondary only"
        today = datetime.now(timezone.utc).date().isoformat()
        properties = {
            "Update": {"title": [{"text": {"content": str(entry.get("title", "Untitled"))[:180]}}]},
            "Company": {"select": {"name": company}},
            "Category": {"select": {"name": category}},
            "Announcement date": {"date": {"start": str(entry.get("date", today))}},
            "Last observed": {"date": {"start": today}},
            "Evidence status": {"select": {"name": evidence_status}},
            "Verified": {"checkbox": False},
            "Event key": {"rich_text": [{"text": {"content": key}}]},
            "Source URL": {"url": str(entry.get("url", "")) or None},
            "Summary": {"rich_text": [{"text": {"content": str(entry.get("summary", ""))[:1800]}}]},
            "Priority score": {"number": int(entry.get("importance_score", 0))},
            "Source domains": {"number": int(entry.get("corroboration_count", 1))},
        }
        query_body = {"filter": {"property": "Event key", "rich_text": {"equals": key}}, "page_size": 1}
        query_raw = request(
            f"https://api.notion.com/v1/data_sources/{NOTION_DATA_SOURCE_ID}/query",
            data=json.dumps(query_body).encode("utf-8"), method="POST",
            headers=headers, timeout=30,
        )
        matches = json.loads(query_raw).get("results", [])
        if matches:
            page_id = matches[0]["id"]
            update_body = {"properties": {
                "Last observed": properties["Last observed"],
                "Source domains": properties["Source domains"],
                "Priority score": properties["Priority score"],
                "Summary": properties["Summary"],
            }}
            request(f"https://api.notion.com/v1/pages/{page_id}",
                    data=json.dumps(update_body).encode("utf-8"), method="PATCH",
                    headers=headers, timeout=30)
            updated += 1
        else:
            create_body = {
                "parent": {"type": "data_source_id", "data_source_id": NOTION_DATA_SOURCE_ID},
                "properties": properties,
            }
            request("https://api.notion.com/v1/pages",
                    data=json.dumps(create_body).encode("utf-8"), method="POST",
                    headers=headers, timeout=30)
            created += 1
    return created, updated

def publish_to_notion(digest: dict[str, Any], updates_count: int) -> str:
    token = os.environ["NOTION_TOKEN"]
    today = datetime.now(timezone.utc).astimezone().strftime("%d %b %Y")
    week_start = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)).strftime("%d %b")
    title = f"AI Weekly Digest | {week_start} – {today}"

    blocks: list[dict[str, Any]] = [
        heading(str(digest.get("headline") or "This Week in AI"), 1),
        paragraph(f"Coverage window: last 7 days | Collected feed items: {updates_count} | Generated: {today}"),
        heading("Executive summary"),
        paragraph(digest.get("executive_summary", "No summary was generated.")),
        heading("Top developments"),
    ]

    developments = digest.get("top_developments", [])
    signals = build_ecosystem_signals(CURRENT_UPDATES)
    blocks.append(heading("AI ecosystem change graph"))
    blocks.append(paragraph(f"Analyzed {signals['items_analyzed']} feed records. These are topic-co-occurrence signals, not predictions or causal findings."))
    for signal in signals["topic_company_convergence"][:6]:
        companies = ", ".join(signal["companies"])
        blocks.append(bullet(f"Cross-company convergence: {signal['topic']} | {signal['company_count']} monitored publishers | {companies}"))
    for profile in signals["company_topic_profiles"][:8]:
        leaders = ", ".join(f"{x['topic']} ({x['items']})" for x in profile["leading_topics"])
        blocks.append(bullet(f"{profile['company']} topic footprint: {leaders}"))
    valid_urls = {item["url"] for item in CURRENT_UPDATES}
    added = 0
    for entry in developments:
        url = str(entry.get("url", "")).strip()
        if url not in valid_urls:
            continue
        label = f"{entry.get('title', 'Update')} | {entry.get('company', 'Company')} | {entry.get('date', 'Date')} | {entry.get('importance_band', 'emerging').upper()} ({entry.get('importance_score', 0)}/100) | {entry.get('evidence_level', 'unknown')} evidence | {entry.get('corroboration_count', 1)} source domain(s)"
        label += f" | snippet overlap: {entry.get('status', 'not assessed')} ({entry.get('score', 0)}%)"
        blocks.append(bullet(label, url))
        summary = str(entry.get("summary", "")).strip()
        if summary:
            blocks.append(paragraph(summary))
        why = str(entry.get("why_it_matters", "")).strip()
        if why:
            blocks.append(paragraph("Why it matters: " + why))
        added += 1

    if added == 0:
        blocks.append(paragraph("No sufficiently supported major developments were identified from the monitored feeds this week."))

    notes = digest.get("company_notes", [])
    if notes:
        blocks.append(heading("Company-by-company notes"))
        for note in notes[:15]:
            blocks.append(bullet(str(note)))

    watch = digest.get("watch_next_week", [])
    if watch:
        blocks.append(heading("What to watch next week"))
        for item in watch[:8]:
            blocks.append(bullet(str(item)))

    blocks.extend([
        heading("The week's takeaway"),
        paragraph(digest.get("bottom_line", "Review the linked primary-source coverage before making decisions.")),
        heading("Editorial and verification note"),
        paragraph("Evidence labels: first-party means the linked publisher is the originating organization; research-source means an academic/research feed; secondary means discovery coverage. Corroboration counts distinct URL hostnames among headline-similar records, not independent confirmation of every claim. Importance scores are deterministic prioritization heuristics, not objective truth or quality measurements. Gemini summaries are AI-generated and may contain errors. Open primary sources and compare the underlying evidence before relying on claims."),
    ])

    # Notion accepts at most 100 child blocks per create-page request.
    payload = {
        "parent": {"type": "page_id", "page_id": NOTION_PARENT_PAGE_ID},
        "properties": {"title": {"title": [notion_rich_text(title)]}},
        "children": blocks[:100],
    }
    raw = request("https://api.notion.com/v1/pages", data=json.dumps(payload).encode("utf-8"),
                  method="POST", headers={
                      "Authorization": f"Bearer {token}",
                      "Notion-Version": NOTION_VERSION,
                      "Content-Type": "application/json",
                  }, timeout=45)
    page = json.loads(raw)
    return page.get("url", "")

CURRENT_UPDATES: list[dict[str, str]] = []

def main() -> None:
    global CURRENT_UPDATES
    required = ["GEMINI_API_KEY", "NOTION_TOKEN"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Missing GitHub Actions secrets: " + ", ".join(missing))

    CURRENT_UPDATES = collect_intelligence()
    print(f"Collected {len(CURRENT_UPDATES)} unique feed items.")
    if not CURRENT_UPDATES:
        raise RuntimeError("No feed items were collected. Notion was not updated.")

    digest = call_gemini(CURRENT_UPDATES)
    page_url = publish_to_notion(digest, len(CURRENT_UPDATES))
    created, updated = sync_tracker(digest.get("top_developments", []))
    print(f"[TRACKER] Notion event ledger: {created} new events, {updated} recurring events updated.")
    if not page_url:
        raise RuntimeError("Notion API did not return a page URL.")
    print("Published weekly digest:", page_url)

if __name__ == "__main__":
    main()
