"""TesterAgent tools: Vite build + structural unit tests."""
from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from agents import RunContextWrapper, function_tool

from ..context import RebrandCtx
from ._helpers import contrast_ratio, norm_hex, run


_WCAG_AA = 4.5
_WHITE = "#ffffff"


def _frontend(ctx: RunContextWrapper[RebrandCtx]) -> Path:
    return Path(ctx.context.repo_root) / "frontend"


@function_tool
def verify_build(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Run `npm run build` in frontend/ to confirm all patched files compile with Vite.

    Returns 'BUILD PASSED' or 'BUILD FAILED: <error excerpt>'.
    """
    frontend_dir = str(_frontend(ctx))
    print("[tester] Running npm run build...")
    t0 = time.time()
    try:
        result = run(["npm", "run", "build"], cwd=frontend_dir, timeout=300)
    except subprocess.TimeoutExpired:
        return "BUILD FAILED: timed out after 300s"

    elapsed = round(time.time() - t0, 1)
    output = (result.stdout or "")[-2000:]
    if result.stderr:
        output += "\n" + (result.stderr or "")[-1000:]

    if result.returncode == 0:
        print(f"[tester] BUILD PASSED in {elapsed}s")
        return "BUILD PASSED"

    print(f"[tester] BUILD FAILED in {elapsed}s")
    return f"BUILD FAILED: {output[-800:]}"


@function_tool
def run_structural_tests(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Run structural unit tests on the patched frontend files without a test suite.

    Tests performed:
    1. All ten palette_a CSS variables are present in style.css
    2. WCAG AA contrast ratios validated mathematically (primary-600..900 on white)
    3. Layout B lb-accent-bg contrast on white ≥ 4.5:1
    4. Every HOLIDAY marker that is opened is also closed
    5. Vue <template> tags are balanced in each changed Vue file
    6. Holiday CSS block contains :focus-visible rule
    7. No raw {primary-xxx} placeholder strings leaked into HTML snippets

    Returns 'TESTS PASSED' or 'TESTS FAILED' with a numbered list of failures.
    """
    failures: list[str] = []
    frontend = _frontend(ctx)
    plan = ctx.context.rebrand_plan

    # 1. CSS variables present in style.css ───────────────────────────────────
    style = (frontend / "src/style.css").read_text(encoding="utf-8")
    for shade in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900):
        var = f"--color-primary-{shade}"
        if var not in style:
            failures.append(f"CSS: {var} not found in style.css")

    # 2. WCAG AA contrast — palette A ─────────────────────────────────────────
    palette = plan.get("palette_a", {})
    for shade in ("primary-600", "primary-700", "primary-800", "primary-900"):
        raw = palette.get(shade, "")
        if not raw:
            failures.append(f"TEST: {shade} missing from plan's palette_a")
            continue
        try:
            ratio = contrast_ratio(norm_hex(raw), _WHITE)
        except Exception as exc:
            failures.append(f"TEST: {shade}={raw} contrast check error: {exc}")
            continue
        if ratio < _WCAG_AA:
            failures.append(
                f"TEST: WCAG AA fail — {shade}={norm_hex(raw)} "
                f"contrast {ratio:.2f}:1 on white (need ≥4.5:1)"
            )

    # 3. Layout B accent-bg contrast ──────────────────────────────────────────
    lb_bg = plan.get("lb_accent", {}).get("lb-accent-bg", "")
    if lb_bg:
        try:
            ratio = contrast_ratio(norm_hex(lb_bg), _WHITE)
            if ratio < _WCAG_AA:
                failures.append(
                    f"TEST: WCAG AA fail — lb-accent-bg={norm_hex(lb_bg)} "
                    f"contrast {ratio:.2f}:1 on white (need ≥4.5:1)"
                )
        except Exception as exc:
            failures.append(f"TEST: lb-accent-bg={lb_bg} contrast check error: {exc}")

    # 4. Holiday marker balance ────────────────────────────────────────────────
    marker_pairs = [
        ("src/style.css",             "/* HOLIDAY-CSS-START */",    "/* HOLIDAY-CSS-END */"),
        ("src/components/Navbar.vue", "<!-- HOLIDAY-BANNER-START -->",   "<!-- HOLIDAY-BANNER-END -->"),
        ("src/components/Navbar.vue", "<!-- HOLIDAY-BANNER-B-START -->", "<!-- HOLIDAY-BANNER-B-END -->"),
        ("src/views/Home.vue",        "<!-- HOLIDAY-HERO-START -->",     "<!-- HOLIDAY-HERO-END -->"),
        ("src/views/Home.vue",        "<!-- HOLIDAY-HERO-B-START -->",   "<!-- HOLIDAY-HERO-B-END -->"),
        ("src/components/Footer.vue", "<!-- HOLIDAY-FOOTER-START -->",   "<!-- HOLIDAY-FOOTER-END -->"),
    ]
    for rel, start, end in marker_pairs:
        content = (frontend / rel).read_text(encoding="utf-8")
        if start in content and end not in content:
            failures.append(f"MARKER: {rel} — {start!r} opened but not closed")
        if end in content and start not in content:
            failures.append(f"MARKER: {rel} — {end!r} closed but never opened")

    # 5. Vue <template> balance ────────────────────────────────────────────────
    for rel in ("src/components/Navbar.vue", "src/views/Home.vue", "src/components/Footer.vue"):
        content = (frontend / rel).read_text(encoding="utf-8")
        opens = len(re.findall(r"<template\b", content))
        closes = content.count("</template>")
        if opens != closes:
            failures.append(f"VUE: {rel} — unbalanced <template> ({opens} open, {closes} close)")

    # 6. :focus-visible in style.css ──────────────────────────────────────────
    if ":focus-visible" not in style:
        failures.append("A11Y: :focus-visible rule missing from style.css")

    # 7. No {primary-xxx} placeholder leakage in HTML snippets ────────────────
    for key in ("banner_a_html", "hero_a_html", "footer_html", "banner_b_html", "hero_b_html"):
        snippet = plan.get(key, "")
        if re.search(r"\{primary-\w+\}", snippet):
            failures.append(
                f"TEMPLATE: {key} contains unresolved {{primary-...}} placeholder — "
                "LLM must use actual hex values"
            )

    # Result ───────────────────────────────────────────────────────────────────
    if not failures:
        print(f"[tester] TESTS PASSED — {len(marker_pairs) + 7} checks OK")
        return "TESTS PASSED"

    report = "\n".join(f"  {i + 1}. {f}" for i, f in enumerate(failures))
    print(f"[tester] TESTS FAILED — {len(failures)} failure(s)")
    ctx.context.test_feedback = report
    return f"TESTS FAILED — {len(failures)} failure(s):\n{report}"
