"""News source fetchers."""

from .rss_fetcher import fetch_rss_feeds
from .reddit_fetcher import fetch_all_reddit
from .hackernews_fetcher import fetch_hackernews


def fetch_all_sources(config: dict = None, hours_back: int = 24) -> list[dict]:
    """Fetch from all configured sources and return combined item list."""
    all_items = []

    all_items.extend(fetch_rss_feeds(config=config, hours_back=hours_back))
    all_items.extend(fetch_all_reddit(config=config, hours_back=hours_back))
    all_items.extend(fetch_hackernews(config=config, hours_back=hours_back))

    print(f"\n[TOTAL] Collected {len(all_items)} raw items from all sources")
    return all_items
