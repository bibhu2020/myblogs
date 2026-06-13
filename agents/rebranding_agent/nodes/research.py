"""Step 1: Research world events via web search and classify the monthly mood."""
import json
import os
from datetime import datetime, timezone

from openai import OpenAI

from ..state import RebrandState

_SEARCH_MODEL = "gpt-4o-search-preview"
_CHAT_MODEL = "gpt-4o"


def _web_search(client: OpenAI, prompt: str) -> str:
    """Try Responses API → gpt-4o-search-preview → gpt-4o fallback."""
    # 1. OpenAI Responses API with built-in web search
    try:
        resp = client.responses.create(
            model=_CHAT_MODEL,
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )
        return resp.output_text or ""
    except Exception:
        pass

    # 2. gpt-4o-search-preview via chat completions
    try:
        resp = client.chat.completions.create(
            model=_SEARCH_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""
    except Exception:
        pass

    # 3. Plain gpt-4o — knowledge only, no live web
    resp = client.chat.completions.create(
        model=_CHAT_MODEL,
        messages=[{"role": "user", "content": f"Based on your knowledge: {prompt}"}],
    )
    return resp.choices[0].message.content or ""


def research_mood_node(state: RebrandState) -> dict:
    """Search the web for major world events and determine the month's dominant theme and mood."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    now = datetime.now(timezone.utc)
    month_year = now.strftime("%B %Y")

    search_prompt = (
        f"It is {month_year}. Search the web and identify the most significant world events "
        "from the past month and the coming week: holidays, festivals, cultural celebrations, "
        "major sports events — but also natural disasters, wars, accidents, or tragedies with "
        "global significance. List the top 5 events you find."
    )
    print("[research] Searching for world events...")
    raw_events = _web_search(client, search_prompt)

    classify_prompt = (
        f"Based on these world events from {month_year}:\n\n{raw_events}\n\n"
        "Choose ONE dominant theme for this month and classify the overall mood.\n\n"
        "Rules:\n"
        "- Celebratory: a major holiday, festival, or global achievement dominates.\n"
        "- Somber: a significant natural disaster, war, or tragedy with global impact dominates. "
        "  Be dignified and brief. Express sympathy for affected civilians without political bias.\n"
        "- Neutral: nothing clearly dominant — use a tasteful seasonal theme.\n\n"
        "Return JSON only:\n"
        '{"chosen_theme": "one sentence", "mood": "celebratory|somber|neutral", '
        '"events_summary": "2-3 sentence summary of what you found and why this theme was chosen"}'
    )
    classify_resp = client.chat.completions.create(
        model=_CHAT_MODEL,
        messages=[{"role": "user", "content": classify_prompt}],
        response_format={"type": "json_object"},
    )
    try:
        extracted = json.loads(classify_resp.choices[0].message.content or "{}")
    except json.JSONDecodeError:
        extracted = {}

    chosen_theme = extracted.get("chosen_theme", f"{month_year} seasonal theme")
    mood = extracted.get("mood", "neutral")
    if mood not in ("celebratory", "somber", "neutral"):
        mood = "neutral"
    events_summary = extracted.get("events_summary", raw_events[:400])

    print(f"[research] Theme: {chosen_theme}")
    print(f"[research] Mood:  {mood}")

    return {
        "world_events": events_summary,
        "chosen_theme": chosen_theme,
        "mood": mood,
    }
