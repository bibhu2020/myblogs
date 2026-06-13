"""All function tools for the Meridian rebranding agent (OpenAI Agents SDK)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from agents import RunContextWrapper, function_tool
from openai import OpenAI


# ── Shared context object ─────────────────────────────────────────────────────

@dataclass
class RebrandCtx:
    """Mutable state shared across all tool calls within one agent run."""
    repo_root: str
    force_rebrand: bool = False
    # Populated by tools during the run
    chosen_theme: str = ""
    mood: str = "neutral"
    world_events: str = ""
    rebrand_plan: dict = field(default_factory=dict)
    files_changed: list = field(default_factory=list)
    patch_errors: list = field(default_factory=list)


# ── Module-level helpers (not tools) ─────────────────────────────────────────

def _web_search(client: OpenAI, prompt: str) -> str:
    """Responses API → gpt-4o-search-preview → gpt-4o plain fallback."""
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


def _run(args: list[str], cwd: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def _mask_token(text: str) -> str:
    return re.sub(r"github_pat_[A-Za-z0-9_]+", "***TOKEN***", text)


def _norm_hex(val: str) -> str:
    val = val.strip()
    return val if val.startswith("#") else f"#{val}"


def _replace_markers(content: str, start: str, end: str, inner: str) -> tuple[str, bool]:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(content):
        return content, False
    return pattern.sub(f"{start}\n{inner}\n{end}", content), True


# ── Planner system prompt (used by generate_rebrand_plan) ─────────────────────

_PLANNER_SYSTEM_PROMPT = """\
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


# ── Tools ─────────────────────────────────────────────────────────────────────

@function_tool
def check_schedule(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Check whether today qualifies for a rebrand run.

    Returns 'PROCEED' if today is the first Sunday of the month (day ≤ 07),
    or if the run was force-triggered by the operator.
    Returns 'SKIP: <reason>' if it should not run today.
    """
    if ctx.context.force_rebrand:
        print("[schedule] Force flag set — bypassing first-Sunday guard.")
        return "PROCEED (forced by operator — first-Sunday guard bypassed)"

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
    Returns a short summary string.
    """
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
        "- celebratory: a major holiday, festival, or global achievement dominates.\n"
        "- somber: a significant natural disaster, war, or tragedy with global impact dominates. "
        "  Be dignified and brief. Express sympathy without political bias.\n"
        "- neutral: nothing clearly dominant — use a tasteful seasonal theme.\n\n"
        "Return JSON only:\n"
        '{"chosen_theme": "one sentence", "mood": "celebratory|somber|neutral", '
        '"events_summary": "2-3 sentence summary"}'
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": classify_prompt}],
        response_format={"type": "json_object"},
    )
    extracted = json.loads(resp.choices[0].message.content or "{}")

    ctx.context.chosen_theme = extracted.get("chosen_theme", f"{month_year} seasonal theme")
    ctx.context.mood = extracted.get("mood", "neutral")
    if ctx.context.mood not in ("celebratory", "somber", "neutral"):
        ctx.context.mood = "neutral"
    ctx.context.world_events = extracted.get("events_summary", raw_events[:400])

    print(f"[research] Theme: {ctx.context.chosen_theme}")
    print(f"[research] Mood:  {ctx.context.mood}")
    return (
        f"Theme: {ctx.context.chosen_theme}\n"
        f"Mood:  {ctx.context.mood}\n"
        f"Events: {ctx.context.world_events}"
    )


@function_tool
def generate_rebrand_plan(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Generate the complete visual rebrand package — colour palette (10 shades),
    Layout B accent tokens, HTML banner/badge/footer snippets, holiday CSS block,
    and title emoji — based on the research results stored in context.

    Stores the full plan dict in context.
    Returns a brief confirmation or 'ERROR: <reason>' on failure.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    now = datetime.now(timezone.utc)
    month_year = now.strftime("%B %Y")

    user_prompt = (
        f"Month: {month_year}\n"
        f"Chosen theme: {ctx.context.chosen_theme}\n"
        f"Mood: {ctx.context.mood}\n"
        f"World events context: {ctx.context.world_events}\n\n"
        "Generate the complete rebrand package JSON following the schema in the system prompt."
    )

    print(f"[planner] Generating rebrand plan for '{ctx.context.chosen_theme}' ({ctx.context.mood})...")
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=4096,
    )

    try:
        plan = json.loads(resp.choices[0].message.content or "{}")
    except json.JSONDecodeError as exc:
        return f"ERROR: Planner returned invalid JSON: {exc}"

    required = {"palette_a", "lb_accent", "banner_a_html", "hero_a_html",
                "footer_html", "banner_b_html", "hero_b_html", "holiday_css"}
    missing = required - set(plan.keys())
    if missing:
        return f"ERROR: Plan missing keys: {missing}"

    expected_shades = {f"primary-{s}" for s in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)}
    if not expected_shades.issubset(plan.get("palette_a", {}).keys()):
        return f"ERROR: palette_a missing shades: {expected_shades - set(plan.get('palette_a', {}))}"

    ctx.context.rebrand_plan = plan
    p600 = plan["palette_a"].get("primary-600", "?")
    accent = plan.get("lb_accent", {}).get("lb-accent", "?")
    print(f"[planner] Plan ready. primary-600={p600}, lb-accent={accent}")
    return f"Plan generated successfully. primary-600={p600}, lb-accent={accent}"


