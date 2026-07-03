"""Tests for rebranding_agent/tools/coding.py: patch_frontend_files,
read_frontend_file, write_frontend_file.

These are @function_tool-decorated — the decorator wraps them into a
FunctionTool object that isn't directly callable, so tests invoke the real
logic via `tool.on_invoke_tool(ToolContext(...), json_args)`, matching how
the OpenAI Agents SDK actually calls them at runtime.
"""
import asyncio
import json

from agents.tool_context import ToolContext

from meridian_agents.rebranding_agent.context import RebrandCtx
from meridian_agents.rebranding_agent.tools.coding import (
    patch_frontend_files,
    read_frontend_file,
    write_frontend_file,
)


def _invoke(tool, ctx: RebrandCtx, **kwargs):
    tc = ToolContext(context=ctx, tool_name=tool.name, tool_call_id="1", tool_arguments="{}")
    return asyncio.run(tool.on_invoke_tool(tc, json.dumps(kwargs)))


STYLE_CSS = """\
:root {
  --color-primary-50: #f0f0f0;
  --color-primary-600: #111111;
  --color-lb-accent: #222222;
  --color-lb-accent-bg: #333333;
  --color-lb-accent-hover: #444444;
  --color-lb-card-hover: #555555;
}
/* HOLIDAY-CSS-START */
/* HOLIDAY-CSS-END */
"""

NAVBAR_VUE = """\
<template>
<!-- HOLIDAY-BANNER-START -->
<!-- HOLIDAY-BANNER-END -->
<!-- HOLIDAY-BANNER-B-START -->
<!-- HOLIDAY-BANNER-B-END -->
</template>
"""

HOME_VUE = """\
<template>
<!-- HOLIDAY-HERO-START -->
<!-- HOLIDAY-HERO-END -->
<!-- HOLIDAY-HERO-B-START -->
<!-- HOLIDAY-HERO-B-END -->
</template>
"""

FOOTER_VUE = """\
<template>
<!-- HOLIDAY-FOOTER-START -->
<!-- HOLIDAY-FOOTER-END -->
</template>
"""

INDEX_HTML = "<title>Meridian — Where Ideas Converge</title>"


def _write_frontend(tmp_path):
    frontend = tmp_path / "frontend"
    (frontend / "src/components").mkdir(parents=True)
    (frontend / "src/views").mkdir(parents=True)
    (frontend / "src/style.css").write_text(STYLE_CSS)
    (frontend / "src/components/Navbar.vue").write_text(NAVBAR_VUE)
    (frontend / "src/views/Home.vue").write_text(HOME_VUE)
    (frontend / "src/components/Footer.vue").write_text(FOOTER_VUE)
    (frontend / "index.html").write_text(INDEX_HTML)
    return frontend


_PLAN = {
    "palette_a": {"primary-50": "#aaaaaa", "primary-600": "#bbbbbb"},
    "lb_accent": {
        "lb-accent": "#cccccc",
        "lb-accent-bg": "#dddddd",
        "lb-accent-bg-hover": "#eeeeee",
        "lb-card-hover": "#ffffff",
    },
    "holiday_css": ".holiday { color: red; }",
    "banner_a_html": '<div role="banner" aria-label="x">Banner A</div>',
    "banner_b_html": '<div role="banner" aria-label="x">Banner B</div>',
    "hero_a_html": '<div class="holiday-badge" aria-label="x">Hero A</div>',
    "hero_b_html": '<div class="holiday-badge-b" aria-label="x">Hero B</div>',
    "footer_html": "<p>Footer message</p>",
    "title_emoji": "🎄",
}


