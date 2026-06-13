"""IdeationAgent tools: schedule guard and world-event research."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

from agents import RunContextWrapper, function_tool
from openai import OpenAI

from ..context import RebrandCtx
from ._helpers import web_search


@function_tool
def check_schedule(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Check whether today qualifies for a rebrand run.

    Returns 'PROCEED' if today is the first Sunday of the month (day ≤ 07),
    or if the run was force-triggered by the operator.
    Returns 'SKIP: <reason>' otherwise — the pipeline must stop immediately.
    """
    if ctx.context.force_rebrand:
        print("[schedule] Force flag set — bypassing first-Sunday guard.")
        return "PROCEED (forced by operator)"

    try:
        result = subprocess.run(["date", "+%d"], capture_output=True, text=True, check=True)
        day = int(result.stdout.strip())
    except Exception:
        day = datetime.now(timezone.utc).day

    if day > 7:
        msg = f"SKIP: Not the first Sunday — day {day:02d} is after day 07."
        print(f"[schedule] {msg}")
        return msg

    msg = f"PROCEED — first Sunday confirmed (day {day:02d})."
    print(f"[schedule] {msg}")
    return msg


@function_tool
def research_world_events(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Search the web for major world events from the past month and classify the
    dominant theme and mood (celebratory | somber | neutral) for this month's rebrand.

    Stores chosen_theme, mood, and world_events in context.
    Returns a short summary string for the IdeationAgent to pass to the planner.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    now = datetime.now(timezone.utc)
    month_year = now.strftime("%B %Y")

    print("[research] Searching for world events...")
    raw = web_search(client, (
        f"It is {month_year}. Search the web and identify the most significant world events "
        "from the past month and the coming week: holidays, festivals, cultural celebrations, "
        "major sports events — but also natural disasters, wars, accidents, or tragedies with "
        "global significance. List the top 5 events you find."
    ))

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": (
            f"Based on these world events from {month_year}:\n\n{raw}\n\n"
            "Choose ONE dominant theme for this month and classify the overall mood.\n\n"
            "Rules:\n"
            "- celebratory: a major holiday, festival, or global achievement dominates.\n"
            "- somber: a significant natural disaster, war, or tragedy with global impact dominates.\n"
            "- neutral: nothing clearly dominant — use a tasteful seasonal theme.\n\n"
            "Return JSON only:\n"
            '{"chosen_theme": "one sentence", "mood": "celebratory|somber|neutral", '
            '"events_summary": "2-3 sentence summary"}'
        )}],
        response_format={"type": "json_object"},
    )
    extracted = json.loads(resp.choices[0].message.content or "{}")

    ctx.context.chosen_theme = extracted.get("chosen_theme", f"{month_year} seasonal theme")
    ctx.context.mood = extracted.get("mood", "neutral")
    if ctx.context.mood not in ("celebratory", "somber", "neutral"):
        ctx.context.mood = "neutral"
    ctx.context.world_events = extracted.get("events_summary", raw[:400])

    print(f"[research] Theme: {ctx.context.chosen_theme}")
    print(f"[research] Mood:  {ctx.context.mood}")
    return (
        f"Theme: {ctx.context.chosen_theme}\n"
        f"Mood:  {ctx.context.mood}\n"
        f"Events: {ctx.context.world_events}"
    )