@function_tool
def patch_frontend_files(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Apply the rebrand plan to all frontend source files:
    style.css (palette + accents + holiday CSS), Navbar.vue (banners),
    Home.vue (hero badges), Footer.vue, and frontend/index.html (title emoji).

    Returns a summary of changed files and any patch warnings.
    """
    plan = ctx.context.rebrand_plan
    if not plan:
        return "ERROR: No rebrand plan in context — call generate_rebrand_plan first."

    repo_root = ctx.context.repo_root
    frontend = Path(repo_root) / "frontend"
    files_changed: list[str] = []
    patch_errors: list[str] = []

    def read(rel: str) -> str:
        return (frontend / rel).read_text(encoding="utf-8")

    def write(rel: str, content: str) -> None:
        (frontend / rel).write_text(content, encoding="utf-8")
        if rel not in files_changed:
            files_changed.append(rel)

    def warn(msg: str) -> None:
        print(f"[patcher] WARNING: {msg}")
        patch_errors.append(msg)

    # ── style.css ────────────────────────────────────────────────────────────
    style = read("src/style.css")
    orig = style

    palette_a = plan.get("palette_a", {})
    for shade, raw_hex in palette_a.items():
        hex_val = _norm_hex(raw_hex)
        style = re.sub(
            r"(--color-" + re.escape(shade) + r":\s*)#[0-9a-fA-F]{3,8}",
            r"\g<1>" + hex_val, style,
        )

    lb = plan.get("lb_accent", {})
    var_map = {
        "lb-accent": "--color-lb-accent",
        "lb-accent-bg": "--color-lb-accent-bg",
        "lb-accent-bg-hover": "--color-lb-accent-hover",
        "lb-card-hover": "--color-lb-card-hover",
    }
    for key, css_var in var_map.items():
        if key in lb:
            style = re.sub(
                r"(" + re.escape(css_var) + r":\s*)#[0-9a-fA-F]{3,8}",
                r"\g<1>" + _norm_hex(lb[key]), style,
            )

    holiday_css = plan.get("holiday_css", "").strip()
    if holiday_css:
        style, ok = _replace_markers(style, "/* HOLIDAY-CSS-START */", "/* HOLIDAY-CSS-END */", holiday_css)
        if not ok:
            warn("style.css: HOLIDAY-CSS markers not found — appending block")
            style += f"\n/* HOLIDAY-CSS-START */\n{holiday_css}\n/* HOLIDAY-CSS-END */\n"

    if style != orig:
        write("src/style.css", style)
        print("[patcher] style.css updated")

    # ── Navbar.vue ────────────────────────────────────────────────────────────
    nav = read("src/components/Navbar.vue")
    orig = nav
    for marker_start, marker_end, key in [
        ("<!-- HOLIDAY-BANNER-START -->",   "<!-- HOLIDAY-BANNER-END -->",   "banner_a_html"),
        ("<!-- HOLIDAY-BANNER-B-START -->", "<!-- HOLIDAY-BANNER-B-END -->", "banner_b_html"),
    ]:
        if plan.get(key):
            nav, ok = _replace_markers(nav, marker_start, marker_end, plan[key])
            if not ok:
                warn(f"Navbar.vue: {marker_start} not found")
    if nav != orig:
        write("src/components/Navbar.vue", nav)
        print("[patcher] Navbar.vue updated")

    # ── Home.vue ──────────────────────────────────────────────────────────────
    home = read("src/views/Home.vue")
    orig = home
    for marker_start, marker_end, key in [
        ("<!-- HOLIDAY-HERO-START -->",   "<!-- HOLIDAY-HERO-END -->",   "hero_a_html"),
        ("<!-- HOLIDAY-HERO-B-START -->", "<!-- HOLIDAY-HERO-B-END -->", "hero_b_html"),
    ]:
        if plan.get(key):
            home, ok = _replace_markers(home, marker_start, marker_end, plan[key])
            if not ok:
                warn(f"Home.vue: {marker_start} not found")
    if home != orig:
        write("src/views/Home.vue", home)
        print("[patcher] Home.vue updated")

    # ── Footer.vue ────────────────────────────────────────────────────────────
    footer_src = read("src/components/Footer.vue")
    orig = footer_src
    if plan.get("footer_html"):
        footer_src, ok = _replace_markers(
            footer_src, "<!-- HOLIDAY-FOOTER-START -->", "<!-- HOLIDAY-FOOTER-END -->", plan["footer_html"]
        )
        if not ok:
            warn("Footer.vue: HOLIDAY-FOOTER markers not found")
    if footer_src != orig:
        write("src/components/Footer.vue", footer_src)
        print("[patcher] Footer.vue updated")

    # ── index.html — title emoji ──────────────────────────────────────────────
    html = read("index.html")
    orig = html
    base_title = "Meridian — Where Ideas Converge"
    emoji = plan.get("title_emoji", "").strip()
    new_title = f"{base_title} {emoji}".rstrip() if emoji else base_title
    html = re.sub(r"<title>Meridian[^<]*</title>", f"<title>{new_title}</title>", html)
    if html != orig:
        write("index.html", html)
        print(f"[patcher] index.html title → {new_title}")

    ctx.context.files_changed = files_changed
    ctx.context.patch_errors = patch_errors

    summary = f"Changed: {files_changed or ['(none)']}"
    if patch_errors:
        summary += f"\nWarnings: {patch_errors}"
    return summary


@function_tool
def verify_build(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Run `npm run build` in frontend/ to confirm all patched files compile successfully.

    Returns 'BUILD PASSED' or 'BUILD FAILED: <error excerpt>'.
    """
    repo_root = ctx.context.repo_root
    frontend_dir = str(Path(repo_root) / "frontend")
    print("[build] Running npm run build...")
    t0 = time.time()
    try:
        result = _run(["npm", "run", "build"], cwd=frontend_dir, timeout=300)
    except subprocess.TimeoutExpired:
        return "BUILD FAILED: timed out after 300s"

    elapsed = round(time.time() - t0, 1)
    output = (result.stdout or "")[-2000:]
    if result.stderr:
        output += "\n" + (result.stderr or "")[-1000:]

    if result.returncode == 0:
        print(f"[build] PASSED in {elapsed}s")
        return "BUILD PASSED"

    print(f"[build] FAILED in {elapsed}s")
    print(output[-600:])
    # Return enough context for the agent to report the error
    return f"BUILD FAILED: {output[-800:]}"


@function_tool
def revert_changes(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Discard all uncommitted file changes via `git checkout -- .`

    Call this only after a BUILD FAILED to restore the repo to a clean state.
    """
    repo_root = ctx.context.repo_root
    _run(["git", "checkout", "--", "."], cwd=repo_root)
    print("[revert] All changes reverted — repo restored to HEAD.")
    return "Reverted — repo is clean."


@function_tool
def commit_and_push(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Commit all rebrand file changes and push to origin/main.

    Call this only after BUILD PASSED.
    Returns a short status: commit SHA and push result, or an error description.
    """
    repo_root = ctx.context.repo_root
    chosen_theme = ctx.context.chosen_theme or "monthly theme"
    now = datetime.now(timezone.utc)
    month_year = now.strftime("%B %Y")
    commit_msg = f"rebrand: {chosen_theme} rebranding for {month_year}"

    def git(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
        return _run(["git", *args], cwd=repo_root, timeout=timeout)

    git("config", "user.name", "Claude Theme Bot")
    git("config", "user.email", "bm80177@gmail.com")

    pull = git("pull", "--rebase", "origin", "main", timeout=90)
    if pull.returncode != 0:
        print(f"[publish] git pull warning: {_mask_token(pull.stderr or pull.stdout)[:200]}")

    git("add", "-A")

    status = git("status", "--porcelain")
    if not status.stdout.strip():
        print("[publish] Working tree is clean — nothing to commit.")
        return "Nothing to commit — working tree already clean."

    commit = git("commit", "-m", commit_msg)
    if commit.returncode != 0:
        err = _mask_token(commit.stderr or commit.stdout)
        return f"ERROR: git commit failed: {err[:300]}"

    sha = git("rev-parse", "--short", "HEAD").stdout.strip()
    print(f"[publish] Committed {sha}: {commit_msg}")

    push = git("push", "origin", "main", timeout=90)
    if push.returncode == 0:
        print("[publish] Pushed to origin/main successfully.")
        return f"Pushed successfully. Commit: {sha}"

    err = _mask_token(push.stderr or push.stdout)[:400]
    print(f"[publish] Push failed: {err}")
    return f"Commit {sha} created but push failed: {err}"
