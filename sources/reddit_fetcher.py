"""
Reddit Fetcher
Pulls top posts from configured subreddits using public JSON API (no auth needed).
"""

import requests
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import time


USER_AGENT = "DailyBriefing/1.0 (personal newsletter aggregator)"
REDDIT_BASE = "https://www.reddit.com"


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def fetch_subreddit(subreddit: str, top_n: int = 10, hours_back: int = 24) -> list[dict]:
    """Fetch top posts from a subreddit within the time window."""
    cutoff_ts = (datetime.now() - timedelta(hours=hours_back)).timestamp()
    items = []

    url = f"{REDDIT_BASE}/{subreddit}/hot.json?limit={top_n * 2}"
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        for post in data.get("data", {}).get("children", []):
            post_data = post["data"]

            # Skip stickied/pinned posts
            if post_data.get("stickied", False):
                continue

            # Skip posts older than cutoff
            created = post_data.get("created_utc", 0)
            if created < cutoff_ts:
                continue

            # Skip low-engagement posts (noise filter)
            score = post_data.get("score", 0)
            if score < 10:
                continue

            items.append({
                "title": post_data.get("title", "Untitled"),
                "url": post_data.get("url", ""),
                "description": post_data.get("selftext", "")[:500] or post_data.get("title", ""),
                "published": datetime.fromtimestamp(created).isoformat(),
                "source_name": f"Reddit {subreddit}",
                "source_url": f"{REDDIT_BASE}/{subreddit}",
                "score": score,
                "num_comments": post_data.get("num_comments", 0),
                "type": "reddit",
            })

            if len(items) >= top_n:
                break

    except Exception as e:
        print(f"[WARN] Failed to fetch {subreddit}: {e}")

    return items


def fetch_all_reddit(config: Optional[dict] = None, hours_back: int = 24) -> list[dict]:
    """Fetch from all configured subreddits."""
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

        posts = fetch_subreddit(subreddit, top_n=top_n, hours_back=hours_back)

        # Tag posts with categories
        for post in posts:
            post["categories"] = categories

        all_items.extend(posts)

        # Respect rate limits
        time.sleep(1)

    print(f"[Reddit] Fetched {len(all_items)} posts from {len(reddit_config['subreddits'])} subreddits")
    return all_items


if __name__ == "__main__":
    import json
    items = fetch_all_reddit()
    print(json.dumps(items[:5], indent=2, default=str))
