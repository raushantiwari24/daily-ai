import hashlib
import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

FEEDS = [
    ("OpenAI", "https://openai.com/news/rss.xml", "Primary"),
    ("Google AI", "https://blog.google/technology/ai/rss/", "Primary"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml", "Primary"),
    ("Google Research", "https://research.google/blog/rss/", "Primary"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml", "Primary"),
    ("NVIDIA", "https://blogs.nvidia.com/feed/", "Primary"),
    ("AWS Machine Learning", "https://aws.amazon.com/blogs/machine-learning/feed/", "Primary"),
    ("Microsoft Research", "https://www.microsoft.com/en-us/research/feed/", "Primary"),
    ("arXiv cs.AI", "https://rss.arxiv.org/rss/cs.AI", "Research"),
    ("arXiv cs.LG", "https://rss.arxiv.org/rss/cs.LG", "Research"),
]
TOPICS = {
    "Reasoning": ("reasoning", "deliberation", "thinking", "solver"),
    "Agents": ("agent", "tool use", "workflow"),
    "Multimodal": ("multimodal", "image", "video", "audio", "speech"),
    "Coding": ("coding", "code", "developer", "software", "programming"),
    "Models": ("model", "llm", "weights"),
    "Open models": ("open source", "open-source", "open weights", "open-weight"),
    "Infrastructure": ("gpu", "chip", "inference", "compute", "datacenter"),
    "Safety": ("safety", "alignment", "security", "red team"),
    "Research": ("research", "paper", "arxiv", "benchmark", "evaluation"),
    "Enterprise": ("enterprise", "business", "workspace", "deployment"),
    "Robotics": ("robot", "robotics", "embodied", "physical ai"),
}
CACHE_SECONDS = 600
_CACHE = {"at": 0, "payload": None}
_STOP = {"the", "and", "for", "with", "from", "that", "this", "into", "after", "have", "has", "are", "was", "were", "will", "its", "their", "new", "how", "what", "why"}

def clean(value):
    value = re.sub(r"<[^>]*>", " ", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value

def date_value(value):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except Exception:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def node_text(node, names):
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return found.text.strip()
    return ""

def fetch_feed(feed):
    publisher, url, tier = feed
    request = urllib.request.Request(url, headers={"User-Agent": "FrontierShift/1.0 (+https://github.com/raushantiwari24/daily-ai)"})
    with urllib.request.urlopen(request, timeout=7) as response:
        root = ET.fromstring(response.read())
    nodes = root.findall(".//item")
    atom = False
    if not nodes:
        atom = True
        nodes = root.findall(".//{http://www.w3.org/2005/Atom}entry")
    results = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    for node in nodes:
        if atom:
            title = clean(node_text(node, ["{http://www.w3.org/2005/Atom}title"]))
            link_node = node.find("{http://www.w3.org/2005/Atom}link")
            link = link_node.attrib.get("href", "") if link_node is not None else ""
            date_raw = node_text(node, ["{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated"])
            description = clean(node_text(node, ["{http://www.w3.org/2005/Atom}summary", "{http://www.w3.org/2005/Atom}content"]))
        else:
            title = clean(node_text(node, ["title"]))
            link = node_text(node, ["link"])
            date_raw = node_text(node, ["pubDate", "published", "updated"])
            description = clean(node_text(node, ["description", "{http://purl.org/rss/1.0/modules/content/}encoded"]))
        published = date_value(date_raw)
        if not title or not link or not published or published < cutoff:
            continue
        parsed = urlsplit(link)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        results.append({
            "id": hashlib.sha1(link.encode("utf-8")).hexdigest()[:16],
            "title": title[:260],
            "summary": description[:650],
            "url": link,
            "source": publisher,
            "source_type": tier,
            "date": published.isoformat(),
            "date_label": published.strftime("%b %d, %Y"),
        })
    return results

def categorize(text):
    value = text.lower()
    rules = [
        ("Research", ("paper", "research", "study", "benchmark", "evaluation", "arxiv")),
        ("Models", ("model", "llm", "weights", "reasoning", "multimodal")),
        ("Products", ("launch", "release", "introduces", "available", "product", "api")),
        ("Safety", ("safety", "alignment", "security", "policy", "responsible ai")),
        ("Infrastructure", ("gpu", "chip", "inference", "compute", "datacenter")),
    ]
    for label, terms in rules:
        if any(term in value for term in terms):
            return label
    return "Industry"

def rank(item):
    text = (item["title"] + " " + item["summary"]).lower()
    weights = {"release": 3, "launch": 3, "benchmark": 3, "model": 2, "research": 2, "open source": 3, "safety": 2, "api": 2, "reasoning": 2, "agent": 2}
    points = sum(weight for term, weight in weights.items() if term in text)
    age = max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(item["date"])).days)
    score = min(100, (36 if item["source_type"] == "Primary" else 28) + min(36, points * 4) + max(0, 28 - age * 2))
    item["priority_score"] = score
    item["priority"] = "High" if score >= 72 else "Medium" if score >= 50 else "Emerging"
    item["category"] = categorize(text)
    item["topics"] = [topic for topic, terms in TOPICS.items() if any(term in text for term in terms)]
    item["evidence"] = "Publisher source" if item["source_type"] == "Primary" else "Research feed"
    return item

def build_payload():
    records = []
    failures = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(fetch_feed, feed): feed[0] for feed in FEEDS}
        for future in as_completed(futures):
            publisher = futures[future]
            try:
                records.extend(future.result())
            except Exception as exc:
                failures.append(publisher)
                print("[feed warning] " + publisher + ": " + str(exc))
    unique = {}
    for item in records:
        key = re.sub(r"[^a-z0-9]", "", item["title"].lower())
        if key not in unique or item["source_type"] == "Primary":
            unique[key] = item
    articles = [rank(item) for item in unique.values()]
    articles.sort(key=lambda item: (item["priority_score"], item["date"]), reverse=True)
    articles = articles[:60]
    company_topics = {}
    topic_companies = {}
    for item in articles:
        company = item["source"]
        company_topics.setdefault(company, {})
        for topic in item["topics"]:
            company_topics[company][topic] = company_topics[company].get(topic, 0) + 1
            topic_companies.setdefault(topic, set()).add(company)
    convergence = []
    for topic, companies in topic_companies.items():
        if len(companies) > 1:
            convergence.append({"topic": topic, "companies": sorted(companies), "count": len(companies)})
    convergence.sort(key=lambda x: (-x["count"], x["topic"]))
    profiles = []
    for company, counts in company_topics.items():
        leading = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:3]
        profiles.append({"company": company, "topics": [{"name": k, "count": v} for k, v in leading], "stories": sum(counts.values())})
    profiles.sort(key=lambda x: (-x["stories"], x["company"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": 14,
        "articles": articles,
        "convergence": convergence[:8],
        "companies": profiles[:10],
        "sources_checked": len(FEEDS),
        "sources_failed": failures,
        "source_note": "Stories link directly to publisher or research feeds. Topic overlap is a discovery signal, not proof of a relationship. Priority is a transparent heuristic, not a truth score.",
    }

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        now = time.time()
        if _CACHE["payload"] is not None and now - _CACHE["at"] < CACHE_SECONDS:
            payload = _CACHE["payload"]
        else:
            try:
                payload = build_payload()
                _CACHE["payload"] = payload
                _CACHE["at"] = now
            except Exception as exc:
                self.send_response(502)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "The intelligence feeds could not be loaded.", "detail": str(exc)}).encode())
                return
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=300, stale-while-revalidate=600")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
