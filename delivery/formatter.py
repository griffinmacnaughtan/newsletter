"""
Email Formatter
Takes the curated briefing JSON and renders it as HTML email.
"""

from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


def format_email(briefing: dict) -> str:
    """
    Render the curated briefing as an HTML email.
    Returns the HTML string.
    """
    template_dir = Path(__file__).parent
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("template.html")

    # Parse date for formatted display
    date_str = briefing.get("date", datetime.now().strftime("%Y-%m-%d"))
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date_formatted = date_obj.strftime("%A, %B %d, %Y")
    except (ValueError, TypeError):
        date_formatted = date_str

    html = template.render(
        date=date_str,
        date_formatted=date_formatted,
        lead_stories=briefing.get("lead_stories", []),
        tech_ai=briefing.get("tech_ai", []),
        sports=briefing.get("sports", []),
        canada=briefing.get("canada", []),
        world=briefing.get("world", []),
        environment=briefing.get("environment", []),
        culture=briefing.get("culture", []),
        radar=briefing.get("radar", []),
    )

    return html


if __name__ == "__main__":
    # Test with sample data
    sample_briefing = {
        "date": "2026-05-22",
        "lead_stories": [
            {
                "headline": "Bank of Canada holds rate at 3.25%",
                "summary": "The central bank maintained its overnight rate, citing stable inflation at 2.1%. [Canadian Press]",
                "source": "Canadian Press",
                "url": "https://example.com",
            }
        ],
        "tech_ai": [
            {
                "headline": "Anthropic releases Claude 4.5 Opus",
                "summary": "New model benchmarks 12% improvement on coding tasks. Available via API immediately. [Reuters Technology]",
                "source": "Reuters",
                "url": "https://example.com",
            }
        ],
        "sports": [],
        "canada": [],
        "world": [],
        "environment": [],
        "culture": [],
        "radar": [
            {"headline": "TTC announces weekend Line 2 closure for maintenance", "source": "CBC Toronto", "url": "https://example.com"},
        ],
    }

    html = format_email(sample_briefing)
    # Write test output
    with open(template_dir / "test_output.html", "w") as f:
        f.write(html)
    print("Test email written to delivery/test_output.html")
