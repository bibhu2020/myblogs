"""ReviewerAgent tools: static SEO and ADA compliance analysis."""
from __future__ import annotations

import re
from pathlib import Path

from agents import RunContextWrapper, function_tool

from ..context import RebrandCtx
from ._helpers import contrast_ratio, norm_hex


_WCAG_AA = 4.5
_WHITE = "#ffffff"


def _frontend(ctx: RunContextWrapper[RebrandCtx]) -> Path:
    return Path(ctx.context.repo_root) / "frontend"


@function_tool
def review_seo_ada(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Perform static SEO and ADA/WCAG AA compliance review of all patched frontend files.

    Checks performed:
    - WCAG AA colour contrast: primary-600..900 on white must be ≥ 4.5:1
    - Layout B accent-bg on white must be ≥ 4.5:1
    - All <img> tags must have non-empty alt attributes
    - All banner divs (role=banner) must have aria-label attributes
    - Holiday badge divs must have aria-label attributes
    - Holiday CSS must include :focus-visible rule
    - <title> tag must be present and descriptive (≥ 15 chars)
    - <meta name="description"> must exist in index.html
    - Holiday markers must be balanced (every START has an END)

    Returns 'REVIEW PASSED' or 'REVIEW FAILED' with a numbered issue list.
    Stores feedback in context for feedback-loop use.
    """
    issues: list[str] = []
    frontend = _frontend(ctx)
    plan = ctx.context.rebrand_plan

    # ── 1. WCAG AA colour contrast ────────────────────────────────────────────
    palette = plan.get("palette_a", {})
    for shade in ("primary-600", "primary-700", "primary-800", "primary-900"):
        raw = palette.get(shade, "")
        if not raw:
            issues.append(f"CONTRAST: {shade} missing from palette_a")
            continue
        try:
            ratio = contrast_ratio(norm_hex(raw), _WHITE)
        except Exception:
            issues.append(f"CONTRAST: {shade}={raw} — could not compute contrast (bad hex?)")
            continue
        if ratio < _WCAG_AA:
            issues.append(
                f"CONTRAST: {shade}={norm_hex(raw)} contrast {ratio:.2f}:1 on white < 4.5:1 (WCAG AA)"
            )

    lb = plan.get("lb_accent", {})
    lb_bg = lb.get("lb-accent-bg", "")
    if lb_bg:
        try:
            ratio = contrast_ratio(norm_hex(lb_bg), _WHITE)
            if ratio < _WCAG_AA:
                issues.append(
                    f"CONTRAST: lb-accent-bg={norm_hex(lb_bg)} contrast {ratio:.2f}:1 on white < 4.5:1"
                )
        except Exception:
            issues.append(f"CONTRAST: lb-accent-bg={lb_bg} — bad hex value")

    # ── 2. Alt text on <img> tags ─────────────────────────────────────────────
    for rel in ("src/components/Navbar.vue", "src/views/Home.vue", "src/components/Footer.vue"):
        content = (frontend / rel).read_text(encoding="utf-8")
        for img_tag in re.findall(r"<img\b[^>]*>", content, re.IGNORECASE):
            alt_match = re.search(r'\balt=["\']([^"\']*)["\']', img_tag, re.IGNORECASE)
            if not alt_match:
                issues.append(f"ALT: {rel} — <img> missing alt attribute: {img_tag[:80]}")
            elif not alt_match.group(1).strip():
                issues.append(f"ALT: {rel} — <img> has empty alt (use '' only for decorative images)")

    # ── 3. aria-label on role=banner divs ────────────────────────────────────
    nav = (frontend / "src/components/Navbar.vue").read_text(encoding="utf-8")
    banners = re.findall(r'<div\b[^>]*role=["\']banner["\'][^>]*>', nav, re.IGNORECASE)
    for b in banners:
        if "aria-label" not in b.lower():
            issues.append(f"ARIA: Navbar.vue role=banner div missing aria-label: {b[:100]}")

    # ── 4. aria-label on holiday badges ──────────────────────────────────────
    for rel in ("src/components/Navbar.vue", "src/views/Home.vue"):
        content = (frontend / rel).read_text(encoding="utf-8")
        for badge in re.findall(r'<div\b[^>]*holiday-badge[^>]*>', content, re.IGNORECASE):
            if "aria-label" not in badge.lower():
                issues.append(f"ARIA: {rel} — holiday-badge div missing aria-label: {badge[:100]}")

    # ── 5. :focus-visible in holiday CSS ─────────────────────────────────────
    holiday_css = plan.get("holiday_css", "")
    if ":focus-visible" not in holiday_css:
        issues.append("A11Y: holiday_css is missing the :focus-visible rule (keyboard navigation)")

    # Also check it landed in style.css
    style_content = (frontend / "src/style.css").read_text(encoding="utf-8")
    if ":focus-visible" not in style_content:
        issues.append("A11Y: :focus-visible rule not found in style.css after patching")

    # ── 6. <title> tag ───────────────────────────────────────────────────────
    html = (frontend / "index.html").read_text(encoding="utf-8")
    title_match = re.search(r"<title>([^<]+)</title>", html)
    if not title_match:
        issues.append("SEO: index.html is missing <title> tag")
    elif len(title_match.group(1).strip()) < 15:
        issues.append(f"SEO: <title> is too short ({title_match.group(1)!r}) — should be ≥ 15 chars")

    # ── 7. <meta name="description"> ─────────────────────────────────────────
    if not re.search(r'<meta\s[^>]*name=["\']description["\'][^>]*content=["\'][^"\']{20,}', html, re.IGNORECASE):
        issues.append("SEO: index.html missing <meta name=\"description\"> with meaningful content (≥ 20 chars)")

    # ── 8. Holiday marker balance ─────────────────────────────────────────────
    marker_pairs = [
        ("src/style.css",              "/* HOLIDAY-CSS-START */",    "/* HOLIDAY-CSS-END */"),
        ("src/components/Navbar.vue",  "<!-- HOLIDAY-BANNER-START -->",   "<!-- HOLIDAY-BANNER-END -->"),
        ("src/components/Navbar.vue",  "<!-- HOLIDAY-BANNER-B-START -->", "<!-- HOLIDAY-BANNER-B-END -->"),
        ("src/views/Home.vue",         "<!-- HOLIDAY-HERO-START -->",     "<!-- HOLIDAY-HERO-END -->"),
        ("src/views/Home.vue",         "<!-- HOLIDAY-HERO-B-START -->",   "<!-- HOLIDAY-HERO-B-END -->"),
        ("src/components/Footer.vue",  "<!-- HOLIDAY-FOOTER-START -->",   "<!-- HOLIDAY-FOOTER-END -->"),
    ]
    for rel, start, end in marker_pairs:
        content = (frontend / rel).read_text(encoding="utf-8")
        has_start = start in content
        has_end = end in content
        if has_start and not has_end:
            issues.append(f"MARKER: {rel} — {start} has no matching {end}")
        if has_end and not has_start:
            issues.append(f"MARKER: {rel} — {end} has no matching {start}")

    # ── Result ────────────────────────────────────────────────────────────────
    if not issues:
        print(f"[reviewer] REVIEW PASSED — {len(ctx.context.files_changed)} files checked")
        ctx.context.review_feedback = ""
        return "REVIEW PASSED — all SEO and ADA checks passed."

    feedback = "\n".join(f"  {i + 1}. {issue}" for i, issue in enumerate(issues))
    print(f"[reviewer] REVIEW FAILED — {len(issues)} issue(s):")
    for issue in issues:
        print(f"  ✗ {issue}")
    ctx.context.review_feedback = feedback

    # Classify: contrast issues → IdeationAgent; code issues → CodingAgent
    contrast_issues = [x for x in issues if x.startswith("CONTRAST")]
    code_issues = [x for x in issues if not x.startswith("CONTRAST")]

    routing = []
    if contrast_issues:
        routing.append("contrast issues require plan revision → route to IdeationAgent")
    if code_issues:
        routing.append("code/markup issues require targeted fixes → route to CodingAgent")

    return (
        f"REVIEW FAILED — {len(issues)} issue(s) found:\n{feedback}\n\n"
        f"Routing recommendation: {'; '.join(routing)}"
    )
