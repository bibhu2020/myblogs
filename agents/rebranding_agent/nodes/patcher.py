"""Steps 3-4 apply: patch frontend source files with the rebrand plan."""
import os
import re
from pathlib import Path

from ..state import RebrandState


# ── helpers ───────────────────────────────────────────────────────────────────

def _norm_hex(val: str) -> str:
    """Ensure hex value has leading #."""
    val = val.strip()
    return val if val.startswith("#") else f"#{val}"


def _replace_markers(content: str, start: str, end: str, inner: str) -> tuple[str, bool]:
    """Replace everything between (and including) start…end markers with new content."""
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(content):
        return content, False
    replacement = f"{start}\n{inner}\n{end}"
    return pattern.sub(replacement, content), True


def _patch_primary_palette(css: str, palette: dict) -> str:
    """Replace --color-primary-* hex values inside the @theme block."""
    for shade, raw_hex in palette.items():
        hex_val = _norm_hex(raw_hex)
        css = re.sub(
            r"(--color-" + re.escape(shade) + r":\s*)#[0-9a-fA-F]{3,8}",
            r"\g<1>" + hex_val,
            css,
        )
    return css


def _patch_lb_accent(css: str, lb: dict) -> str:
    """Replace lb-accent CSS variable values (works inside or outside @theme)."""
    var_map = {
        "lb-accent":          "--color-lb-accent",
        "lb-accent-bg":       "--color-lb-accent-bg",
        "lb-accent-bg-hover": "--color-lb-accent-hover",
        "lb-card-hover":      "--color-lb-card-hover",
    }
    for key, css_var in var_map.items():
        if key not in lb:
            continue
        hex_val = _norm_hex(lb[key])
        css = re.sub(
            r"(" + re.escape(css_var) + r":\s*)#[0-9a-fA-F]{3,8}",
            r"\g<1>" + hex_val,
            css,
        )
    return css


# ── main node ─────────────────────────────────────────────────────────────────

def apply_changes_node(state: RebrandState) -> dict:
    """Apply palette and messaging changes to all frontend source files."""
    repo_root = state["repo_root"]
    plan = state.get("rebrand_plan", {})

    if not plan:
        return {"error": "No rebrand plan in state — cannot patch files"}

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
    if palette_a:
        style = _patch_primary_palette(style, palette_a)

    lb_accent = plan.get("lb_accent", {})
    if lb_accent:
        style = _patch_lb_accent(style, lb_accent)

    holiday_css = plan.get("holiday_css", "").strip()
    if holiday_css:
        style, ok = _replace_markers(style, "/* HOLIDAY-CSS-START */", "/* HOLIDAY-CSS-END */", holiday_css)
        if not ok:
            warn("style.css: /* HOLIDAY-CSS-START/END */ markers not found — appending block")
            style += f"\n/* HOLIDAY-CSS-START */\n{holiday_css}\n/* HOLIDAY-CSS-END */\n"

    if style != orig:
        write("src/style.css", style)
        print(f"[patcher] style.css updated (palette + accents + holiday CSS)")

    # ── Navbar.vue ────────────────────────────────────────────────────────────
    nav = read("src/components/Navbar.vue")
    orig = nav

    if plan.get("banner_a_html"):
        nav, ok = _replace_markers(nav, "<!-- HOLIDAY-BANNER-START -->", "<!-- HOLIDAY-BANNER-END -->", plan["banner_a_html"])
        if not ok:
            warn("Navbar.vue: HOLIDAY-BANNER-START/END not found")

    if plan.get("banner_b_html"):
        nav, ok = _replace_markers(nav, "<!-- HOLIDAY-BANNER-B-START -->", "<!-- HOLIDAY-BANNER-B-END -->", plan["banner_b_html"])
        if not ok:
            warn("Navbar.vue: HOLIDAY-BANNER-B-START/END not found")

    if nav != orig:
        write("src/components/Navbar.vue", nav)
        print("[patcher] Navbar.vue updated (Layout A + B banners)")

    # ── Home.vue ──────────────────────────────────────────────────────────────
    home = read("src/views/Home.vue")
    orig = home

    if plan.get("hero_a_html"):
        home, ok = _replace_markers(home, "<!-- HOLIDAY-HERO-START -->", "<!-- HOLIDAY-HERO-END -->", plan["hero_a_html"])
        if not ok:
            warn("Home.vue: HOLIDAY-HERO-START/END not found")

    if plan.get("hero_b_html"):
        home, ok = _replace_markers(home, "<!-- HOLIDAY-HERO-B-START -->", "<!-- HOLIDAY-HERO-B-END -->", plan["hero_b_html"])
        if not ok:
            warn("Home.vue: HOLIDAY-HERO-B-START/END not found")

    if home != orig:
        write("src/views/Home.vue", home)
        print("[patcher] Home.vue updated (Layout A + B hero badges)")

    # ── Footer.vue ────────────────────────────────────────────────────────────
    footer = read("src/components/Footer.vue")
    orig = footer

    if plan.get("footer_html"):
        footer, ok = _replace_markers(footer, "<!-- HOLIDAY-FOOTER-START -->", "<!-- HOLIDAY-FOOTER-END -->", plan["footer_html"])
        if not ok:
            warn("Footer.vue: HOLIDAY-FOOTER-START/END not found")

    if footer != orig:
        write("src/components/Footer.vue", footer)
        print("[patcher] Footer.vue updated (shared footer line)")

    # ── index.html — title emoji ───────────────────────────────────────────────
    html = read("index.html")
    orig = html
    base_title = "Meridian — Where Ideas Converge"
    emoji = plan.get("title_emoji", "").strip()
    new_title = f"{base_title} {emoji}".rstrip() if emoji else base_title
    html = re.sub(r"<title>Meridian[^<]*</title>", f"<title>{new_title}</title>", html)
    if html != orig:
        write("index.html", html)
        print(f"[patcher] index.html title updated to: {new_title}")

    return {"files_changed": files_changed, "patch_errors": patch_errors}
