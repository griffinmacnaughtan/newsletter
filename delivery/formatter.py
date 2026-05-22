"""
Email Formatter
Takes the curated briefing JSON and renders it as HTML email.
"""

from datetime import datetime
from urllib.parse import quote
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

REPO = "griffinmacnaughtan/newsletter"


def make_feedback_url(date: str, rating: str) -> str:
    """Generate a GitHub Issue URL pre-filled with feedback."""
    title = quote(f"Feedback {date}: {rating}")
    body = quote(f"Rating: {rating}\nDate: {date}\n\n_Optional: add notes here_")
    return f"https://github.com/{REPO}/issues/new?title={title}&body={body}&labels=feedback"


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
        feedback_url_great=make_feedback_url(date_str, "great"),
        feedback_url_good=make_feedback_url(date_str, "good"),
        feedback_url_fix=make_feedback_url(date_str, "needs-work"),
    )

    return html
