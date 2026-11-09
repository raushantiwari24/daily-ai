# AI Intelligence Digest

An automated weekly AI-industry intelligence pipeline that collects updates from monitored publishers, uses Gemini to synthesize a concise briefing, validates generated citations against collected source records, and publishes the result to Notion.

**Schedule:** Sundays at 9:00 AM India Standard Time (03:30 UTC)  
**Output:** A dated page in the connected Notion workspace  
**Status:** Working prototype with automated structural validation. Source claims still require human review.

## What it does

1. Collects recent AI-related stories for 11 monitored organizations through domain-restricted Google News RSS searches.
2. Removes duplicate headlines and keeps a rolling seven-day window.
3. Sends the collected titles, snippets, dates, and links to Gemini 3.5 Flash-Lite.
4. Asks Gemini for an executive summary, key developments, company notes, and watchlist.
5. Validates the response structure, limits the number of developments, and rejects citations or dates that do not match the collected source records.
6. Publishes the digest to Notion with clickable source links and an explicit editorial verification note.

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
- **Discovery coverage:** Google News RSS is a discovery layer. It can miss announcements, include duplicate syndication, or surface low-quality coverage.
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
WEEKLY_AI_DIGEST_SETUP.md
README.md
```

## Roadmap

- Replace broad RSS discovery with a curated registry of first-party feeds and publisher pages.
- Resolve syndicated links to original publisher URLs where possible.
- Add source-tier labels and cross-source corroboration for major claims.
- Add automated unit tests and a preview/dry-run mode before publishing.
- Publish structured entries into the AI Updates Tracker database as well as the weekly briefing page.

## Portfolio note

This project demonstrates scheduled data ingestion, deduplication, LLM-based information extraction, validation, API integration, and automated publishing. Describe it as an **AI-assisted news intelligence pipeline**, not as a fully fact-checked news service.
