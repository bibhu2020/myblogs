"""Steps 3-4: Generate the complete rebrand plan — palette, accents, and messaging."""
import json
import os
from datetime import datetime, timezone

from openai import OpenAI

from ..state import RebrandState

_MODEL = "gpt-4o"

_SYSTEM_PROMPT = """\
You are the Meridian website rebrand planner. Given a world theme and mood, generate a \
complete monthly rebrand package as a single JSON object.

Meridian is a blogging platform with two layouts:
  Layout A — light theme. Uses Tailwind CSS v4 `primary-*` color tokens (primary-50…primary-900).
  Layout B — dark near-black background (#080810) with custom accent colors.

─── JSON SCHEMA (return exactly these keys) ───────────────────────────────────────

"palette_a": {
  "primary-50" through "primary-900": 10 six-digit hex values (#rrggbb).
  • primary-50..300: light tints (backgrounds, hero badges, light text on colored buttons).
  • primary-400..500: mid-tones (hover states, accents).
  • primary-600..900: dark shades used for navbars, buttons, footer, dark text.
  • WCAG AA requirement: primary-600 through primary-900 must give ≥4.5:1 contrast with
    white (#ffffff). This means relative luminance ≤ 0.178.
    (L = 0.2126·R_lin + 0.7152·G_lin + 0.0722·B_lin where X_lin = (X/255)^2.2 approx)
    To be safe: keep primary-600..900 luminance values under 0.15 (very dark shades).
  • primary-900 is the footer background; primary-200 is the footer text — ensure ≥4.5:1.
  Mood guidance:
    celebratory → vibrant palette fitting the event (warm golds, festive reds, tropical teals…)
    somber      → muted, desaturated palette (soft grays, desaturated blues, subdued earthy tones)
    neutral     → tasteful seasonal tones (cool indigos, slate-blues, soft greens…)
}

"lb_accent": {
  "lb-accent":         vivid hex — text/icon color readable on #0f0f1e dark bg.
  "lb-accent-bg":      button background; must contrast ≥4.5:1 with white.
  "lb-accent-bg-hover": slightly darker than lb-accent-bg (darken by ~10%).
  "lb-card-hover":     very dark tint of accent hue (card border on dark bg, e.g. #0d1020).
  somber  → muted steel-blue/slate family (e.g., #7090b0, #3a5270, #2a3f5c, #0d1a2a).
  neutral → cool indigo or slate-blue family.
}

"banner_a_html": Single <div> for Layout A navbar banner strip. Use primary-* Tailwind classes.
  Celebratory: gradient OK — `<div class="bg-gradient-to-r from-primary-700 to-primary-600 \
text-white text-center text-sm py-1.5 font-medium">🎊 Message</div>`
  Somber: `<div class="bg-primary-800 text-primary-200 text-center text-sm py-1.5">\
Respectful one-line message</div>` — NO emoji, no exclamation marks.
  Neutral: `<div class="bg-primary-700 text-white text-center text-sm py-1">Message</div>`

"hero_a_html": Single <div> for Layout A hero badge, class="holiday-badge".
  Format: `<div class="holiday-badge bg-primary-50 text-primary-800 border border-primary-200 \
rounded-full px-4 py-1 text-sm inline-block mb-4">Short tagline</div>`
  Somber: plain text, no emoji. Celebratory: one tasteful emoji OK.

"footer_html": Single <p> for Footer (shared by both layouts via :class binding).
  Format: `<p class="mb-2" :class="layout.variant === 'b' ? 'text-slate-500' : \
'text-primary-300'">Footer message</p>`
  Somber: brief, dignified, no emoji. Celebratory: one emoji OK.

"banner_b_html": Single <div> for Layout B navbar banner (dark theme).
  Use the lb-accent hex directly — NOT Tailwind classes for custom colors.
  Format: `<div class="bg-[#0d0d1a] border-b border-[{lb-accent}]/20 text-[{lb-accent}] \
text-center text-sm py-1.5">Message</div>`
  Somber: subdued `bg-[#0a0a14]` with `text-slate-500`, no emoji.

"hero_b_html": Single <div> for Layout B hero badge, class="holiday-badge-b".
  Format: `<div class="holiday-badge-b bg-[#13132a] border border-[{lb-accent}]/30 \
text-[{lb-accent}] rounded-full px-4 py-1 text-sm inline-block mb-4">Short tagline</div>`

"holiday_css": CSS string for the HOLIDAY-CSS block.
  MUST always include the :focus-visible rule:
    `:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }`
  Celebratory: add subtle bg tint for Layout A + glow on badges:
    `[data-layout="a"] body, [data-layout="a"] #app { background-color: {primary-50}; }`
    `.holiday-badge { box-shadow: 0 0 12px {primary-200}80; }`
    `.holiday-badge-b { box-shadow: 0 0 12px {lb-accent}40; }`
  Somber/Neutral: only the :focus-visible rule (no decorative additions).

"title_emoji": Emoji string appended to `<title>Meridian — Where Ideas Converge`.
  Celebratory only (e.g., "🎄" or "⚽"). Somber: "" (empty string). Neutral: "".

─── CONTENT RULES ──────────────────────────────────────────────────────────────
• Site name "Meridian" never changes.
• All messages: tasteful, one line, appropriate to the mood.
• Somber: dignified and brief. No political blame. "Our thoughts are with the people of <place>."
• Celebratory: festive but not loud. Max one emoji per message slot.
• All HTML must be valid Vue template syntax (properly quoted attributes, no unclosed tags).
"""


def generate_plan_node(state: RebrandState) -> dict:
    """Call GPT-4o with JSON mode to generate the full rebrand plan."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    now = datetime.now(timezone.utc)
    month_year = now.strftime("%B %Y")

    chosen_theme = state.get("chosen_theme", f"{month_year} seasonal theme")
    mood = state.get("mood", "neutral")
    world_events = state.get("world_events", "")

    user_prompt = (
        f"Month: {month_year}\n"
        f"Chosen theme: {chosen_theme}\n"
        f"Mood: {mood}\n"
        f"World events context: {world_events}\n\n"
        "Generate the complete rebrand package JSON following the schema in the system prompt."
    )

    print(f"[planner] Generating rebrand plan for '{chosen_theme}' ({mood})...")
    resp = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=4096,
    )

    try:
        plan = json.loads(resp.choices[0].message.content or "{}")
    except json.JSONDecodeError as exc:
        return {"error": f"Planner returned invalid JSON: {exc}"}

    # Validate required keys
    required = {"palette_a", "lb_accent", "banner_a_html", "hero_a_html",
                "footer_html", "banner_b_html", "hero_b_html", "holiday_css"}
    missing = required - set(plan.keys())
    if missing:
        return {"error": f"Planner plan missing keys: {missing}"}

    # Ensure palette_a has all 10 shades
    expected_shades = {f"primary-{s}" for s in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)}
    if not expected_shades.issubset(plan.get("palette_a", {}).keys()):
        return {"error": f"palette_a missing shades: {expected_shades - set(plan.get('palette_a', {}))}"}

    print(f"[planner] Plan generated. palette_a[primary-700]={plan['palette_a'].get('primary-700')}, "
          f"lb-accent={plan.get('lb_accent', {}).get('lb-accent')}")
    return {"rebrand_plan": plan}
