"""
Reddit Fetcher
Pulls top posts from configured subreddits using RSS feeds (no auth, no rate limits).
Reddit exposes RSS at /r/{subreddit}/.rss which works from any IP including CI servers.
"""

import re
import feedparser
import requests
import yaml
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from pathlib import Path
from typing import Optional

FEED_TIMEOUT = 10


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def fetch_subreddit_rss(subreddit: str, top_n: int = 10, hours_back: int = 24) -> list[dict]:
    """Fetch posts from a subreddit via RSS feed."""
    cutoff = datetime.now() - timedelta(hours=hours_back)
    items = []

    # Reddit RSS endpoint (not blocked like JSON API)
    rss_url = f"https://www.reddit.com/{subreddit}/.rss"

    try:
        resp = requests.get(rss_url, timeout=FEED_TIMEOUT, headers={
            "User-Agent": "DailyBriefing/1.0 (personal newsletter aggregator)"
        })
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        for entry in feed.entries:
            # Parse date
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])
            else:
                continue

            if published < cutoff:
                continue

            # Extract title and clean description
            title = entry.get("title", "Untitled")
            description = entry.get("summary", "")
            description = re.sub(r"<[^>]+>", "", description).strip()
            if len(description) > 500:
                description = description[:500] + "..."

            # Get the actual link (not the reddit comments link)
            url = entry.get("link", "")

            items.append({
                "title": title,
                "url": url,
                "description": description,
                "published": published.isoformat(),
                "source_name": f"Reddit {subreddit}",
                "source_url": f"https://www.reddit.com/{subreddit}",
                "type": "reddit",
            })

            if len(items) >= top_n:
                break

    except Exception as e:
        print(f"[WARN] Failed to fetch {subreddit} RSS: {e}")

    return items


def fetch_all_reddit(config: Optional[dict] = None, hours_back: int = 24) -> list[dict]:
    """Fetch from all configured subreddits via RSS."""
    if config is None:
        config = load_config()

    all_items = []
    reddit_config = None

    for api in config["sources"]["apis"]:
        if api["name"] == "reddit":
            reddit_config = api
            break

    if not reddit_config:
        return []

    for sub_config in reddit_config["subreddits"]:
        subreddit = sub_config["name"]
        categories = sub_config["categories"]
        top_n = sub_config.get("top_n", 10)

        posts = fetch_subreddit_rss(subreddit, top_n=top_n, hours_back=hours_back)

        for post in posts:
            post["categories"] = categories

        all_items.extend(posts)

    print(f"[Reddit] Fetched {len(all_items)} posts from {len(reddit_config['subreddits'])} subreddits")
    return all_items


if __name__ == "__main__":
    import json
    items = fetch_all_reddit()
    print(json.dumps(items[:5], indent=2, default=str))
