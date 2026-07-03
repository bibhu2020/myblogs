"""Tests for rebranding_agent/tools/testing.py: verify_build, run_structural_tests.

`run` is always mocked in verify_build tests — no real `npm run build` ever
executes. run_structural_tests is pure file/string analysis, no subprocess.
"""
import asyncio
import json
import subprocess
from unittest.mock import patch, MagicMock

from agents.tool_context import ToolContext

from meridian_agents.rebranding_agent.context import RebrandCtx
from meridian_agents.rebranding_agent.tools import testing as testing_mod
from meridian_agents.rebranding_agent.tools.testing import (
    verify_build,
    run_structural_tests,
)


def _invoke(tool, ctx: RebrandCtx, **kwargs):
    tc = ToolContext(context=ctx, tool_name=tool.name, tool_call_id="1", tool_arguments="{}")
    return asyncio.run(tool.on_invoke_tool(tc, json.dumps(kwargs)))


def _proc(stdout="", stderr="", returncode=0):
    return MagicMock(stdout=stdout, stderr=stderr, returncode=returncode)


class TestVerifyBuild:
    def test_reports_build_passed(self):
        ctx = RebrandCtx(repo_root="/repo")
        with patch.object(testing_mod, "run", return_value=_proc(returncode=0, stdout="built")):
            result = _invoke(verify_build, ctx)
        assert result == "BUILD PASSED"

    def test_reports_build_failed_with_error_excerpt(self):
        ctx = RebrandCtx(repo_root="/repo")
        with patch.object(testing_mod, "run", return_value=_proc(returncode=1, stderr="TS2304: Cannot find name")):
            result = _invoke(verify_build, ctx)
        assert result.startswith("BUILD FAILED")
        assert "TS2304" in result

    def test_reports_timeout(self):
        ctx = RebrandCtx(repo_root="/repo")
        with patch.object(testing_mod, "run", side_effect=subprocess.TimeoutExpired("npm", 300)):
            result = _invoke(verify_build, ctx)
        assert result == "BUILD FAILED: timed out after 300s"


GOOD_STYLE = ":focus-visible { outline: 2px solid; }\n" + "\n".join(
    f"--color-primary-{s}: #111111;" for s in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)
)
GOOD_NAVBAR = (
    "<template>\n"
    "<!-- HOLIDAY-BANNER-START -->\n<!-- HOLIDAY-BANNER-END -->\n"
    "<!-- HOLIDAY-BANNER-B-START -->\n<!-- HOLIDAY-BANNER-B-END -->\n"
    "</template>"
)
GOOD_HOME = (
    "<template>\n"
    "<!-- HOLIDAY-HERO-START -->\n<!-- HOLIDAY-HERO-END -->\n"
    "<!-- HOLIDAY-HERO-B-START -->\n<!-- HOLIDAY-HERO-B-END -->\n"
    "</template>"
)
GOOD_FOOTER = (
    "<template>\n"
    "<!-- HOLIDAY-FOOTER-START -->\n<!-- HOLIDAY-FOOTER-END -->\n"
    "</template>"
)
GOOD_PLAN = {
    "palette_a": {
        "primary-600": "#0a0a0a", "primary-700": "#080808",
        "primary-800": "#060606", "primary-900": "#040404",
    },
    "lb_accent": {"lb-accent-bg": "#050505"},
    "banner_a_html": "<div>a</div>",
    "hero_a_html": "<div>h</div>",
    "footer_html": "<p>f</p>",
    "banner_b_html": "<div>b</div>",
    "hero_b_html": "<div>hb</div>",
}


def _write_frontend(tmp_path, *, style=GOOD_STYLE, navbar=GOOD_NAVBAR, home=GOOD_HOME, footer=GOOD_FOOTER):
    frontend = tmp_path / "frontend"
    (frontend / "src/components").mkdir(parents=True)
    (frontend / "src/views").mkdir(parents=True)
    (frontend / "src/style.css").write_text(style)
    (frontend / "src/components/Navbar.vue").write_text(navbar)
    (frontend / "src/views/Home.vue").write_text(home)
    (frontend / "src/components/Footer.vue").write_text(footer)
    return frontend


class TestRunStructuralTests:
    def test_passes_a_fully_compliant_frontend(self, tmp_path):
        _write_frontend(tmp_path)
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(run_structural_tests, ctx)
        assert result == "TESTS PASSED"

    def test_flags_missing_css_variable(self, tmp_path):
        _write_frontend(tmp_path, style=GOOD_STYLE.replace("--color-primary-600: #111111;", ""))
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(run_structural_tests, ctx)
        assert "TESTS FAILED" in result
        assert "--color-primary-600 not found" in ctx.test_feedback

    def test_flags_low_contrast_shade(self, tmp_path):
        _write_frontend(tmp_path)
        plan = {**GOOD_PLAN, "palette_a": {**GOOD_PLAN["palette_a"], "primary-600": "#eeeeee"}}
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=plan)
        result = _invoke(run_structural_tests, ctx)
        assert "WCAG AA fail" in ctx.test_feedback

    def test_flags_missing_palette_shade(self, tmp_path):
        _write_frontend(tmp_path)
        plan = {**GOOD_PLAN, "palette_a": {"primary-600": "#0a0a0a"}}
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=plan)
        result = _invoke(run_structural_tests, ctx)
        assert "missing from plan's palette_a" in ctx.test_feedback

    def test_flags_low_contrast_lb_accent_bg(self, tmp_path):
        _write_frontend(tmp_path)
        plan = {**GOOD_PLAN, "lb_accent": {"lb-accent-bg": "#eeeeee"}}
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=plan)
        result = _invoke(run_structural_tests, ctx)
        assert "lb-accent-bg=" in ctx.test_feedback

    def test_flags_unbalanced_markers(self, tmp_path):
        _write_frontend(tmp_path, navbar=GOOD_NAVBAR.replace("<!-- HOLIDAY-BANNER-END -->", ""))
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(run_structural_tests, ctx)
        assert "opened but not closed" in ctx.test_feedback

    def test_flags_unbalanced_template_tags(self, tmp_path):
        _write_frontend(tmp_path, navbar=GOOD_NAVBAR + "\n<template>")
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(run_structural_tests, ctx)
        assert "unbalanced <template>" in ctx.test_feedback

    def test_flags_missing_focus_visible(self, tmp_path):
        style_without_focus = "\n".join(
            f"--color-primary-{s}: #111111;" for s in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)
        )
        _write_frontend(tmp_path, style=style_without_focus)
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(run_structural_tests, ctx)
        assert "A11Y: :focus-visible rule missing" in ctx.test_feedback

    def test_flags_unresolved_placeholder_in_html_snippet(self, tmp_path):
        _write_frontend(tmp_path)
        plan = {**GOOD_PLAN, "banner_a_html": "<div>{primary-600}</div>"}
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=plan)
        result = _invoke(run_structural_tests, ctx)
        assert "unresolved {primary-...} placeholder" in ctx.test_feedback
