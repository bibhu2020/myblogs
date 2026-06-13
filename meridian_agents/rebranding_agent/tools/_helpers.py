"""Shared utilities and the planner system prompt used across tool modules."""
from __future__ import annotations

import re
import subprocess

from openai import OpenAI


# ── Process helpers ───────────────────────────────────────────────────────────

def run(args: list[str], cwd: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def mask_token(text: str) -> str:
    return re.sub(r"github_pat_[A-Za-z0-9_]+", "***TOKEN***", text)


def norm_hex(val: str) -> str:
    val = val.strip()
    return val if val.startswith("#") else f"#{val}"


def replace_markers(content: str, start: str, end: str, inner: str) -> tuple[str, bool]:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(content):
        return content, False
    return pattern.sub(f"{start}\n{inner}\n{end}", content), True


# ── WCAG colour contrast ──────────────────────────────────────────────────────

def relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(hex1: str, hex2: str) -> float:
    l1, l2 = relative_luminance(hex1), relative_luminance(hex2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ── OpenAI web search helper ──────────────────────────────────────────────────

def web_search(client: OpenAI, prompt: str) -> str:
    """Responses API with web_search_preview → chat fallback."""
    try:
        resp = client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )
        return resp.output_text or ""
    except Exception:
        pass
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""
    except Exception:
        pass
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Based on your knowledge: {prompt}"}],
    )
    return resp.choices[0].message.content or ""


# ── Planner system prompt ─────────────────────────────────────────────────────

PLANNER_SYSTEM_PROMPT = """\
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
  MUST include role="banner" aria-label="<theme> announcement" on the outer div.
  Celebratory: gradient OK — `<div role="banner" aria-label="..." class="bg-gradient-to-r \
from-primary-700 to-primary-600 text-white text-center text-sm py-1.5 font-medium">🎊 Msg</div>`
  Somber: `<div role="banner" aria-label="..." class="bg-primary-800 text-primary-200 \
text-center text-sm py-1.5">Respectful one-line message</div>` — NO emoji, no exclamation marks.
  Neutral: `<div role="banner" aria-label="..." class="bg-primary-700 text-white \
text-center text-sm py-1">Message</div>`

"hero_a_html": Single <div> for Layout A hero badge, class="holiday-badge".
  Format: `<div class="holiday-badge bg-primary-50 text-primary-800 border border-primary-200 \
rounded-full px-4 py-1 text-sm inline-block mb-4" aria-label="<short description>">Short tagline</div>`
  Somber: plain text, no emoji. Celebratory: one tasteful emoji OK.

"footer_html": Single <p> for Footer (shared by both layouts via :class binding).
  Format: `<p class="mb-2" :class="layout.variant === 'b' ? 'text-slate-500' : \
'text-primary-300'">Footer message</p>`
  Somber: brief, dignified, no emoji. Celebratory: one emoji OK.

"banner_b_html": Single <div> for Layout B navbar banner (dark theme).
  MUST include role="banner" aria-label="<theme> announcement" on the outer div.
  Use the lb-accent hex directly — NOT Tailwind classes for custom colors.
  Format: `<div role="banner" aria-label="..." class="bg-[#0d0d1a] border-b \
border-[{lb-accent}]/20 text-[{lb-accent}] text-center text-sm py-1.5">Message</div>`
  Somber: subdued `bg-[#0a0a14]` with `text-slate-500`, no emoji.

"hero_b_html": Single <div> for Layout B hero badge, class="holiday-badge-b".
  Format: `<div class="holiday-badge-b bg-[#13132a] border border-[{lb-accent}]/30 \
text-[{lb-accent}] rounded-full px-4 py-1 text-sm inline-block mb-4" \
aria-label="<short description>">Short tagline</div>`

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
• SEO: every banner/badge must include descriptive aria-label attributes.
• ADA: colour contrast primary-600..900 on white must be ≥4.5:1 (WCAG AA).
"""
