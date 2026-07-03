"""Tests for the static-analysis / pure-logic tools in maintenance_agent/tools.py:
check_frontend_static, check_internal_links, analyze_post_seo, analyze_html_fragment.
"""
import json
from pathlib import Path

from meridian_agents.maintenance_agent import tools as tools_mod
from meridian_agents.maintenance_agent.tools import (
    check_frontend_static,
    check_internal_links,
    analyze_post_seo,
    analyze_html_fragment,
)

GOOD_INDEX_HTML = """<!DOCTYPE html><html lang="en">
<head>
<meta name="description" content="desc">
og:title og:description og:type og:url
twitter:card twitter:title
<meta name="viewport" content="width=device-width">
<link rel="canonical" href="https://x">
</head></html>"""

GOOD_ROBOTS = "User-agent: *\nAllow: /"
GOOD_ROUTER = "router.afterEach((to) => { document.title = to.meta.title })"
GOOD_APP = '<a href="#main-content" class="sr-only">Skip to content</a>'
GOOD_HOME = (
    'id="main-content" id="main-content" '
    'aria-label="Email address for newsletter" aria-label="Email address for newsletter"'
)
GOOD_NAVBAR = 'aria-label="Toggle navigation" aria-expanded="false"'
GOOD_FOOTER = (
    'Follow Meridian on Twitter Follow Meridian on LinkedIn Follow Meridian on Instagram <h3>Topics</h3>'
)
GOOD_BLOGPOST = '<h2 class="x">Photo Gallery</h2>'
GOOD_STYLE = ":focus-visible { outline: 2px solid; }"
GOOD_WORKFLOW = "FORCE_MAINTENANCE: true"


def _write_full_good_frontend(base: Path):
    (base / "frontend").mkdir(parents=True, exist_ok=True)
    (base / "frontend/index.html").write_text(GOOD_INDEX_HTML)
    (base / "frontend/public").mkdir(parents=True, exist_ok=True)
    (base / "frontend/public/robots.txt").write_text(GOOD_ROBOTS)
    (base / "frontend/src/router").mkdir(parents=True, exist_ok=True)
    (base / "frontend/src/router/index.js").write_text(GOOD_ROUTER)
    (base / "frontend/src/App.vue").write_text(GOOD_APP)
    (base / "frontend/src/views").mkdir(parents=True, exist_ok=True)
    (base / "frontend/src/views/Home.vue").write_text(GOOD_HOME)
    (base / "frontend/src/components").mkdir(parents=True, exist_ok=True)
    (base / "frontend/src/components/Navbar.vue").write_text(GOOD_NAVBAR)
    (base / "frontend/src/components/Footer.vue").write_text(GOOD_FOOTER)
    (base / "frontend/src/views/BlogPost.vue").write_text(GOOD_BLOGPOST)
    (base / "frontend/src/style.css").write_text(GOOD_STYLE)
    (base / ".github/workflows").mkdir(parents=True, exist_ok=True)
    (base / ".github/workflows/run-maintenance-agent.yml").write_text(GOOD_WORKFLOW)


