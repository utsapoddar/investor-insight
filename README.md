# Alpha Digest

A fully automated weekly briefing on what the world's best investors are doing — and why. Tracks 25 top investors, funds, and institutions across SEC filings, crypto treasuries, commodities, and financial news, then distills it into a single concise report delivered every Monday.

**[Read the latest issue →](https://utsapoddar.github.io/alpha-digest)**

## How It Works

A GitHub Actions pipeline runs every Monday morning and executes a five-stage process:

1. **Fetch** — Pulls data from SEC EDGAR (Form 4 insider trades + 13F institutional holdings), CoinGecko corporate crypto treasuries, Yahoo Finance commodity prices, and 12 financial news RSS feeds (MarketWatch, CNBC, WSJ, Seeking Alpha, Bloomberg, and more)
2. **Enrich** — Cross-references raw filings and news against a watchlist of 25 tracked entities, linking trades to the investors who made them
3. **Summarize** — Sends enriched data to Groq (LLM) to produce a concise narrative for each investor — what they did and why it matters
4. **Render** — Generates a styled HTML digest using Jinja2 templates (one for email, one for web)
5. **Deliver** — Emails the digest to subscribers via Gmail SMTP and publishes the web version to this GitHub Pages site

## Tracked Investors

| Investor / Fund | Data Sources |
|---|---|
| Warren Buffett / Berkshire Hathaway | Form 4, 13F, News |
| Michael Burry / Scion Asset Management | Form 4, 13F, News |
| Ray Dalio / Bridgewater Associates | 13F, News |
| Stanley Druckenmiller / Duquesne Family Office | Form 4, 13F, News |
| Howard Marks / Oaktree Capital Management | Form 4, 13F, News |
| Cathie Wood / ARK Invest | 13F, News |
| Jamie Dimon / JPMorgan Chase | Form 4, News |
| Michael Saylor / Strategy | Form 4, 13F, Crypto (BTC), News |
| BlackRock | 13F, News |
| Shopify | 13F, News |
| Jeff Gundlach / DoubleLine Capital | News |
| Eric Nuttall / Ninepoint Partners | 13F, News |
| Jerome Powell / Federal Reserve | News |
| Tiff Macklem / Bank of Canada | News |
| World Gold Council | News |

Plus commodity tracking: Gold, Oil (WTI), Silver.

## Tech Stack

| Component | Tool |
|---|---|
| Language | Python 3.12 |
| SEC data | SEC EDGAR API (Form 4 + 13F) |
| Crypto data | CoinGecko API |
| Commodity data | Yahoo Finance |
| News | Google News RSS + 12 custom RSS feeds |
| LLM | Groq API |
| Templating | Jinja2 |
| Email | Gmail SMTP |
| Hosting | GitHub Pages |
| Automation | GitHub Actions (cron: every Monday 10:00 UTC) |

## Project Structure

Everything lives in this repo: the pipeline on `main`, the published site on `gh-pages`.

```
main/                       # Pipeline
├── main.py                 # Pipeline entrypoint
├── watchlist.csv           # 25 tracked entities + SEC CIKs
├── config/
│   ├── sources.yaml        # Toggle fetchers on/off
│   ├── feeds.csv           # 12 custom RSS feed URLs
│   └── recipients.example.yaml  # Subscriber list template
├── digest/
│   ├── fetchers/           # SEC EDGAR, news, crypto, commodities
│   ├── enrichers/          # Cross-reference + context
│   ├── summarizer.py       # LLM summarization
│   ├── renderer.py         # Jinja2 HTML rendering
│   ├── notifier.py         # Gmail SMTP delivery
│   └── publisher.py        # Publishes to gh-pages
├── templates/
│   ├── digest_email.html.j2
│   ├── digest_web.html.j2
│   ├── landing_page.html.j2
│   └── archive_index.html.j2
└── .github/workflows/
    └── weekly-digest.yml   # Cron automation

gh-pages/                   # Published site
├── index.html              # Landing page
└── archive/                # Every published weekly digest
```

## Configuration

Recipient addresses are personal data and are kept out of the repo. In CI, set the
`DIGEST_RECIPIENTS` secret to a comma-separated list. Locally, copy
`config/recipients.example.yaml` to `config/recipients.yaml` (gitignored).

Required secrets: `GEMINI_API_KEY`, `NVIDIA_API_KEY`, `GMAIL_ADDRESS`,
`GMAIL_APP_PASSWORD`, `ALPHA_DIGEST_TOKEN`, `DIGEST_RECIPIENTS`.

## Sample Output

Each digest includes:
- **Macro context** — Key market events and Fed/BoC decisions
- **Commodity snapshot** — Weekly price changes for gold, oil, and silver
- **Per-investor briefings** — What each investor bought/sold, with SEC filing links and AI-generated context on why

Built by [Utsa Poddar](https://utsapoddar.github.io)
