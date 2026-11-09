# Weekly AI Intelligence Digest

This workflow collects recent AI-company updates every Sunday at **9:00 AM India Standard Time**, summarizes them with Gemini 2.5 Flash-Lite, and creates a dated child page under the AI Intelligence Hub in Notion.

## Monitored publishers

OpenAI, Anthropic, Google / Gemini, Google DeepMind, xAI / Grok, Meta / Llama, DeepSeek, Mistral AI, Microsoft, NVIDIA, and Hugging Face. Collection uses domain-restricted Google News RSS queries. The digest keeps source links and labels its contents as AI-assisted leads rather than claiming independent verification.

## One-time setup required

Add these two repository Actions secrets. Never commit either value to the repository.

1. `GEMINI_API_KEY`: create a key in [Google AI Studio](https://aistudio.google.com/app/apikey). The workflow uses the Gemini 2.5 Flash-Lite model. Free-tier availability and quotas depend on Google's current account and model limits.
2. `NOTION_TOKEN`: create an internal Notion integration, give it access to the **AI Intelligence Hub** page, and copy its secret token. Notion's guide: [Create an integration](https://www.notion.com/help/create-integrations-with-the-notion-api).

In GitHub, open **Settings → Secrets and variables → Actions → New repository secret** and add each secret with the exact name above.

## Run a test

Open the repository's **Actions** tab, select **Weekly AI Intelligence Digest**, choose **Run workflow**, and start it on the `main` branch. A successful run prints the new Notion page URL in the job log.

## Schedule and cost

- Schedule: Sundays, 9:00 AM IST.
- GitHub Actions: standard GitHub-hosted runners are free for public repositories.
- Gemini: uses the free tier when available. Free-tier quotas and model availability can change; do not enable paid billing if you want to keep this project at zero API cost.
- Notion: uses the existing workspace and API integration.

A scheduled run is not active until both secrets are configured, the Notion integration is granted access to the parent page, and a manual test succeeds. Public-repository scheduled workflows can be disabled by GitHub after 60 days without repository activity, so check the Actions tab periodically.
