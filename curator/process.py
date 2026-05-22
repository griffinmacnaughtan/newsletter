"""
Curator Processor
Sends raw items to Claude for intelligent curation and structuring.
"""

import json
from datetime import datetime
from anthropic import Anthropic
from .prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


def curate_items(raw_items: list[dict], date: str = None) -> dict:
    """
    Send raw news items to Claude for curation.
    Returns structured briefing as a dict.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    # Prepare items for the prompt - strip unnecessary fields to save tokens
    slim_items = []
    for item in raw_items:
        slim_items.append({
            "title": item.get("title", ""),
            "description": item.get("description", "")[:300],
            "url": item.get("url", ""),
            "source": item.get("source_name", ""),
            "published": item.get("published", ""),
            "categories": item.get("categories", []),
            "tier": item.get("tier", 2),
            "score": item.get("score", None),
        })

    items_json = json.dumps(slim_items, indent=None, default=str)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        count=len(slim_items),
        date=date,
        items_json=items_json,
    )

    # Call Claude
    client = Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
    )

    # Check if response was truncated
    if response.stop_reason == "max_tokens":
        print("[WARN] Claude response hit token limit, retrying with higher limit...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16384,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
        )

    # Extract JSON from response
    response_text = response.content[0].text

    # Try to parse JSON (Claude may wrap in ```json blocks)
    json_text = response_text
    if "```json" in json_text:
        json_text = json_text.split("```json")[1].split("```")[0]
    elif "```" in json_text:
        json_text = json_text.split("```")[1].split("```")[0]

    try:
        briefing = json.loads(json_text.strip())
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse Claude response as JSON: {e}")
        print(f"[DEBUG] Response text: {response_text[:500]}")
        # Return empty structure as fallback
        briefing = {
            "date": date,
            "lead_stories": [],
            "tech_ai": [],
            "sports": [],
            "canada": [],
            "world": [],
            "environment": [],
            "culture": [],
            "radar": [],
            "error": "Failed to parse curation response",
        }

    return briefing


if __name__ == "__main__":
    # Test with sample data
    sample = [
        {
            "title": "Bank of Canada holds interest rate at 3.25%",
            "description": "The Bank of Canada held its key interest rate steady.",
            "url": "https://example.com",
            "source_name": "Canadian Press",
            "published": "2026-05-22T08:00:00",
            "categories": ["canadian_politics"],
            "tier": 1,
        }
    ]
    result = curate_items(sample)
    print(json.dumps(result, indent=2))
