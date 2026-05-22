"""
Email Formatter
Takes the curated briefing JSON and renders it as HTML email.
"""

from datetime import datetime
from urllib.parse import quote
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

REPO = "griffinmacnaughtan/newsletter"

# Each feedback type maps to a structured issue the auto-fix agent can parse.
# The body includes machine-readable metadata so the scheduled agent knows
# exactly what to investigate and which files to touch.
FEEDBACK_TYPES = {
    "missing_stories": {
        "label": "Missing stories",
        "title_tag": "missing-stories",
        "suggested_action": "Check feed list in config.yaml for gaps in coverage. "
                            "Consider adding sources for under-represented topics.",
        "files_hint": "config.yaml",
    },
    "wrong_section": {
        "label": "Wrong section",
        "title_tag": "wrong-section",
        "suggested_action": "Review section placement rules in curator/prompt.py. "
                            "Tighten category definitions so items land correctly.",
        "files_hint": "curator/prompt.py",
    },
    "too_much_one_source": {
        "label": "Too much of one source",
        "title_tag": "source-concentration",
        "suggested_action": "Check source diversity rules in curator/prompt.py. "
                            "May need to add competing sources in config.yaml or "
                            "lower the concentration threshold.",
        "files_hint": "config.yaml, curator/prompt.py",
    },
    "tone": {
        "label": "Language not neutral",
        "title_tag": "tone-violation",
        "suggested_action": "Review banned verbs/adjectives lists in curator/prompt.py. "
                            "Add any new offending words to the ban lists.",
        "files_hint": "curator/prompt.py",
    },
    "weak_section": {
        "label": "Section too thin",
        "title_tag": "thin-section",
        "suggested_action": "Add more RSS feeds for the weak category in config.yaml. "
                            "Check if existing feeds for that category are returning items.",
        "files_hint": "config.yaml",
    },
    "great": {
        "label": "No notes, great edition",
        "title_tag": "great-edition",
        "suggested_action": "No action needed. Log as positive signal.",
        "files_hint": "",
    },
}


def make_feedback_url(date: str, feedback_key: str) -> str:
    """
    Generate a GitHub Issue URL for a specific feedback type.
    Body includes structured metadata the auto-fix agent can parse.
    """
    fb = FEEDBACK_TYPES[feedback_key]
    title = quote(f"[feedback] {fb['title_tag']} ({date})")
    body_lines = [
        f"## Feedback: {fb['label']}",
        f"**Date:** {date}",
        f"**Type:** `{feedback_key}`",
        "",
        "---",
        "",
        "### Agent Metadata",
        f"- **suggested_action:** {fb['suggested_action']}",
        f"- **files_hint:** {fb['files_hint']}",
        "",
        "---",
        "",
        "_Optional: add details below (e.g. which story was misplaced, "
        "which source dominated, what was missing)_",
        "",
    ]
    body = quote("\n".join(body_lines))
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
        fb_missing_stories=make_feedback_url(date_str, "missing_stories"),
        fb_wrong_section=make_feedback_url(date_str, "wrong_section"),
        fb_too_much_cbc=make_feedback_url(date_str, "too_much_one_source"),
        fb_tone=make_feedback_url(date_str, "tone"),
        fb_weak_section=make_feedback_url(date_str, "weak_section"),
        fb_great=make_feedback_url(date_str, "great"),
    )

    return html
