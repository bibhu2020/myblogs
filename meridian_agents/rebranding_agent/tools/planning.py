"""IdeationAgent tools: generate and revise the visual rebrand plan."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from agents import RunContextWrapper, function_tool
from openai import OpenAI

from ..context import RebrandCtx
from ._helpers import PLANNER_SYSTEM_PROMPT


@function_tool
def generate_rebrand_plan(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Generate the complete visual rebrand package for both Layout A and Layout B:
    colour palette (10 shades), accent tokens, HTML banners/badges/footer,
    holiday CSS (including :focus-visible), and title emoji.

    Requires research_world_events to have run first.
    Stores the full plan dict in context and returns a brief confirmation.
    """
    if not ctx.context.chosen_theme:
        return "ERROR: No theme in context — call research_world_events before generate_rebrand_plan."

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    now = datetime.now(timezone.utc)
    month_year = now.strftime("%B %Y")

    print(f"[ideation] Generating rebrand plan for '{ctx.context.chosen_theme}' ({ctx.context.mood})...")
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Month: {month_year}\n"
                f"Chosen theme: {ctx.context.chosen_theme}\n"
                f"Mood: {ctx.context.mood}\n"
                f"World events context: {ctx.context.world_events}\n\n"
                "Generate the complete rebrand package JSON following the schema in the system prompt."
            )},
        ],
        response_format={"type": "json_object"},
        max_tokens=4096,
    )

    try:
        plan = json.loads(resp.choices[0].message.content or "{}")
    except json.JSONDecodeError as exc:
        return f"ERROR: Planner returned invalid JSON: {exc}"

    required = {
        "palette_a", "lb_accent", "banner_a_html", "hero_a_html",
        "footer_html", "banner_b_html", "hero_b_html", "holiday_css",
    }
    missing = required - set(plan.keys())
    if missing:
        return f"ERROR: Plan missing required keys: {sorted(missing)}"

    expected_shades = {f"primary-{s}" for s in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)}
    if not expected_shades.issubset(plan.get("palette_a", {}).keys()):
        return f"ERROR: palette_a missing shades: {sorted(expected_shades - set(plan.get('palette_a', {})))}"

    ctx.context.rebrand_plan = plan
    p600 = plan["palette_a"].get("primary-600", "?")
    accent = plan.get("lb_accent", {}).get("lb-accent", "?")
    print(f"[ideation] Plan ready. primary-600={p600}, lb-accent={accent}")
    return (
        f"Plan generated. Theme: {ctx.context.chosen_theme} | Mood: {ctx.context.mood}\n"
        f"primary-600={p600}, lb-accent={accent}\n"
        f"Proceed to CodingAgent for implementation."
    )


@function_tool
def revise_rebrand_plan(ctx: RunContextWrapper[RebrandCtx], feedback: str) -> str:
    """Revise the current rebrand plan based on review feedback.

    Called when ReviewerAgent sends back specific issues with the plan
    (e.g., insufficient colour contrast, wrong tone for the mood).
    Increments revision counter — returns ERROR if cycles exceed 3.
    """
    ctx.context.review_cycles += 1
    if ctx.context.review_cycles > 3:
        return (
            "ERROR: Maximum revision cycles (3) exceeded. "
            "The plan could not be made compliant automatically — escalate to human review."
        )

    if not ctx.context.rebrand_plan:
        return "ERROR: No existing plan to revise — call generate_rebrand_plan first."

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    print(f"[ideation] Revising plan (cycle {ctx.context.review_cycles}/3) — feedback: {feedback[:120]}…")

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": (
                "The previous rebrand plan was reviewed and had these issues:\n\n"
                f"{feedback}\n\n"
                "Current plan (fix only the issues above — keep everything else):\n\n"
                f"{json.dumps(ctx.context.rebrand_plan, indent=2)}\n\n"
                "Return the corrected complete plan JSON."
            )},
        ],
        response_format={"type": "json_object"},
        max_tokens=4096,
    )

    try:
        plan = json.loads(resp.choices[0].message.content or "{}")
    except json.JSONDecodeError as exc:
        return f"ERROR: Revised plan invalid JSON: {exc}"

    ctx.context.rebrand_plan = plan
    ctx.context.review_feedback = ""
    p600 = plan.get("palette_a", {}).get("primary-600", "?")
    print(f"[ideation] Plan revised. primary-600={p600}")
    return (
        f"Plan revised (cycle {ctx.context.review_cycles}/3). primary-600={p600}\n"
        "Proceed to CodingAgent to apply the updated plan."
    )