class TestCheckFrontendStatic:
    def test_reports_all_checks_missing_on_an_empty_tree(self, tmp_path):
        result = json.loads(check_frontend_static(str(tmp_path)))
        assert result["passedCount"] == 0
        assert result["failedCount"] > 0

    def test_reports_everything_passing_on_a_compliant_tree(self, tmp_path):
        _write_full_good_frontend(tmp_path)
        result = json.loads(check_frontend_static(str(tmp_path)))
        assert result["failedCount"] == 0
        assert result["passedCount"] > 0

    def test_flags_home_with_only_one_main_content_id(self, tmp_path):
        _write_full_good_frontend(tmp_path)
        (tmp_path / "frontend/src/views/Home.vue").write_text('id="main-content"')
        result = json.loads(check_frontend_static(str(tmp_path)))
        assert any("only found once" in f["message"] for f in result["failed"])

    def test_flags_footer_using_h4_headings(self, tmp_path):
        _write_full_good_frontend(tmp_path)
        (tmp_path / "frontend/src/components/Footer.vue").write_text(
            GOOD_FOOTER.replace("<h3>Topics</h3>", "<h4>Topics</h4>")
        )
        result = json.loads(check_frontend_static(str(tmp_path)))
        assert any("h4" in f["message"] for f in result["failed"])

    def test_flags_blogpost_photo_gallery_as_h3(self, tmp_path):
        _write_full_good_frontend(tmp_path)
        (tmp_path / "frontend/src/views/BlogPost.vue").write_text('<h3 class="x">Photo Gallery</h3>')
        result = json.loads(check_frontend_static(str(tmp_path)))
        assert any("h3" in f["message"] and "Photo Gallery" in f["message"] for f in result["failed"])

    def test_uses_repo_root_by_default(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        result = json.loads(check_frontend_static())
        assert result["failedCount"] > 0


class TestCheckInternalLinks:
    ROUTER = """
routes: [
  { path: '/', component: Home },
  { path: '/blog', component: BlogList },
  { path: '/admin', component: Layout, children: [
      { path: 'dashboard', component: Dashboard },
      { path: 'posts', component: Posts },
  ]},
  { path: '/:pathMatch(.*)*', component: NotFound },
]
"""

    def _write_router(self, base: Path):
        d = base / "frontend/src/router"
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.js").write_text(self.ROUTER)

    def test_reports_no_broken_links_for_valid_routes(self, tmp_path):
        self._write_router(tmp_path)
        src = tmp_path / "frontend/src/components"
        src.mkdir(parents=True, exist_ok=True)
        (src / "Nav.vue").write_text('<RouterLink to="/blog">Blog</RouterLink>')
        result = json.loads(check_internal_links(str(tmp_path)))
        assert result["brokenLinks"] == 0
        assert result["filesScanned"] == 2  # router/index.js itself is also a scanned .js file

    def test_detects_a_broken_link(self, tmp_path):
        self._write_router(tmp_path)
        src = tmp_path / "frontend/src/components"
        src.mkdir(parents=True, exist_ok=True)
        (src / "Nav.vue").write_text('<RouterLink to="/does-not-exist">X</RouterLink>')
        result = json.loads(check_internal_links(str(tmp_path)))
        assert result["brokenLinks"] == 1
        assert result["broken"][0]["path"] == "/does-not-exist"

    def test_resolves_nested_child_routes(self, tmp_path):
        self._write_router(tmp_path)
        src = tmp_path / "frontend/src/components"
        src.mkdir(parents=True, exist_ok=True)
        (src / "Nav.vue").write_text('<RouterLink to="/admin/posts">Posts</RouterLink>')
        result = json.loads(check_internal_links(str(tmp_path)))
        assert result["brokenLinks"] == 0

    def test_ignores_api_and_static_asset_paths(self, tmp_path):
        self._write_router(tmp_path)
        src = tmp_path / "frontend/src/components"
        src.mkdir(parents=True, exist_ok=True)
        (src / "Nav.vue").write_text(
            '<a href="/api/posts">API</a> <a href="/logo.svg">Logo</a> <a href="//external.com">Ext</a>'
        )
        result = json.loads(check_internal_links(str(tmp_path)))
        assert result["brokenLinks"] == 0

    def test_handles_missing_router_file(self, tmp_path):
        src = tmp_path / "frontend/src/components"
        src.mkdir(parents=True, exist_ok=True)
        (src / "Nav.vue").write_text('<RouterLink to="/blog">Blog</RouterLink>')
        result = json.loads(check_internal_links(str(tmp_path)))
        assert result["routesFound"] == 0
        assert result["brokenLinks"] == 1

    def test_skips_files_that_cannot_be_read(self, tmp_path, monkeypatch):
        self._write_router(tmp_path)
        src = tmp_path / "frontend/src/components"
        src.mkdir(parents=True, exist_ok=True)
        bad_file = src / "Bad.vue"
        bad_file.write_text("content")

        original_read_text = Path.read_text

        def flaky_read_text(self, *args, **kwargs):
            if self.name == "Bad.vue":
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "bad")
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", flaky_read_text)
        result = json.loads(check_internal_links(str(tmp_path)))
        # filesScanned counts every matched file regardless of read success;
        # Bad.vue contributes no broken-link findings since it couldn't be read.
        assert result["filesScanned"] == 2
        assert result["brokenLinks"] == 0


