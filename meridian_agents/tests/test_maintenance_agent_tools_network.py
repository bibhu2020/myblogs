"""Tests for requests-based tools in maintenance_agent/tools.py. Every
requests.* call is mocked — nothing here hits a real network or GitHub API.
"""
import json
import subprocess
from unittest.mock import patch, MagicMock

from meridian_agents.maintenance_agent import tools as tools_mod
from meridian_agents.maintenance_agent.tools import (
    run_npm_audit,
    list_outdated_packages,
    read_source_file,
    fetch_all_posts,
    fetch_post_html,
    list_github_prs,
    merge_github_pr,
    close_github_pr,
    get_pr_details,
    create_github_pr,
    delete_github_branch,
    check_url_status,
    generate_sitemap,
    get_sitemap_urls,
)


def _proc(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


class TestRunNpmAudit:
    def test_rejects_unknown_service(self):
        result = json.loads(run_npm_audit("not-a-service"))
        assert "error" in result

    def test_errors_when_directory_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        result = json.loads(run_npm_audit("frontend"))
        assert "error" in result

    def test_summarises_vulnerabilities(self, monkeypatch, tmp_path):
        (tmp_path / "frontend").mkdir()
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        audit_json = json.dumps({
            "metadata": {"vulnerabilities": {"high": 1}},
            "auditReportVersion": 2,
            "vulnerabilities": {"lodash": {"severity": "high", "isDirect": True, "fixAvailable": True, "via": ["CVE-123"]}},
        })
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stdout=audit_json)):
            result = json.loads(run_npm_audit("frontend"))
        assert result["service"] == "frontend"
        assert result["topVulnerabilities"][0]["name"] == "lodash"

    def test_handles_empty_output(self, monkeypatch, tmp_path):
        (tmp_path / "frontend").mkdir()
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stdout="")):
            result = json.loads(run_npm_audit("frontend"))
        assert "error" in result

    def test_handles_timeout(self, monkeypatch, tmp_path):
        (tmp_path / "frontend").mkdir()
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch.object(tools_mod.subprocess, "run", side_effect=subprocess.TimeoutExpired("npm", 120)):
            result = json.loads(run_npm_audit("frontend"))
        assert "timed out" in result["error"]

    def test_handles_malformed_json(self, monkeypatch, tmp_path):
        (tmp_path / "frontend").mkdir()
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stdout="not json")):
            result = json.loads(run_npm_audit("frontend"))
        assert "error" in result


class TestListOutdatedPackages:
    def test_rejects_unknown_service(self):
        result = json.loads(list_outdated_packages("nope"))
        assert "error" in result

    def test_errors_when_directory_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        result = json.loads(list_outdated_packages("frontend"))
        assert "error" in result

    def test_reports_no_outdated_packages_when_empty(self, monkeypatch, tmp_path):
        (tmp_path / "frontend").mkdir()
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stdout="")):
            result = json.loads(list_outdated_packages("frontend"))
        assert result["outdated"] == {}

    def test_annotates_bump_type(self, monkeypatch, tmp_path):
        (tmp_path / "frontend").mkdir()
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        outdated_json = json.dumps({
            "vue": {"current": "3.4.0", "latest": "4.0.0"},
            "axios": {"current": "1.2.0", "latest": "1.5.0"},
            "lodash": {"current": "1.2.3", "latest": "1.2.9"},
        })
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stdout=outdated_json)):
            result = json.loads(list_outdated_packages("frontend"))
        assert result["outdated"]["vue"]["bumpType"] == "major"
        assert result["outdated"]["axios"]["bumpType"] == "minor"
        assert result["outdated"]["lodash"]["bumpType"] == "patch"

    def test_handles_timeout(self, monkeypatch, tmp_path):
        (tmp_path / "frontend").mkdir()
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch.object(tools_mod.subprocess, "run", side_effect=subprocess.TimeoutExpired("npm", 120)):
            result = json.loads(list_outdated_packages("frontend"))
        assert "timed out" in result["error"]


