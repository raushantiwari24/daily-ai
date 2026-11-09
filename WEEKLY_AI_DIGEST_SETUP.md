# Weekly AI Intelligence Digest

This workflow collects AI-industry news every Sunday at **9:00 AM India Standard Time**, summarizes the collected feed records with Gemini 3.5 Flash-Lite, validates generated citations against those records, and creates a dated child page under the AI Intelligence Hub in Notion.

## Monitored organizations

OpenAI, Anthropic, Google / Gemini, Google DeepMind, xAI / Grok, Meta / Llama, DeepSeek, Mistral AI, Microsoft, NVIDIA, and Hugging Face.

Discovery currently uses domain-restricted Google News RSS queries. This improves coverage across publishers but is not equivalent to reading and independently verifying every original article.

## Required GitHub Actions secrets

Add these under **Repository → Settings → Secrets and variables → Actions**:

1. `GEMINI_API_KEY`: create a key in [Google AI Studio](https://aistudio.google.com/app/apikey).
2. `NOTION_TOKEN`: create an internal Notion integration, grant it access to the **AI Intelligence Hub** page, and copy its token. See [Notion's integration guide](https://www.notion.com/help/create-integrations-with-the-notion-api).

Never commit either secret to the repository.

## Run a test

Open **Actions → Weekly AI Intelligence Digest → Run workflow**, select `main`, and start the run. A successful run prints the new Notion page URL in the job log.

## Schedule

- Cron: `30 3 * * 0`
- Local time: Sunday, 9:00 AM IST
- The workflow can also be started manually with `workflow_dispatch`.

## Reliability notes

- The collector deduplicates titles and keeps a rolling seven-day window.
- Gemini output is checked for required fields.
- Each published development must cite an exact URL from the collected feed, and its date must match the source record.
- Transient HTTP failures receive bounded retries.
- These checks validate structure and provenance, not the truth of every generated sentence. Always open primary sources before relying on claims.
- Google News RSS can miss relevant stories or surface syndicated coverage.
- Gemini free-tier quotas and model availability depend on Google's current account limits. Do not enable paid billing if you intend to keep API usage free.

## Troubleshooting

- **Gemini HTTP 400/404:** Check the model/API availability and the shortened response detail in the failed Actions step.
- **Gemini HTTP 429:** The API quota or rate limit may have been reached. Retry later or reduce collection volume.
- **Notion HTTP 401/403:** Check that `NOTION_TOKEN` is current and the integration has access to the AI Intelligence Hub page.
- **No feed items:** Check the Actions log; Notion will not be updated when collection returns zero items.

GitHub may disable scheduled workflows after prolonged repository inactivity. Check the Actions tab periodically.
