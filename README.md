# FrontierShift

**An AI ecosystem intelligence platform.** FrontierShift collects recent updates from AI research labs, infrastructure companies, and research feeds, then organizes them into a source-linked editorial view with transparent topic and priority signals.

The project combines a Python feed-ingestion API, a responsive editorial website, and a separate scheduled research-digest workflow.

## Product

The public website is designed around three jobs:

- **Discover:** browse and search recent AI developments, filtered by topic.
- **Understand:** see which topics appear across multiple monitored publishers and review each publisher's recent activity.
- **Verify:** open the original publisher or research source. Every story links to its source.

The interface uses a bright, restrained visual system with generous whitespace, precise typography, subtle depth, and responsive layouts. It takes inspiration from premium product editorial design without copying Apple's brand assets or page layouts.

## Current architecture

\`\`\`text
Browser
  |
  v
Vercel static site: public/index.html
  |
  v
/api/news  (Python serverless function)
  |
  +--> Official publisher RSS / Atom feeds
  |
  +--> Research feeds (arXiv cs.AI, cs.LG)
  |
  v
Normalize + date filter + deduplicate
  |
  +--> Topic tagging
  +--> Transparent priority heuristic
  +--> Cross-publisher topic overlap
  |
  v
JSON response + 10-minute instance cache
  |
  v
FrontierShift editorial interface
\`\`\`

A separate GitHub Actions workflow continues to run the weekly AI digest and Notion archive. Notion is not required by the public website.

## Monitored feeds

| Publisher / feed | Type |
|---|---|
| OpenAI | Publisher |
| Google AI | Publisher |
| Google DeepMind | Publisher |
| Google Research | Publisher |
| Hugging Face | Publisher |
| NVIDIA | Publisher |
| AWS Machine Learning | Publisher |
| Microsoft Research | Publisher |
| arXiv cs.AI | Research |
| arXiv cs.LG | Research |

The API checks the most recent 14 days, normalizes dates to UTC, and keeps direct source links. Feed outages are isolated and reported in the API response rather than silently fabricating replacement stories.

## Signals and limitations

- **Priority score:** a deterministic heuristic based on publisher type, selected topic terms, and recency. It is a triage aid, not a measure of truth, quality, or market importance.
- **Topic tags:** transparent keyword rules applied to titles and feed descriptions. They can miss context or misclassify ambiguous wording.
- **Cross-publisher themes:** indicate that multiple monitored feeds contain items tagged with a topic during the same collection window. This does not establish collaboration, causation, competition, or a trend in the wider industry.
- **Publisher evidence:** a direct publisher feed establishes where the item was published, not that every claim in it is independently verified.
- **Coverage:** curated feeds are not exhaustive. Feed format changes, outages, and publication delays can affect results.
- **Freshness:** the API checks feeds on request and caches a successful response in the running function instance for up to 10 minutes. It is not a continuous crawler.

## Run locally

The site is static HTML and the API uses only the Python standard library.

\`\`\`bash
python -m unittest discover -s tests -v
python -m py_compile api/news.py scripts/*.py
\`\`\`

For a local website preview, serve the \`public\` directory with any static file server. The \`/api/news\` endpoint requires a Python-compatible serverless runtime; a plain static server will not execute it.

## Deploy to Vercel

1. Import this GitHub repository into Vercel.
2. Keep the project root set to the repository root.
3. Deploy with the included \`vercel.json\`.
4. Open the deployed site and confirm that \`/api/news\` returns JSON and that stories link to their original sources.

The website does not require a Gemini, Groq, or Notion API key to display publisher-feed items. The separate weekly Notion digest workflow still requires its existing GitHub Actions secrets.

## Continuous integration

The \`FrontierShift CI\` workflow runs on pushes and pull requests to \`main\`. It compiles the Python modules and runs the standard-library unit tests.

## Repository layout

\`\`\`text
.github/workflows/
  frontiershift-ci.yml
  weekly-ai-digest.yml
api/
  news.py
public/
  index.html
scripts/
  evidence_checks.py
  intelligence_graph.py
  source_registry.py
  weekly_ai_digest.py
tests/
  test_api_news.py
  test_evidence_checks.py
  test_intelligence_graph.py
  test_source_registry.py
\`\`\`

## Project status

The website and source-backed feed API have been added to the repository. CI is configured to validate Python syntax and unit tests. A successful CI run and a live Vercel deployment must be confirmed from their respective dashboards before describing the hosted product as production-ready.

## Portfolio description

FrontierShift is a source-linked AI ecosystem intelligence project built with Python and a responsive web interface. It ingests publisher and research feeds, normalizes and deduplicates records, applies explainable topic and priority heuristics, and surfaces cross-publisher topic overlap with direct source links. The project explicitly documents the limits of keyword-based classification and heuristic scoring.
