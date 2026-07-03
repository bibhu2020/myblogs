"""Tests for rebranding_agent/tools/review.py: review_seo_ada.
Pure static analysis over files on disk — no network/subprocess involved.
"""
import asyncio
import json

from agents.tool_context import ToolContext

from meridian_agents.rebranding_agent.context import RebrandCtx
from meridian_agents.rebranding_agent.tools.review import review_seo_ada


def _invoke(tool, ctx: RebrandCtx, **kwargs):
    tc = ToolContext(context=ctx, tool_name=tool.name, tool_call_id="1", tool_arguments="{}")
    return asyncio.run(tool.on_invoke_tool(tc, json.dumps(kwargs)))


GOOD_PLAN = {
    "palette_a": {
        "primary-600": "#0a0a0a", "primary-700": "#080808",
        "primary-800": "#060606", "primary-900": "#040404",
    },
    "lb_accent": {"lb-accent-bg": "#050505"},
    "holiday_css": ":focus-visible { outline: 2px solid; }",
}

GOOD_NAVBAR = (
    '<img src="a.jpg" alt="A photo">'
    '<div role="banner" aria-label="announcement">Banner</div>'
    '<div class="holiday-badge" aria-label="badge">Hi</div>'
)
GOOD_HOME = '<div class="holiday-badge" aria-label="badge">Hi</div>'
GOOD_FOOTER = '<img src="b.jpg" alt="B photo">'
GOOD_STYLE = ":focus-visible { outline: 2px solid; }"
GOOD_HTML = (
    "<title>Meridian — Winter Holidays Edition</title>"
    '<meta name="description" content="A blogging platform celebrating the season with style.">'
)


def _write_frontend(tmp_path, *, navbar=GOOD_NAVBAR, home=GOOD_HOME, footer=GOOD_FOOTER,
                     style=GOOD_STYLE, html=GOOD_HTML):
    frontend = tmp_path / "frontend"
    (frontend / "src/components").mkdir(parents=True)
    (frontend / "src/views").mkdir(parents=True)
    (frontend / "src/components/Navbar.vue").write_text(navbar)
    (frontend / "src/views/Home.vue").write_text(home)
    (frontend / "src/components/Footer.vue").write_text(footer)
    (frontend / "src/style.css").write_text(style)
    (frontend / "index.html").write_text(html)
    return frontend


class TestReviewSeoAda:
    def test_passes_a_fully_compliant_frontend(self, tmp_path):
        _write_frontend(tmp_path)
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN, files_changed=["index.html"])
        result = _invoke(review_seo_ada, ctx)
        assert result == "REVIEW PASSED — all SEO and ADA checks passed."
        assert ctx.review_feedback == ""

    def test_flags_low_contrast_palette_shades(self, tmp_path):
        _write_frontend(tmp_path)
        plan = {**GOOD_PLAN, "palette_a": {**GOOD_PLAN["palette_a"], "primary-600": "#eeeeee"}}
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=plan)
        result = _invoke(review_seo_ada, ctx)
        assert "REVIEW FAILED" in result
        assert "CONTRAST" in result
        assert "IdeationAgent" in result

    def test_flags_missing_palette_shade(self, tmp_path):
        _write_frontend(tmp_path)
        plan = {**GOOD_PLAN, "palette_a": {"primary-600": "#0a0a0a"}}
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=plan)
        result = _invoke(review_seo_ada, ctx)
        assert "missing from palette_a" in ctx.review_feedback

    def test_flags_bad_hex_in_lb_accent_bg(self, tmp_path):
        _write_frontend(tmp_path)
        plan = {**GOOD_PLAN, "lb_accent": {"lb-accent-bg": "not-a-hex"}}
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=plan)
        result = _invoke(review_seo_ada, ctx)
        assert "bad hex value" in ctx.review_feedback

    def test_flags_missing_alt_attribute(self, tmp_path):
        _write_frontend(tmp_path, navbar=GOOD_NAVBAR.replace(' alt="A photo"', ""))
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(review_seo_ada, ctx)
        assert "missing alt attribute" in ctx.review_feedback

    def test_flags_empty_alt_attribute(self, tmp_path):
        _write_frontend(tmp_path, navbar=GOOD_NAVBAR.replace('alt="A photo"', 'alt=""'))
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(review_seo_ada, ctx)
        assert "empty alt" in ctx.review_feedback

    def test_flags_banner_missing_aria_label(self, tmp_path):
        _write_frontend(tmp_path, navbar=GOOD_NAVBAR.replace(' aria-label="announcement"', ""))
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(review_seo_ada, ctx)
        assert "role=banner div missing aria-label" in ctx.review_feedback

    def test_flags_holiday_badge_missing_aria_label(self, tmp_path):
        _write_frontend(tmp_path, home=GOOD_HOME.replace(' aria-label="badge"', ""))
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(review_seo_ada, ctx)
        assert "holiday-badge div missing aria-label" in ctx.review_feedback

    def test_flags_missing_focus_visible_in_plan_css(self, tmp_path):
        _write_frontend(tmp_path)
        plan = {**GOOD_PLAN, "holiday_css": ".x { color: red; }"}
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=plan)
        result = _invoke(review_seo_ada, ctx)
        assert "holiday_css is missing the :focus-visible rule" in ctx.review_feedback

    def test_flags_missing_focus_visible_in_style_css_file(self, tmp_path):
        _write_frontend(tmp_path, style="body { color: black; }")
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(review_seo_ada, ctx)
        assert ":focus-visible rule not found in style.css" in ctx.review_feedback

    def test_flags_missing_title_tag(self, tmp_path):
        _write_frontend(tmp_path, html='<meta name="description" content="x">')
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(review_seo_ada, ctx)
        assert "missing <title> tag" in ctx.review_feedback

    def test_flags_too_short_title(self, tmp_path):
        _write_frontend(tmp_path, html=(
            "<title>Hi</title>"
            '<meta name="description" content="A blogging platform celebrating the season.">'
        ))
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(review_seo_ada, ctx)
        assert "too short" in ctx.review_feedback

    def test_flags_missing_meta_description(self, tmp_path):
        _write_frontend(tmp_path, html="<title>Meridian — Winter Holidays Edition</title>")
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(review_seo_ada, ctx)
        assert 'missing <meta name="description">' in ctx.review_feedback

    def test_flags_unbalanced_holiday_markers(self, tmp_path):
        style = GOOD_STYLE + "\n/* HOLIDAY-CSS-START */\nbody{}\n"  # opened, never closed
        _write_frontend(tmp_path, style=style)
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(review_seo_ada, ctx)
        assert "has no matching" in ctx.review_feedback

    def test_routes_code_only_issues_to_coding_agent(self, tmp_path):
        _write_frontend(tmp_path, navbar=GOOD_NAVBAR.replace(' aria-label="announcement"', ""))
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=GOOD_PLAN)
        result = _invoke(review_seo_ada, ctx)
        assert "CodingAgent" in result
        assert "IdeationAgent" not in result
