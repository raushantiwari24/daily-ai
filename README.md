# AI Intelligence Digest

An automated weekly AI-industry intelligence pipeline that ingests first-party publisher feeds and research feeds, uses secondary news discovery for coverage gaps, computes transparent evidence and priority signals, uses Gemini to synthesize a briefing, validates source provenance, and publishes the result to Notion.

**Schedule:** Sundays at 9:00 AM India Standard Time (03:30 UTC)  
**Output:** A dated page in the connected Notion workspace  
**Status:** Working prototype with automated structural validation. Source claims still require human review.

## What it does

1. Ingests rolling seven-day updates from direct publisher feeds (OpenAI, Google AI, DeepMind, Google Research, Hugging Face, NVIDIA, AWS ML, Microsoft Research) and arXiv research feeds.
2. Uses Google News RSS as a secondary discovery layer, not as primary evidence.
3. Normalizes dates and URLs, then computes headline-similarity clusters, distinct-host corroboration counts, evidence labels, and a transparent 0-100 prioritization heuristic.
4. Sends the source records and evidence metadata to Gemini 3.5 Flash-Lite for synthesis.
5. Validates response structure, exact source URLs, and dates before publication.
6. Publishes the digest to Notion with evidence labels, importance bands, source links, and explicit limitations.

## Monitored organizations

OpenAI, Anthropic, Google / Gemini, Google DeepMind, xAI / Grok, Meta / Llama, DeepSeek, Mistral AI, Microsoft, NVIDIA, and Hugging Face.

## Architecture

```text
GitHub Actions (weekly schedule / manual run)
                 |
                 v
      Google News RSS discovery
                 |
                 v
       Normalize + deduplicate
                 |
                 v
        Gemini 3.5 Flash-Lite
                 |
                 v
   Schema + source URL/date validation
                 |
                 v
       Notion API page publishing
```

## Reliability and known limitations

- **Citation integrity:** A generated development is only retained when its URL exactly matches a collected feed item and its date matches that item.
- **Not independent fact-checking:** A matching URL proves provenance to a feed record, not that every sentence in the AI summary is true. Open the original article before relying on a claim.
- **Source coverage:** First-party feeds are curated, not exhaustive. Feed outages and publisher format changes can reduce coverage. Secondary Google News discovery can miss announcements, include duplicate syndication, or surface low-quality coverage.
- **Corroboration is heuristic:** Similarity clusters and distinct-host counts are triage signals. They do not prove that publishers are independent or that every claim is true.
- **Importance score:** A transparent heuristic based on source type, topic keywords, corroboration and recency. It is for prioritization, not an objective measure of truth.
- **No continuous monitoring:** The workflow runs weekly, not continuously.
- **Failure handling:** Transient HTTP errors are retried with bounded backoff. Non-retryable API errors include a shortened response detail in the Actions log.

## Setup

Create two GitHub Actions repository secrets:

| Secret | Purpose |
|---|---|
| `GEMINI_API_KEY` | Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `NOTION_TOKEN` | Internal Notion integration token with access to the AI Intelligence Hub parent page |

Never commit secrets or paste them into issues, logs, or chat.

Then open **Actions → Weekly AI Intelligence Digest → Run workflow** to run a manual test on `main`.

## Schedule

The cron expression is `30 3 * * 0`, which is Sunday at 03:30 UTC / 9:00 AM IST.

## Repository structure

```text
.github/workflows/weekly-ai-digest.yml
scripts/weekly_ai_digest.py
scripts/source_registry.py
WEEKLY_AI_DIGEST_SETUP.md
README.md
```

## Roadmap

- Add robust publisher-specific sitemap/page adapters for companies without stable RSS feeds.
- Resolve syndicated links to original publisher URLs and detect shared wire-service sources.
- Add claim-level extraction and evidence matching against source article text.
- Add automated unit tests, integration fixtures, and a preview/dry-run mode before publishing.
- Persist structured developments to a Notion database for longitudinal trend analysis.
- Publish structured entries into the AI Updates Tracker database as well as the weekly briefing page.

## Portfolio note

This project demonstrates scheduled data ingestion, deduplication, LLM-based information extraction, validation, API integration, and automated publishing. Describe it as an **AI-assisted news intelligence pipeline**, not as a fully fact-checked news service.
