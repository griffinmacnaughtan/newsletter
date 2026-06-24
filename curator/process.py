"""
Curator Processor
Sends raw items to Claude for intelligent curation and structuring.
Includes retry logic for malformed JSON and truncation.
"""

import json
import re
from datetime import datetime
from anthropic import Anthropic, APIError
from .prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

MAX_RETRIES = 3
SECTIONS = ["lead_stories", "tech_ai", "sports", "canada", "world", "environment", "culture", "radar"]


def _validate_urls(briefing: dict) -> dict:
    """Drop items with empty or invalid URLs so every headline is clickable."""
    dropped = 0
    for section in SECTIONS:
        items = briefing.get(section, [])
        valid = []
        for item in items:
            url = (item.get("url") or "").strip()
            if url and url.startswith("http"):
                valid.append(item)
            else:
                dropped += 1
        briefing[section] = valid
    if dropped:
        print(f"  [URL] Dropped {dropped} items with missing/invalid URLs")
    return briefing


def _extract_json(text: str) -> str:
    """Extract JSON from Claude's response, handling code fences and preamble."""
    # Strip ```json ... ``` blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    # Find the outermost { ... } in case Claude added preamble/postamble
    match = re.search(r"\{", text)
    if match:
        depth = 0
        start = match.start()
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

    return text.strip()


def _count_items(briefing: dict) -> int:
    """Count total curated items across all sections."""
    return sum(len(briefing.get(s, [])) for s in SECTIONS)


def curate_items(raw_items: list[dict], date: str = None) -> dict:
    """
    Send raw news items to Claude for curation.
    Retries up to MAX_RETRIES times on malformed JSON or truncation.
    Returns structured briefing as a dict, or None if all retries fail.
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

    client = Anthropic()

    for attempt in range(1, MAX_RETRIES + 1):
        # Scale up token limit on retries
        max_tokens = 8192 if attempt == 1 else 16384

        print(f"  [Attempt {attempt}/{MAX_RETRIES}] Calling Claude (max_tokens={max_tokens})...")

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            )
        except APIError as e:
            print(f"  [ERROR] Anthropic API error on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                print("  Retrying...")
                continue
            else:
                print(f"  [FATAL] API error after {MAX_RETRIES} attempts.")
                return None

        # Check truncation
        if response.stop_reason == "max_tokens":
            print(f"  [WARN] Response truncated at {max_tokens} tokens.")
            if attempt < MAX_RETRIES:
                print("  Retrying with higher limit...")
                continue
            else:
                print("  [ERROR] Still truncated after max retries.")
                return None

        # Extract and parse JSON
        response_text = response.content[0].text
        json_text = _extract_json(response_text)

        try:
            briefing = json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"  [WARN] JSON parse error on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                print("  Retrying...")
                continue
            else:
                print(f"  [ERROR] Failed to parse after {MAX_RETRIES} attempts.")
                print(f"  [DEBUG] Last response (first 500 chars): {response_text[:500]}")
                return None

        # Validate the briefing has actual content
        total = _count_items(briefing)
        if total == 0:
            print(f"  [WARN] Parsed OK but 0 items on attempt {attempt}.")
            if attempt < MAX_RETRIES:
                print("  Retrying...")
                continue
            else:
                print("  [ERROR] All attempts produced empty briefings.")
                return None

        briefing = _validate_urls(briefing)
        total = _count_items(briefing)
        print(f"  Curated down to {total} items across all sections")
        return briefing

    return None


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