class TestReadSourceFile:
    def test_reads_an_existing_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        (tmp_path / "a.txt").write_text("hello")
        assert read_source_file("a.txt") == "hello"

    def test_reports_missing_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        assert "not found" in read_source_file("missing.txt")


class TestFetchAllPosts:
    def test_returns_summarised_posts(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"posts": [{"id": 1, "title": "T", "category": {"name": "Tech"}}]}
            mock_requests.get.return_value = resp
            result = json.loads(fetch_all_posts())
        assert result["total"] == 1
        assert result["posts"][0]["category"] == "Tech"

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.get.side_effect = Exception("down")
            result = json.loads(fetch_all_posts())
        assert "error" in result


class TestFetchPostHtml:
    def test_returns_html_content(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"title": "T", "content": "<p>x</p>"}
            mock_requests.get.return_value = resp
            result = json.loads(fetch_post_html("my-slug"))
        assert result["html"] == "<p>x</p>"

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.get.side_effect = Exception("404")
            result = json.loads(fetch_post_html("missing"))
        assert "error" in result


class TestListGithubPrs:
    def test_lists_open_prs(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            resp = MagicMock(status_code=200)
            resp.raise_for_status.return_value = None
            resp.json.return_value = [{
                "number": 1, "title": "Bump lodash", "user": {"login": "dependabot[bot]"},
                "created_at": "2026-01-01T00:00:00Z", "html_url": "https://gh/1", "labels": [],
            }]
            mock_requests.get.return_value = resp
            result = json.loads(list_github_prs("owner", "repo"))
        assert result["total"] == 1
        assert result["pulls"][0]["isDependabot"] is True

    def test_returns_error_on_404(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.get.return_value = MagicMock(status_code=404)
            result = json.loads(list_github_prs("owner", "missing"))
        assert "error" in result

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.get.side_effect = Exception("boom")
            result = json.loads(list_github_prs("owner", "repo"))
        assert "error" in result


class TestMergeGithubPr:
    def test_errors_without_token(self, monkeypatch):
        monkeypatch.delenv("SECRET_TOKEN_GITHUB", raising=False)
        result = json.loads(merge_github_pr("owner", "repo", 1))
        assert result["success"] is False

    def test_merges_successfully(self, monkeypatch):
        monkeypatch.setenv("SECRET_TOKEN_GITHUB", "tok")
        with patch.object(tools_mod, "requests") as mock_requests:
            resp = MagicMock(status_code=200, content=b"{}")
            resp.json.return_value = {"sha": "abc123"}
            mock_requests.put.return_value = resp
            result = json.loads(merge_github_pr("owner", "repo", 1))
        assert result["success"] is True
        assert result["sha"] == "abc123"

    def test_reports_failure_status(self, monkeypatch):
        monkeypatch.setenv("SECRET_TOKEN_GITHUB", "tok")
        with patch.object(tools_mod, "requests") as mock_requests:
            resp = MagicMock(status_code=405, content=b"{}")
            resp.json.return_value = {"message": "not mergeable"}
            mock_requests.put.return_value = resp
            result = json.loads(merge_github_pr("owner", "repo", 1))
        assert result["success"] is False


class TestCloseGithubPr:
    def test_errors_without_token(self, monkeypatch):
        monkeypatch.delenv("SECRET_TOKEN_GITHUB", raising=False)
        result = json.loads(close_github_pr("owner", "repo", 1))
        assert result["success"] is False

    def test_closes_successfully(self, monkeypatch):
        monkeypatch.setenv("SECRET_TOKEN_GITHUB", "tok")
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.post.return_value = MagicMock(status_code=201)
            mock_requests.patch.return_value = MagicMock(status_code=200, content=b"{}", json=lambda: {})
            result = json.loads(close_github_pr("owner", "repo", 1, reason="superseded"))
        assert result["success"] is True

    def test_reports_partial_when_token_lacks_permission(self, monkeypatch):
        monkeypatch.setenv("SECRET_TOKEN_GITHUB", "tok")
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.post.return_value = MagicMock(status_code=201)
            mock_requests.patch.return_value = MagicMock(status_code=403, content=b"{}", json=lambda: {})
            result = json.loads(close_github_pr("owner", "repo", 1))
        assert result["success"] is False
        assert result["partial"] is True

    def test_returns_error_on_exception(self, monkeypatch):
        monkeypatch.setenv("SECRET_TOKEN_GITHUB", "tok")
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.post.side_effect = Exception("down")
            result = json.loads(close_github_pr("owner", "repo", 1))
        assert result["success"] is False


class TestGetPrDetails:
    def test_returns_error_on_404(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.get.return_value = MagicMock(status_code=404)
            result = json.loads(get_pr_details("owner", "repo", 1))
        assert "error" in result

    def test_detects_major_bump(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            pr_resp = MagicMock(status_code=200)
            pr_resp.raise_for_status.return_value = None
            pr_resp.json.return_value = {
                "number": 1, "title": "Bump vue from 3.4.0 to 4.0.0", "user": {"login": "dependabot"},
                "state": "open", "body": "desc", "mergeable": True, "html_url": "https://gh/1",
            }
            files_resp = MagicMock(ok=True)
            files_resp.json.return_value = [{"filename": "package.json"}]
            mock_requests.get.side_effect = [pr_resp, files_resp]
            result = json.loads(get_pr_details("owner", "repo", 1))
        assert result["semverBump"] == "major"
        assert result["riskLevel"] == "high"

    def test_defaults_to_unknown_bump_without_a_version_pattern(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            pr_resp = MagicMock(status_code=200)
            pr_resp.raise_for_status.return_value = None
            pr_resp.json.return_value = {
                "number": 1, "title": "Fix a typo", "user": {"login": "someone"},
                "state": "open", "body": "", "mergeable": True, "html_url": "https://gh/1",
            }
            files_resp = MagicMock(ok=False)
            mock_requests.get.side_effect = [pr_resp, files_resp]
            result = json.loads(get_pr_details("owner", "repo", 1))
        assert result["semverBump"] == "unknown"

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.get.side_effect = Exception("boom")
            result = json.loads(get_pr_details("owner", "repo", 1))
        assert "error" in result


class TestCreateGithubPr:
    def test_errors_without_token(self, monkeypatch):
        monkeypatch.delenv("SECRET_TOKEN_GITHUB", raising=False)
        result = json.loads(create_github_pr("owner", "repo", "T", "B", "feature"))
        assert result["success"] is False

    def test_creates_successfully(self, monkeypatch):
        monkeypatch.setenv("SECRET_TOKEN_GITHUB", "tok")
        with patch.object(tools_mod, "requests") as mock_requests:
            resp = MagicMock(status_code=201, content=b"{}")
            resp.json.return_value = {"number": 5, "html_url": "https://gh/5"}
            mock_requests.post.return_value = resp
            result = json.loads(create_github_pr("owner", "repo", "T", "B", "feature"))
        assert result["success"] is True
        assert result["pr_number"] == 5

    def test_reports_failure(self, monkeypatch):
        monkeypatch.setenv("SECRET_TOKEN_GITHUB", "tok")
        with patch.object(tools_mod, "requests") as mock_requests:
            resp = MagicMock(status_code=422, content=b"{}")
            resp.json.return_value = {"message": "already exists"}
            mock_requests.post.return_value = resp
            result = json.loads(create_github_pr("owner", "repo", "T", "B", "feature"))
        assert result["success"] is False


class TestDeleteGithubBranch:
    def test_errors_without_token(self, monkeypatch):
        monkeypatch.delenv("SECRET_TOKEN_GITHUB", raising=False)
        result = json.loads(delete_github_branch("owner", "repo", "old-branch"))
        assert result["success"] is False

    def test_deletes_successfully(self, monkeypatch):
        monkeypatch.setenv("SECRET_TOKEN_GITHUB", "tok")
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.delete.return_value = MagicMock(status_code=204)
            result = json.loads(delete_github_branch("owner", "repo", "old-branch"))
        assert result["success"] is True

    def test_returns_error_on_exception(self, monkeypatch):
        monkeypatch.setenv("SECRET_TOKEN_GITHUB", "tok")
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.delete.side_effect = Exception("down")
            result = json.loads(delete_github_branch("owner", "repo", "old-branch"))
        assert result["success"] is False


class TestCheckUrlStatus:
    def test_checks_a_plain_url_directly(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.get.return_value = MagicMock(status_code=200)
            result = json.loads(check_url_status("https://site/about"))
        assert result["ok"] is True
        assert result["checkedUrl"] == "https://site/about"

    def test_rewrites_post_urls_to_the_api(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.get.return_value = MagicMock(status_code=200)
            check_url_status("https://site/post/my-slug")
        called_url = mock_requests.get.call_args[0][0]
        assert "/api/posts/my-slug" in called_url

    def test_rewrites_story_urls_to_the_api(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.get.return_value = MagicMock(status_code=200)
            check_url_status("https://site/story/42")
        called_url = mock_requests.get.call_args[0][0]
        assert "/api/stories/42" in called_url

    def test_flags_404(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.get.return_value = MagicMock(status_code=404)
            result = json.loads(check_url_status("https://site/post/missing"))
        assert result["is404"] is True
        assert result["ok"] is False

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.get.side_effect = Exception("timeout")
            result = json.loads(check_url_status("https://site/x"))
        assert result["ok"] is False


class TestGenerateSitemap:
    def test_generates_a_sitemap_with_static_and_dynamic_urls(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        monkeypatch.setattr(tools_mod, "SERVER_BASE", "https://site")
        router_dir = tmp_path / "frontend/src/router"
        router_dir.mkdir(parents=True)
        (router_dir / "index.js").write_text("path: '/about'\npath: '/admin/dashboard'\npath: '/:slug'")

        with patch.object(tools_mod, "requests") as mock_requests:
            posts_resp = MagicMock(ok=True)
            posts_resp.json.return_value = {"posts": [{"slug": "hello", "status": "published"}]}
            stories_resp = MagicMock(ok=True)
            stories_resp.json.return_value = [{"id": 3}]
            mock_requests.get.side_effect = [posts_resp, stories_resp]
            result = json.loads(generate_sitemap())

        assert result["success"] is True
        assert "https://site/post/hello" in result["urls"]
        assert "https://site/story/3" in result["urls"]
        assert "https://site/about" in result["urls"]
        assert "https://site/admin/dashboard" not in result["urls"]
        sitemap_file = tmp_path / "frontend/public/sitemap.xml"
        assert sitemap_file.exists()

    def test_tolerates_missing_router_and_failed_fetches(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        monkeypatch.setattr(tools_mod, "SERVER_BASE", "https://site")
        with patch.object(tools_mod, "requests") as mock_requests:
            mock_requests.get.side_effect = Exception("down")
            result = json.loads(generate_sitemap())
        assert result["success"] is True
        assert result["urlCount"] == 3  # just the hardcoded static paths


class TestGetSitemapUrls:
    def test_reports_missing_sitemap(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        result = json.loads(get_sitemap_urls())
        assert result["exists"] is False

    def test_parses_existing_sitemap(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        sitemap_dir = tmp_path / "frontend/public"
        sitemap_dir.mkdir(parents=True)
        (sitemap_dir / "sitemap.xml").write_text(
            '<urlset><url><loc>https://site/a</loc></url><url><loc>https://site/b</loc></url></urlset>'
        )
        result = json.loads(get_sitemap_urls())
        assert result["count"] == 2
        assert "https://site/a" in result["urls"]
