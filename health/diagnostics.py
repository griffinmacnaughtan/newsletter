"""
Post-run diagnostics
Analyzes each day's pipeline output and generates a health report.
Saves to health/reports/ as daily JSON artifacts.
"""

import json
from datetime import datetime
from collections import Counter
from pathlib import Path


def run_diagnostics(raw_items: list[dict], briefing: dict, config: dict) -> dict:
    """
    Analyze today's pipeline run and return a health report.
    Designed to catch recurring issues before they become blind spots.
    """
    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "source_health": analyze_source_health(raw_items, config),
        "section_coverage": analyze_section_coverage(briefing),
        "source_diversity": analyze_source_diversity(briefing),
        "issues": [],
    }

    # Flag issues
    for feed in report["source_health"]["failed_feeds"]:
        report["issues"].append({
            "severity": "warn",
            "type": "dead_feed",
            "detail": f"Feed returned 0 items: {feed}",
        })

    for section, count in report["section_coverage"].items():
        if count == 0 and section != "error":
            report["issues"].append({
                "severity": "warn",
                "type": "empty_section",
                "detail": f"Section '{section}' has 0 items",
            })

    dominant = report["source_diversity"].get("dominant_source")
    if dominant and dominant["percentage"] > 60:
        report["issues"].append({
            "severity": "warn",
            "type": "source_concentration",
            "detail": f"{dominant['name']} accounts for {dominant['percentage']}% of items",
        })

    total_issues = len(report["issues"])
    report["status"] = "healthy" if total_issues == 0 else f"{total_issues} issues detected"

    return report


def analyze_source_health(raw_items: list[dict], config: dict) -> dict:
    """Check which configured feeds actually returned items."""
    configured_feeds = set()
    for feed in config.get("sources", {}).get("rss", []):
        configured_feeds.add(feed["url"])

    feeds_with_items = set()
    for item in raw_items:
        if item.get("source_url"):
            feeds_with_items.add(item["source_url"])

    failed_feeds = list(configured_feeds - feeds_with_items)

    # Count items per source type
    type_counts = Counter(item.get("type", "unknown") for item in raw_items)

    return {
        "total_raw_items": len(raw_items),
        "configured_rss_feeds": len(configured_feeds),
        "active_rss_feeds": len(feeds_with_items & configured_feeds),
        "failed_feeds": sorted(failed_feeds),
        "items_by_type": dict(type_counts),
    }


def analyze_section_coverage(briefing: dict) -> dict:
    """Count items per section in the curated output."""
    sections = [
        "lead_stories", "tech_ai", "sports", "canada",
        "world", "environment", "culture", "radar"
    ]
    return {s: len(briefing.get(s, [])) for s in sections}


def analyze_source_diversity(briefing: dict) -> dict:
    """Check if any single source dominates the output."""
    all_sources = []
    for section in ["lead_stories", "tech_ai", "sports", "canada",
                     "world", "environment", "culture"]:
        for item in briefing.get(section, []):
            source = item.get("source", "Unknown")
            all_sources.append(source)

    if not all_sources:
        return {"total_items": 0, "sources": {}, "dominant_source": None}

    source_counts = Counter(all_sources)
    total = len(all_sources)

    dominant_name = source_counts.most_common(1)[0][0]
    dominant_count = source_counts.most_common(1)[0][1]
    dominant_pct = round((dominant_count / total) * 100)

    return {
        "total_items": total,
        "sources": dict(source_counts),
        "dominant_source": {
            "name": dominant_name,
            "count": dominant_count,
            "percentage": dominant_pct,
        },
    }


def save_report(report: dict, output_dir: Path) -> Path:
    """Save the health report to disk."""
    health_dir = output_dir / "health"
    health_dir.mkdir(exist_ok=True)
    path = health_dir / f"health_{report['date']}.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    return path


def print_report(report: dict):
    """Print a human-readable summary to stdout."""
    print(f"\n{'=' * 60}")
    print(f"HEALTH CHECK  |  {report['date']}")
    print(f"{'=' * 60}")

    sh = report["source_health"]
    print(f"\n  Sources: {sh['active_rss_feeds']}/{sh['configured_rss_feeds']} RSS feeds active")
    print(f"  Raw items: {sh['total_raw_items']} ({', '.join(f'{v} {k}' for k, v in sh['items_by_type'].items())})")

    sc = report["section_coverage"]
    print(f"\n  Sections: {', '.join(f'{k}={v}' for k, v in sc.items())}")

    sd = report["source_diversity"]
    if sd.get("dominant_source"):
        ds = sd["dominant_source"]
        print(f"\n  Top source: {ds['name']} ({ds['percentage']}% of curated items)")

    if report["issues"]:
        print(f"\n  Issues ({len(report['issues'])}):")
        for issue in report["issues"]:
            print(f"    [{issue['severity'].upper()}] {issue['detail']}")
    else:
        print("\n  No issues detected.")

    print()
