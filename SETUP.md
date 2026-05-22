# Daily Briefing — Setup Guide

## One-Time Setup (15 minutes)

### 1. Install dependencies

```bash
cd /c/code/newsletter
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Generate Rogers/Yahoo app password

Rogers email uses Yahoo Mail infrastructure. You need an "app password" (not your regular password) for the script to send emails.

1. Go to https://login.yahoo.com/account/security
2. Sign in with your Rogers email (gmacnaughtan@rogers.com)
3. Scroll to "Generate app password" (or "Manage app passwords")
4. Select "Other app" → name it "Daily Briefing"
5. Copy the generated password

### 3. Set environment variables

Create a `.env` file (or set in your system):

```bash
cp .env.example .env
# Edit .env with your actual values:
# NEWSLETTER_SMTP_PASSWORD=the_app_password_from_step_2
# ANTHROPIC_API_KEY=your_key
```

Or export directly:
```bash
export NEWSLETTER_SMTP_PASSWORD="your_app_password"
export ANTHROPIC_API_KEY="your_api_key"
```

### 4. Test email delivery

```bash
python main.py --test-email
```

Check your inbox. If it arrives, you're good.

### 5. Test full pipeline (dry run)

```bash
python main.py --dry-run
```

This fetches real news, curates it, and saves the HTML locally (won't send). Open `output/briefing_YYYYMMDD.html` in a browser to preview.

### 6. Schedule for 7:30 AM daily

**Option A: Windows Task Scheduler**
```
schtasks /create /tn "DailyBriefing" /tr "C:\code\newsletter\venv\Scripts\python.exe C:\code\newsletter\main.py" /sc daily /st 07:00
```
(Runs at 7:00 to allow processing time — email arrives ~7:15-7:30)

**Option B: Claude Code Scheduled Task**
Use `/schedule` in Claude Code to set up a daily run.

**Option C: GitHub Actions (runs even when PC is off)**
See `.github/workflows/newsletter.yml` (create this if you want cloud scheduling).

---

## Usage

| Command | What it does |
|---------|-------------|
| `python main.py` | Full run — fetch, curate, format, send |
| `python main.py --dry-run` | Everything except sending (preview locally) |
| `python main.py --fetch-only` | Only fetch raw items (test sources) |
| `python main.py --test-email` | Send a test email to verify SMTP |

## Customization

- **Add/remove sources**: Edit `config.yaml` → `sources` section
- **Change priorities**: Edit `config.yaml` → `interests` weights
- **Adjust section sizes**: Edit `config.yaml` → `format.sections.max_items`
- **Change email style**: Edit `delivery/template.html`
- **Tweak curation rules**: Edit `curator/prompt.py`

## Architecture

```
main.py                  ← orchestrator
├── sources/
│   ├── rss_fetcher.py   ← pulls RSS feeds
│   ├── reddit_fetcher.py ← pulls Reddit JSON
│   └── hackernews_fetcher.py ← pulls HN API
├── curator/
│   ├── prompt.py        ← editorial rules for Claude
│   └── process.py       ← sends items to Claude API
├── delivery/
│   ├── formatter.py     ← renders HTML from template
│   ├── template.html    ← email HTML template
│   └── sender.py        ← SMTP delivery
├── config.yaml          ← all configuration
└── output/              ← daily artifacts (gitignored)
```

## Cost

- RSS feeds: free
- Reddit JSON: free (public, no API key)
- Hacker News API: free
- Claude API: ~$0.01-0.03 per run (one Sonnet call processing ~300 items)
- Rogers SMTP: free (you're emailing yourself)
- **Total: ~$0.50-1.00/month** for Claude API usage