class TestPatchFrontendFiles:
    def test_errors_without_a_plan_in_context(self, tmp_path):
        _write_frontend(tmp_path)
        ctx = RebrandCtx(repo_root=str(tmp_path))
        result = _invoke(patch_frontend_files, ctx)
        assert "ERROR" in result
        assert "IdeationAgent" in result

    def test_patches_all_five_files(self, tmp_path):
        frontend = _write_frontend(tmp_path)
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=_PLAN)
        result = _invoke(patch_frontend_files, ctx)

        style = (frontend / "src/style.css").read_text()
        assert "#aaaaaa" in style
        assert "#bbbbbb" in style
        assert "#cccccc" in style
        assert ".holiday { color: red; }" in style

        nav = (frontend / "src/components/Navbar.vue").read_text()
        assert "Banner A" in nav
        assert "Banner B" in nav

        home = (frontend / "src/views/Home.vue").read_text()
        assert "Hero A" in home
        assert "Hero B" in home

        footer = (frontend / "src/components/Footer.vue").read_text()
        assert "Footer message" in footer

        html = (frontend / "index.html").read_text()
        assert "🎄" in html

        assert set(ctx.files_changed) == {
            "src/style.css", "src/components/Navbar.vue", "src/views/Home.vue",
            "src/components/Footer.vue", "index.html",
        }
        assert ctx.patch_errors == []
        assert "Patched files" in result

    def test_appends_holiday_css_when_markers_missing_and_warns(self, tmp_path):
        frontend = _write_frontend(tmp_path)
        (frontend / "src/style.css").write_text(STYLE_CSS.replace(
            "/* HOLIDAY-CSS-START */\n/* HOLIDAY-CSS-END */\n", ""
        ))
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=_PLAN)
        result = _invoke(patch_frontend_files, ctx)
        style = (frontend / "src/style.css").read_text()
        assert ".holiday { color: red; }" in style
        assert any("markers not found" in e for e in ctx.patch_errors)
        assert "Warnings" in result

    def test_warns_when_navbar_markers_missing(self, tmp_path):
        frontend = _write_frontend(tmp_path)
        (frontend / "src/components/Navbar.vue").write_text("<template></template>")
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=_PLAN)
        _invoke(patch_frontend_files, ctx)
        assert any("Navbar.vue" in e for e in ctx.patch_errors)

    def test_leaves_title_unchanged_without_emoji(self, tmp_path):
        frontend = _write_frontend(tmp_path)
        plan = {**_PLAN, "title_emoji": ""}
        ctx = RebrandCtx(repo_root=str(tmp_path), rebrand_plan=plan)
        _invoke(patch_frontend_files, ctx)
        html = (frontend / "index.html").read_text()
        assert html == "<title>Meridian — Where Ideas Converge</title>"


class TestReadFrontendFile:
    def test_reads_an_allowed_file(self, tmp_path):
        _write_frontend(tmp_path)
        ctx = RebrandCtx(repo_root=str(tmp_path))
        result = _invoke(read_frontend_file, ctx, filename="src/style.css")
        assert "--color-primary-50" in result

    def test_rejects_a_disallowed_file(self, tmp_path):
        _write_frontend(tmp_path)
        ctx = RebrandCtx(repo_root=str(tmp_path))
        result = _invoke(read_frontend_file, ctx, filename="../../etc/passwd")
        assert "ERROR" in result
        assert "not an allowed file" in result

    def test_truncates_content_to_8000_chars(self, tmp_path):
        frontend = _write_frontend(tmp_path)
        (frontend / "src/style.css").write_text("x" * 10000)
        ctx = RebrandCtx(repo_root=str(tmp_path))
        result = _invoke(read_frontend_file, ctx, filename="src/style.css")
        assert len(result) == 8000


class TestWriteFrontendFile:
    def test_writes_an_allowed_file_and_tracks_it(self, tmp_path):
        frontend = _write_frontend(tmp_path)
        ctx = RebrandCtx(repo_root=str(tmp_path))
        result = _invoke(write_frontend_file, ctx, filename="src/style.css", content="new content")
        assert (frontend / "src/style.css").read_text() == "new content"
        assert ctx.files_changed == ["src/style.css"]
        assert "Written" in result

    def test_does_not_duplicate_an_already_tracked_file(self, tmp_path):
        _write_frontend(tmp_path)
        ctx = RebrandCtx(repo_root=str(tmp_path))
        _invoke(write_frontend_file, ctx, filename="src/style.css", content="v1")
        _invoke(write_frontend_file, ctx, filename="src/style.css", content="v2")
        assert ctx.files_changed == ["src/style.css"]

    def test_rejects_a_disallowed_file(self, tmp_path):
        _write_frontend(tmp_path)
        ctx = RebrandCtx(repo_root=str(tmp_path))
        result = _invoke(write_frontend_file, ctx, filename="package.json", content="{}")
        assert "ERROR" in result
