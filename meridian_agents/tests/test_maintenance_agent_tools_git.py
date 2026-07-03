"""Tests for subprocess-based (git/npm/py_compile) tools in
maintenance_agent/tools.py. Every subprocess.run call is mocked — nothing
here executes a real git or npm command against this repository.
"""
import json
import subprocess
from unittest.mock import patch, MagicMock

from meridian_agents.maintenance_agent import tools as tools_mod
from meridian_agents.maintenance_agent.tools import (
    apply_file_patch,
    revert_file,
    build_nodejs_service,
    check_python_syntax,
    install_frontend_deps,
    run_frontend_build,
    git_diff_changes,
    git_status_short,
    git_pull_rebase,
    git_commit_and_push,
    get_github_repo,
    get_current_branch,
    git_checkout_branch,
    git_pull_main,
    git_stage_and_commit,
    git_push_current_branch,
)


def _proc(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


class TestApplyFilePatch:
    def test_rejects_path_traversal(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        result = json.loads(apply_file_patch("../../etc/passwd", "a", "b"))
        assert result["success"] is False
        assert "traversal" in result["error"]

    def test_reports_missing_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        result = json.loads(apply_file_patch("missing.txt", "a", "b"))
        assert result["success"] is False

    def test_reports_when_old_string_not_found(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        (tmp_path / "a.txt").write_text("hello world")
        result = json.loads(apply_file_patch("a.txt", "goodbye", "hi"))
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_reports_when_old_string_is_ambiguous(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        (tmp_path / "a.txt").write_text("foo foo foo")
        result = json.loads(apply_file_patch("a.txt", "foo", "bar"))
        assert result["success"] is False
        assert "unique" in result["error"]

    def test_replaces_a_unique_match(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        (tmp_path / "a.txt").write_text("hello world")
        result = json.loads(apply_file_patch("a.txt", "world", "there"))
        assert result["success"] is True
        assert (tmp_path / "a.txt").read_text() == "hello there"


class TestRevertFile:
    def test_rejects_path_traversal(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        result = json.loads(revert_file("../../etc/passwd"))
        assert result["success"] is False

    def test_reverts_successfully(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        (tmp_path / "a.txt").write_text("x")
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=0)) as mock_run:
            result = json.loads(revert_file("a.txt"))
        assert result["success"] is True
        assert mock_run.call_args[0][0][:3] == ["git", "checkout", "HEAD"]

    def test_reports_git_failure(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        (tmp_path / "a.txt").write_text("x")
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stderr="fatal: error", returncode=1)):
            result = json.loads(revert_file("a.txt"))
        assert result["success"] is False


class TestBuildNodejsService:
    def test_rejects_unknown_service(self):
        result = json.loads(build_nodejs_service("nope"))
        assert "error" in result

    def test_skips_when_npm_unavailable(self, monkeypatch):
        with patch("shutil.which", return_value=None):
            result = json.loads(build_nodejs_service("frontend"))
        assert result["verdict"] == "BUILD SKIPPED"

    def test_skips_when_directory_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/npm"):
            result = json.loads(build_nodejs_service("frontend"))
        assert result["verdict"] == "BUILD SKIPPED"

    def test_uses_npm_ci_when_lockfile_present(self, monkeypatch, tmp_path):
        svc_dir = tmp_path / "frontend"
        svc_dir.mkdir()
        (svc_dir / "package-lock.json").write_text("{}")
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/npm"), \
             patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=0)) as mock_run:
            result = json.loads(build_nodejs_service("frontend"))
        assert result["verdict"] == "BUILD PASSED"
        first_call_cmd = mock_run.call_args_list[0][0][0]
        assert first_call_cmd == ["npm", "ci"]

    def test_uses_npm_install_without_lockfile(self, monkeypatch, tmp_path):
        svc_dir = tmp_path / "frontend"
        svc_dir.mkdir()
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/npm"), \
             patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=0)) as mock_run:
            build_nodejs_service("frontend")
        first_call_cmd = mock_run.call_args_list[0][0][0]
        assert first_call_cmd == ["npm", "install"]

    def test_reports_install_failure(self, monkeypatch, tmp_path):
        svc_dir = tmp_path / "frontend"
        svc_dir.mkdir()
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/npm"), \
             patch.object(tools_mod.subprocess, "run", return_value=_proc(stderr="peer dep conflict", returncode=1)):
            result = json.loads(build_nodejs_service("frontend"))
        assert result["success"] is False
        assert result["verdict"] == "BUILD FAILED"

    def test_reports_build_failure(self, monkeypatch, tmp_path):
        svc_dir = tmp_path / "frontend"
        svc_dir.mkdir()
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/npm"), \
             patch.object(tools_mod.subprocess, "run", side_effect=[_proc(returncode=0), _proc(returncode=1, stderr="TS error")]):
            result = json.loads(build_nodejs_service("frontend"))
        assert result["success"] is False
        assert result["verdict"] == "BUILD FAILED"

    def test_handles_timeout(self, monkeypatch, tmp_path):
        svc_dir = tmp_path / "frontend"
        svc_dir.mkdir()
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/npm"), \
             patch.object(tools_mod.subprocess, "run", side_effect=subprocess.TimeoutExpired("npm", 300)):
            result = json.loads(build_nodejs_service("frontend"))
        assert result["verdict"] == "BUILD FAILED"


class TestCheckPythonSyntax:
    def test_reports_ok_for_valid_python(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        agents_dir = tmp_path / "meridian_agents"
        agents_dir.mkdir()
        (agents_dir / "good.py").write_text("x = 1\n")
        result = json.loads(check_python_syntax())
        assert result["verdict"] == "SYNTAX OK"
        assert result["checked"] == 1

    def test_reports_syntax_errors(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        agents_dir = tmp_path / "meridian_agents"
        agents_dir.mkdir()
        (agents_dir / "bad.py").write_text("def f(:\n")
        result = json.loads(check_python_syntax())
        assert result["verdict"] == "SYNTAX ERRORS FOUND"
        assert result["errorCount"] == 1

    def test_skips_pycache_directories(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        agents_dir = tmp_path / "meridian_agents"
        agents_dir.mkdir()
        pycache = agents_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.py").write_text("def f(:\n")  # would fail if scanned
        result = json.loads(check_python_syntax())
        assert result["checked"] == 0


class TestInstallFrontendDeps:
    def test_skips_when_npm_unavailable(self):
        with patch("shutil.which", return_value=None):
            result = json.loads(install_frontend_deps())
        assert result["success"] is False
        assert result["verdict"] == "SKIPPED"

    def test_installs_successfully(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/npm"), \
             patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=0, stdout="up to date")):
            result = json.loads(install_frontend_deps())
        assert result["success"] is True

    def test_handles_timeout(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/npm"), \
             patch.object(tools_mod.subprocess, "run", side_effect=subprocess.TimeoutExpired("npm", 300)):
            result = json.loads(install_frontend_deps())
        assert result["success"] is False

    def test_handles_exception(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/npm"), \
             patch.object(tools_mod.subprocess, "run", side_effect=Exception("boom")):
            result = json.loads(install_frontend_deps())
        assert result["success"] is False


class TestRunFrontendBuild:
    def test_skips_when_npm_unavailable(self):
        with patch("shutil.which", return_value=None):
            result = json.loads(run_frontend_build())
        assert result["verdict"] == "BUILD SKIPPED"

    def test_reports_build_passed(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/npm"), \
             patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=0)):
            result = json.loads(run_frontend_build())
        assert result["verdict"] == "BUILD PASSED"

    def test_reports_build_failed(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/npm"), \
             patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=1, stderr="error")):
            result = json.loads(run_frontend_build())
        assert result["verdict"] == "BUILD FAILED"

    def test_handles_timeout(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tools_mod, "REPO_ROOT", str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/npm"), \
             patch.object(tools_mod.subprocess, "run", side_effect=subprocess.TimeoutExpired("npm", 300)):
            result = json.loads(run_frontend_build())
        assert result["verdict"] == "BUILD FAILED"


class TestGitDiffChanges:
    def test_reports_clean_tree(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stdout="")):
            result = json.loads(git_diff_changes())
        assert result["diff"] == ""

    def test_reports_a_diff(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stdout="diff --git a b\n+x")):
            result = json.loads(git_diff_changes())
        assert "diff --git" in result["diff"]

    def test_truncates_large_diffs(self):
        big_diff = "x" * 20000
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stdout=big_diff)):
            result = json.loads(git_diff_changes())
        assert "truncated" in result["diff"]

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=Exception("boom")):
            result = json.loads(git_diff_changes())
        assert "error" in result


class TestGitStatusShort:
    def test_reports_clean_tree(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stdout="")):
            result = json.loads(git_status_short())
        assert "clean" in result["output"]

    def test_reports_changes(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stdout=" M file.txt")):
            result = json.loads(git_status_short())
        assert "file.txt" in result["output"]

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=Exception("boom")):
            result = json.loads(git_status_short())
        assert "error" in result


class TestGitPullRebase:
    def test_reports_success(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=0, stdout="Already up to date.")):
            result = json.loads(git_pull_rebase())
        assert result["success"] is True

    def test_reports_failure(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=1, stderr="conflict")):
            result = json.loads(git_pull_rebase())
        assert result["success"] is False

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=Exception("boom")):
            result = json.loads(git_pull_rebase())
        assert result["success"] is False


class TestGitCommitAndPush:
    def test_reports_nothing_to_commit(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stdout="")):
            result = json.loads(git_commit_and_push("msg"))
        assert result["success"] is False
        assert "Nothing to commit" in result["message"]

    def test_reports_add_failure(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=[_proc(stdout=" M a.txt"), _proc(returncode=1, stderr="add failed")]):
            result = json.loads(git_commit_and_push("msg"))
        assert result["success"] is False
        assert "git add" in result["error"]

    def test_reports_commit_failure(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=[
            _proc(stdout=" M a.txt"), _proc(returncode=0), _proc(returncode=1, stderr="nothing to commit"),
        ]):
            result = json.loads(git_commit_and_push("msg"))
        assert result["success"] is False
        assert "git commit" in result["error"]

    def test_commits_and_pushes_successfully(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=[
            _proc(stdout=" M a.txt"), _proc(returncode=0), _proc(returncode=0, stdout="commit ok"), _proc(returncode=0, stdout="push ok"),
        ]):
            result = json.loads(git_commit_and_push("msg"))
        assert result["success"] is True

    def test_reports_push_failure_after_successful_commit(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=[
            _proc(stdout=" M a.txt"), _proc(returncode=0), _proc(returncode=0, stdout="commit ok"), _proc(returncode=1, stderr="push rejected"),
        ]):
            result = json.loads(git_commit_and_push("msg"))
        assert result["success"] is False
        assert "Committed but push failed" in result["message"]

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=Exception("boom")):
            result = json.loads(git_commit_and_push("msg"))
        assert result["success"] is False


class TestGetGithubRepo:
    def test_returns_error_when_unset(self, monkeypatch):
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        result = json.loads(get_github_repo())
        assert "error" in result

    def test_parses_owner_and_repo(self, monkeypatch):
        monkeypatch.setenv("GITHUB_REPO", "bibhu2020/myblogs")
        result = json.loads(get_github_repo())
        assert result == {"owner": "bibhu2020", "repo": "myblogs", "full": "bibhu2020/myblogs"}


class TestGetCurrentBranch:
    def test_returns_the_branch_name(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=0, stdout="local\n")):
            result = json.loads(get_current_branch())
        assert result["branch"] == "local"
        assert result["success"] is True

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=Exception("boom")):
            result = json.loads(get_current_branch())
        assert "error" in result


