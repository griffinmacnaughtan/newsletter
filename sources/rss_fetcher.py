"""
RSS Feed Fetcher
Pulls articles from configured RSS feeds and returns structured items.
"""

import re
import requests
import feedparser
import yaml
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from pathlib import Path
from typing import Optional

FEED_TIMEOUT = 10  # seconds per feed


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def fetch_single_feed(url: str, timeout: int = FEED_TIMEOUT) -> feedparser.FeedParserDict:
    """Fetch a feed with a hard timeout using requests first."""
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "DailyBriefing/1.0"})
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except Exception:
        # Fallback: let feedparser try directly (some feeds need special handling)
        return feedparser.parse(url)


def fetch_rss_feeds(config: Optional[dict] = None, hours_back: int = 24) -> list[dict]:
    """
    Fetch all configured RSS feeds and return structured items.
    Only includes items published within the last `hours_back` hours.
    """
    if config is None:
        config = load_config()

    cutoff = datetime.now() - timedelta(hours=hours_back)
    items = []
    success_count = 0
    fail_count = 0

    for feed_config in config["sources"]["rss"]:
        url = feed_config["url"]
        categories = feed_config["categories"]
        tier = feed_config.get("tier", 2)

        try:
            feed = fetch_single_feed(url)
            success_count += 1

            for entry in feed.entries:
                # Parse publication date
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])
                elif hasattr(entry, "published"):
                    try:
                        published = dateparser.parse(entry.published)
                    except (ValueError, TypeError):
                        published = datetime.now()
                else:
                    published = datetime.now()

                # Skip items older than cutoff
                if published < cutoff:
                    continue

                # Extract description/summary
                description = ""
                if hasattr(entry, "summary"):
                    description = entry.summary
                elif hasattr(entry, "description"):
                    description = entry.description

                # Strip HTML tags
                description = re.sub(r"<[^>]+>", "", description).strip()
                if len(description) > 500:
                    description = description[:500] + "..."

                items.append({
                    "title": entry.get("title", "Untitled"),
                    "url": entry.get("link", ""),
                    "description": description,
                    "published": published.isoformat(),
                    "source_url": url,
                    "source_name": feed.feed.get("title", url),
                    "categories": categories,
                    "tier": tier,
                    "type": "rss",
                })

        except Exception as e:
            fail_count += 1
            print(f"[WARN] Failed to fetch {url}: {e}")
            continue

    print(f"[RSS] Fetched {len(items)} items from {success_count}/{success_count + fail_count} feeds")
    return items


if __name__ == "__main__":
    import json
    items = fetch_rss_feeds()
    print(json.dumps(items[:5], indent=2, default=str))
