"""
Hacker News Fetcher
Pulls top stories from the HN Firebase API (fully public, no auth).
"""

import requests
from datetime import datetime, timedelta
from typing import Optional
import yaml
from pathlib import Path


HN_BASE = "https://hacker-news.firebaseio.com/v0"


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def fetch_item(item_id: int) -> Optional[dict]:
    """Fetch a single HN item by ID."""
    try:
        resp = requests.get(f"{HN_BASE}/item/{item_id}.json", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def fetch_hackernews(config: Optional[dict] = None, hours_back: int = 24) -> list[dict]:
    """Fetch top HN stories within the time window."""
    if config is None:
        config = load_config()

    # Determine how many to fetch from config
    top_n = 30
    for api in config["sources"]["apis"]:
        if api["name"] == "hacker_news":
            top_n = api.get("top_n", 30)
            break

    cutoff_ts = (datetime.now() - timedelta(hours=hours_back)).timestamp()
    items = []

    try:
        # Get top story IDs
        resp = requests.get(f"{HN_BASE}/topstories.json", timeout=10)
        resp.raise_for_status()
        story_ids = resp.json()[:top_n * 2]  # Fetch extra to account for filtering
    except Exception as e:
        print(f"[WARN] Failed to fetch HN top stories: {e}")
        return []

    for story_id in story_ids:
        if len(items) >= top_n:
            break

        story = fetch_item(story_id)
        if not story:
            continue

        # Skip items that aren't stories
        if story.get("type") != "story":
            continue

        # Skip old items
        created = story.get("time", 0)
        if created < cutoff_ts:
            continue

        # Skip low-score items
        score = story.get("score", 0)
        if score < 20:
            continue

        items.append({
            "title": story.get("title", "Untitled"),
            "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
            "description": "",  # HN stories don't have descriptions
            "published": datetime.fromtimestamp(created).isoformat(),
            "source_name": "Hacker News",
            "source_url": f"https://news.ycombinator.com/item?id={story_id}",
            "score": score,
            "num_comments": story.get("descendants", 0),
            "categories": ["tech_ai_data"],
            "tier": 2,
            "type": "hackernews",
        })

    print(f"[HN] Fetched {len(items)} stories")
    return items


if __name__ == "__main__":
    import json
    items = fetch_hackernews()
    print(json.dumps(items[:5], indent=2, default=str))