class TestAnalyzePostSeo:
    def test_flags_a_too_short_title(self):
        result = json.loads(analyze_post_seo("Short", "x" * 130, "good-slug", 900))
        assert any(i["field"] == "title" and "too short" in i["message"] for i in result["issues"])

    def test_flags_a_too_long_title(self):
        result = json.loads(analyze_post_seo("x" * 80, "x" * 130, "good-slug", 900))
        assert any(i["field"] == "title" and "too long" in i["message"] for i in result["issues"])

    def test_flags_missing_excerpt(self):
        result = json.loads(analyze_post_seo("x" * 55, "", "good-slug", 900))
        assert any(i["field"] == "excerpt" and i["severity"] == "critical" for i in result["issues"])

    def test_flags_underscore_and_uppercase_slug(self):
        result = json.loads(analyze_post_seo("x" * 55, "x" * 130, "Bad_Slug", 900))
        messages = [i["message"] for i in result["issues"]]
        assert any("underscores" in m for m in messages)
        assert any("uppercase" in m for m in messages)

    def test_flags_short_content(self):
        result = json.loads(analyze_post_seo("x" * 55, "x" * 130, "good-slug", 100))
        assert any(i["field"] == "content" and i["severity"] == "high" for i in result["issues"])

    def test_perfect_post_scores_100(self):
        result = json.loads(analyze_post_seo("x" * 55, "x" * 130, "a-good-slug", 900))
        assert result["score"] == 100
        assert result["issues"] == []

    def test_computes_read_time(self):
        result = json.loads(analyze_post_seo("x" * 55, "x" * 130, "good-slug", 400))
        assert result["readTimeMinutes"] == 2


class TestAnalyzeHtmlFragment:
    def test_flags_image_without_alt(self):
        result = json.loads(analyze_html_fragment('<img src="a.jpg">', "test"))
        assert any(f["wcag"] == "1.1.1" and f["severity"] == "critical" for f in result["findings"])

    def test_flags_image_with_empty_alt(self):
        result = json.loads(analyze_html_fragment('<img src="a.jpg" alt="">', "test"))
        assert any(f["severity"] == "medium" and "empty alt" in f["message"] for f in result["findings"])

    def test_flags_button_without_label(self):
        result = json.loads(analyze_html_fragment("<button></button>", "test"))
        assert any(f["wcag"] == "4.1.2" for f in result["findings"])

    def test_does_not_flag_button_with_aria_label(self):
        result = json.loads(analyze_html_fragment('<button aria-label="Close"></button>', "test"))
        assert result["issueCount"] == 0

    def test_flags_link_without_text(self):
        result = json.loads(analyze_html_fragment('<a href="/x"></a>', "test"))
        assert any(f["wcag"] == "2.4.4" for f in result["findings"])

    def test_flags_skipped_heading_level(self):
        result = json.loads(analyze_html_fragment("<h1>T</h1><h3>Sub</h3>", "test"))
        assert any(f["wcag"] == "1.3.1" and "skipped" in f["message"] for f in result["findings"])

    def test_flags_table_without_headers(self):
        result = json.loads(analyze_html_fragment("<table><tr><td>1</td></tr></table>", "test"))
        assert any(f["element"] == "table" for f in result["findings"])

    def test_clean_html_has_no_findings(self):
        html = '<h1>T</h1><h2>S</h2><img src="a.jpg" alt="desc"><a href="/x">Click here</a><table><th scope="col">H</th></table>'
        result = json.loads(analyze_html_fragment(html, "test"))
        assert result["issueCount"] == 0
