"""
Daily Briefing - Main Orchestrator
Fetches news, curates via Claude, formats, and sends.

Usage:
    python main.py              # Full run: fetch, curate, format, send
    python main.py --fetch-only # Only fetch and save raw items (for testing)
    python main.py --dry-run    # Full pipeline but don't send email (save HTML locally)
    python main.py --test-email # Send a test email to verify SMTP config
"""

import sys
import json
import yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent / ".env")

from sources import fetch_all_sources
from curator.process import curate_items
from delivery.formatter import format_email
from delivery.sender import send_email


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def run_fetch(config: dict) -> list[dict]:
    """Step 1: Fetch raw items from all sources."""
    print("=" * 60)
    print(f"DAILY BRIEFING  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print("\n[1/4] Fetching sources...")

    items = fetch_all_sources(config=config, hours_back=24)
    return items


def run_curate(raw_items: list[dict]) -> dict:
    """Step 2: Curate via Claude."""
    print("\n[2/4] Curating with Claude...")
    print(f"  Processing {len(raw_items)} raw items...")

    briefing = curate_items(raw_items)

    # Count items in output
    total_output = sum(
        len(briefing.get(section, []))
        for section in ["lead_stories", "tech_ai", "sports", "canada", "world", "environment", "culture", "radar"]
    )
    print(f"  Curated down to {total_output} items across all sections")

    return briefing


def run_format(briefing: dict) -> str:
    """Step 3: Format as HTML email."""
    print("\n[3/4] Formatting email...")
    html = format_email(briefing)
    print(f"  HTML generated ({len(html)} chars)")
    return html


def run_send(html: str, config: dict) -> bool:
    """Step 4: Send via SMTP."""
    print("\n[4/4] Sending email...")
    return send_email(html, config=config)


def now_toronto() -> datetime:
    """Get current time in Toronto (UTC-4 EDT / UTC-5 EST)."""
    eastern = timezone(timedelta(hours=-4))  # EDT
    return datetime.now(eastern)


def main():
    config = load_config()
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Parse args
    args = sys.argv[1:]

    if "--test-email" in args:
        print("Sending test email...")
        # Use the real template with sample data for a proper preview
        sample_briefing = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "lead_stories": [
                {
                    "headline": "Bank of Canada holds overnight rate at 3.25%, cites stable inflation",
                    "summary": "The central bank maintained its benchmark rate at its May decision. Governor Macklem noted inflation at 2.1% remains within target range. Next decision scheduled for July 9.",
                    "source": "Canadian Press",
                    "url": "#",
                },
                {
                    "headline": "Anthropic releases Claude 4 model family with expanded tool use",
                    "summary": "New model series available via API. Benchmarks show 15% improvement on coding and reasoning tasks over previous generation.",
                    "source": "Reuters Technology",
                    "url": "#",
                },
            ],
            "tech_ai": [
                {
                    "headline": "Databricks acquires data observability startup for $1.2B",
                    "summary": "Acquisition expands Databricks' data quality capabilities. Integration expected by Q4 2026.",
                    "source": "TechCrunch",
                    "url": "#",
                },
                {
                    "headline": "Apache Spark 4.0 released with native GPU acceleration",
                    "summary": "Major release includes built-in GPU scheduling and a redesigned Catalyst optimizer for large-scale workloads.",
                    "source": "Hacker News",
                    "url": "#",
                },
            ],
            "sports": [
                {
                    "headline": "Maple Leafs acquire first-round pick in three-team trade",
                    "summary": "Toronto sends two prospects to Calgary in exchange for the 14th overall selection in the 2026 draft. Third team receives a 2027 second-round pick.",
                    "source": "TSN",
                    "url": "#",
                },
                {
                    "headline": "Corey Conners finishes T-4 at the Memorial Tournament",
                    "summary": "Conners shot a final-round 67 at Muirfield Village, his best finish on Tour this season. Earned $820,000.",
                    "source": "PGA Tour",
                    "url": "#",
                },
            ],
            "canada": [
                {
                    "headline": "Ontario introduces bill to expand affordable housing on transit corridors",
                    "summary": "Bill 214 would permit up to 12-storey residential buildings within 500 metres of major transit stations across the province.",
                    "source": "CBC News",
                    "url": "#",
                },
            ],
            "world": [
                {
                    "headline": "EU and Mercosur finalize terms of long-delayed trade agreement",
                    "summary": "The deal eliminates tariffs on 91% of goods traded between the two blocs. Ratification votes expected in autumn.",
                    "source": "Reuters",
                    "url": "#",
                },
            ],
            "environment": [
                {
                    "headline": "Great Lakes water levels reach 15-year high across all five lakes",
                    "summary": "U.S.-Canada International Joint Commission reported May levels exceeding long-term averages by 22 to 35 centimetres.",
                    "source": "The Narwhal",
                    "url": "#",
                },
            ],
            "culture": [
                {
                    "headline": "Luminato Festival announces 2026 lineup featuring 14 world premieres",
                    "summary": "Toronto's annual arts festival runs June 12 to 28. Program includes commissions from three Canadian composers.",
                    "source": "NOW Toronto",
                    "url": "#",
                },
            ],
            "radar": [
                {"headline": "TTC Line 2 weekend closure May 24-25 for signal upgrades", "source": "CBC Toronto", "url": "#"},
                {"headline": "Blue Jays place starting pitcher on 15-day IL with forearm strain", "source": "Sportsnet", "url": "#"},
                {"headline": "Canada Post reaches tentative agreement with rural carriers union", "source": "Canadian Press", "url": "#"},
                {"headline": "OpenAI open-sources its tokenizer library under MIT license", "source": "Hacker News", "url": "#"},
            ],
        }
        html = format_email(sample_briefing)
        success = send_email(html, config=config)
        sys.exit(0 if success else 1)

    # Step 1: Fetch
    raw_items = run_fetch(config)

    # Save raw items for debugging
    raw_path = output_dir / f"raw_{datetime.now().strftime('%Y%m%d')}.json"
    with open(raw_path, "w") as f:
        json.dump(raw_items, f, indent=2, default=str)
    print(f"  Raw items saved to {raw_path}")

    if "--fetch-only" in args:
        print("\n[DONE] Fetch-only mode. Raw items saved.")
        sys.exit(0)

    # Step 2: Curate
    briefing = run_curate(raw_items)

    # Save curated output for debugging
    curated_path = output_dir / f"curated_{datetime.now().strftime('%Y%m%d')}.json"
    with open(curated_path, "w") as f:
        json.dump(briefing, f, indent=2, default=str)

    # Step 3: Format
    html = run_format(briefing)

    # Save HTML for debugging / preview
    html_path = output_dir / f"briefing_{datetime.now().strftime('%Y%m%d')}.html"
    with open(html_path, "w") as f:
        f.write(html)
    print(f"  HTML saved to {html_path}")

    if "--dry-run" in args:
        print(f"\n[DONE] Dry run complete. Open {html_path} to preview.")
        sys.exit(0)

    # Step 4: Send
    success = run_send(html, config)

    if success:
        print("\n" + "=" * 60)
        print("BRIEFING SENT SUCCESSFULLY")
        print("=" * 60)
    else:
        print("\n[FAIL] Email delivery failed. Check logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
