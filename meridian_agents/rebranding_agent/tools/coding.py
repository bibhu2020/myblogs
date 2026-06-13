"""CodingAgent tools: apply and patch frontend files."""
from __future__ import annotations

import re
from pathlib import Path

from agents import RunContextWrapper, function_tool

from ..context import RebrandCtx
from ._helpers import norm_hex, replace_markers


# Allowed filenames the CodingAgent can read/write (relative to frontend/)
_ALLOWED = {
    "src/style.css",
    "src/components/Navbar.vue",
    "src/views/Home.vue",
    "src/components/Footer.vue",
    "index.html",
}


def _frontend(ctx: RunContextWrapper[RebrandCtx]) -> Path:
    return Path(ctx.context.repo_root) / "frontend"


@function_tool
def patch_frontend_files(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Apply the rebrand plan to all five frontend source files:
    style.css  — palette tokens + Layout B accent tokens + holiday CSS block
    Navbar.vue — Layout A and Layout B banner strips (HOLIDAY-BANNER markers)
    Home.vue   — Layout A and Layout B hero badges (HOLIDAY-HERO markers)
    Footer.vue — shared footer message (HOLIDAY-FOOTER marker)
    index.html — page title emoji

    Requires generate_rebrand_plan to have run first.
    Returns a summary of changed files and any patch warnings.
    """
    plan = ctx.context.rebrand_plan
    if not plan:
        return "ERROR: No rebrand plan in context — IdeationAgent must run first."

    frontend = _frontend(ctx)
    files_changed: list[str] = []
    patch_errors: list[str] = []

    def read(rel: str) -> str:
        return (frontend / rel).read_text(encoding="utf-8")

    def write(rel: str, content: str) -> None:
        (frontend / rel).write_text(content, encoding="utf-8")
        if rel not in files_changed:
            files_changed.append(rel)

    def warn(msg: str) -> None:
        print(f"[coding] WARNING: {msg}")
        patch_errors.append(msg)

    # ── style.css ─────────────────────────────────────────────────────────────
    style = read("src/style.css")
    orig = style
    for shade, raw_hex in plan.get("palette_a", {}).items():
        hex_val = norm_hex(raw_hex)
        style = re.sub(
            r"(--color-" + re.escape(shade) + r":\s*)#[0-9a-fA-F]{3,8}",
            r"\g<1>" + hex_val, style,
        )
    var_map = {
        "lb-accent":          "--color-lb-accent",
        "lb-accent-bg":       "--color-lb-accent-bg",
        "lb-accent-bg-hover": "--color-lb-accent-hover",
        "lb-card-hover":      "--color-lb-card-hover",
    }
    for key, css_var in var_map.items():
        if key in plan.get("lb_accent", {}):
            style = re.sub(
                r"(" + re.escape(css_var) + r":\s*)#[0-9a-fA-F]{3,8}",
                r"\g<1>" + norm_hex(plan["lb_accent"][key]), style,
            )
    holiday_css = plan.get("holiday_css", "").strip()
    if holiday_css:
        style, ok = replace_markers(style, "/* HOLIDAY-CSS-START */", "/* HOLIDAY-CSS-END */", holiday_css)
        if not ok:
            warn("style.css: HOLIDAY-CSS markers not found — appending block")
            style += f"\n/* HOLIDAY-CSS-START */\n{holiday_css}\n/* HOLIDAY-CSS-END */\n"
    if style != orig:
        write("src/style.css", style)
        print("[coding] style.css updated")

    # ── Navbar.vue ────────────────────────────────────────────────────────────
    nav = read("src/components/Navbar.vue")
    orig = nav
    for start, end, key in [
        ("<!-- HOLIDAY-BANNER-START -->",   "<!-- HOLIDAY-BANNER-END -->",   "banner_a_html"),
        ("<!-- HOLIDAY-BANNER-B-START -->", "<!-- HOLIDAY-BANNER-B-END -->", "banner_b_html"),
    ]:
        if plan.get(key):
            nav, ok = replace_markers(nav, start, end, plan[key])
            if not ok:
                warn(f"Navbar.vue: {start} not found")
    if nav != orig:
        write("src/components/Navbar.vue", nav)
        print("[coding] Navbar.vue updated")

    # ── Home.vue ──────────────────────────────────────────────────────────────
    home = read("src/views/Home.vue")
    orig = home
    for start, end, key in [
        ("<!-- HOLIDAY-HERO-START -->",   "<!-- HOLIDAY-HERO-END -->",   "hero_a_html"),
        ("<!-- HOLIDAY-HERO-B-START -->", "<!-- HOLIDAY-HERO-B-END -->", "hero_b_html"),
    ]:
        if plan.get(key):
            home, ok = replace_markers(home, start, end, plan[key])
            if not ok:
                warn(f"Home.vue: {start} not found")
    if home != orig:
        write("src/views/Home.vue", home)
        print("[coding] Home.vue updated")

    # ── Footer.vue ────────────────────────────────────────────────────────────
    footer_src = read("src/components/Footer.vue")
    orig = footer_src
    if plan.get("footer_html"):
        footer_src, ok = replace_markers(
            footer_src, "<!-- HOLIDAY-FOOTER-START -->", "<!-- HOLIDAY-FOOTER-END -->", plan["footer_html"],
        )
        if not ok:
            warn("Footer.vue: HOLIDAY-FOOTER markers not found")
    if footer_src != orig:
        write("src/components/Footer.vue", footer_src)
        print("[coding] Footer.vue updated")

    # ── index.html — title emoji ──────────────────────────────────────────────
    html = read("index.html")
    orig = html
    base_title = "Meridian — Where Ideas Converge"
    emoji = plan.get("title_emoji", "").strip()
    new_title = f"{base_title} {emoji}".rstrip() if emoji else base_title
    html = re.sub(r"<title>Meridian[^<]*</title>", f"<title>{new_title}</title>", html)
    if html != orig:
        write("index.html", html)
        print(f"[coding] index.html title → {new_title}")

    ctx.context.files_changed = files_changed
    ctx.context.patch_errors = patch_errors

    summary = f"Patched files: {files_changed or ['(none)']}"
    if patch_errors:
        summary += f"\nWarnings: {patch_errors}"
    return summary


@function_tool
def read_frontend_file(ctx: RunContextWrapper[RebrandCtx], filename: str) -> str:
    """Read a frontend source file so the CodingAgent can inspect current content
    before making targeted fixes.

    filename must be one of: src/style.css, src/components/Navbar.vue,
    src/views/Home.vue, src/components/Footer.vue, index.html
    """
    if filename not in _ALLOWED:
        return f"ERROR: '{filename}' is not an allowed file. Choose from: {sorted(_ALLOWED)}"
    content = (_frontend(ctx) / filename).read_text(encoding="utf-8")
    return content[:8000]  # cap to avoid bloating the conversation


@function_tool
def write_frontend_file(ctx: RunContextWrapper[RebrandCtx], filename: str, content: str) -> str:
    """Overwrite a frontend source file with corrected content.

    Used by CodingAgent to apply targeted accessibility or SEO fixes that
    cannot be expressed as plan-level changes.  filename must be one of the
    allowed set (same as read_frontend_file).
    """
    if filename not in _ALLOWED:
        return f"ERROR: '{filename}' is not an allowed file. Choose from: {sorted(_ALLOWED)}"
    path = _frontend(ctx) / filename
    path.write_text(content, encoding="utf-8")
    if filename not in ctx.context.files_changed:
        ctx.context.files_changed.append(filename)
    print(f"[coding] {filename} written ({len(content)} chars)")
    return f"Written: {filename}"