class TestGitCheckoutBranch:
    def test_checks_out_an_existing_branch(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=0, stdout="Switched")) as mock_run:
            result = json.loads(git_checkout_branch("feature-x"))
        assert result["success"] is True
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["git", "checkout", "feature-x"]

    def test_creates_branch_from_main(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=0)) as mock_run:
            result = json.loads(git_checkout_branch("feature-x", create_from_main=True))
        assert result["success"] is True
        assert mock_run.call_count == 4  # stash, checkout main, pull, checkout -b

    def test_reports_failure_when_checkout_main_fails(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=[_proc(), _proc(returncode=1, stderr="fatal")]):
            result = json.loads(git_checkout_branch("feature-x", create_from_main=True))
        assert result["success"] is False

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=Exception("boom")):
            result = json.loads(git_checkout_branch("feature-x"))
        assert result["success"] is False


class TestGitPullMain:
    def test_syncs_successfully(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=0, stdout="up to date")):
            result = json.loads(git_pull_main())
        assert result["success"] is True

    def test_reports_failure(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(returncode=1, stderr="fatal")):
            result = json.loads(git_pull_main())
        assert result["success"] is False

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=Exception("boom")):
            result = json.loads(git_pull_main())
        assert result["success"] is False


class TestGitStageAndCommit:
    def test_reports_nothing_to_commit(self):
        with patch.object(tools_mod.subprocess, "run", return_value=_proc(stdout="")):
            result = json.loads(git_stage_and_commit("msg"))
        assert result["success"] is False

    def test_reports_add_failure(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=[_proc(stdout=" M a.txt"), _proc(returncode=1, stderr="fail")]):
            result = json.loads(git_stage_and_commit("msg"))
        assert result["success"] is False
        assert "git add failed" in result["error"]

    def test_commits_successfully(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=[_proc(stdout=" M a.txt"), _proc(returncode=0), _proc(returncode=0, stdout="ok")]):
            result = json.loads(git_stage_and_commit("msg"))
        assert result["success"] is True

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=Exception("boom")):
            result = json.loads(git_stage_and_commit("msg"))
        assert result["success"] is False


class TestGitPushCurrentBranch:
    def test_pushes_successfully(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=[_proc(stdout="local\n"), _proc(returncode=0, stdout="pushed")]):
            result = json.loads(git_push_current_branch())
        assert result["success"] is True
        assert result["branch"] == "local"

    def test_reports_push_failure(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=[_proc(stdout="local\n"), _proc(returncode=1, stderr="rejected")]):
            result = json.loads(git_push_current_branch())
        assert result["success"] is False

    def test_returns_error_on_exception(self):
        with patch.object(tools_mod.subprocess, "run", side_effect=Exception("boom")):
            result = json.loads(git_push_current_branch())
        assert result["success"] is False
