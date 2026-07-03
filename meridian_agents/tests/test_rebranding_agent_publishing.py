"""Tests for rebranding_agent/tools/publishing.py: revert_changes, commit_and_push.

`run` (imported from _helpers into this module's namespace) is always mocked
— no real git commands ever execute against this repository.
"""
import asyncio
import json
from unittest.mock import patch, MagicMock

from agents.tool_context import ToolContext

from meridian_agents.rebranding_agent.context import RebrandCtx
from meridian_agents.rebranding_agent.tools import publishing as publishing_mod
from meridian_agents.rebranding_agent.tools.publishing import (
    revert_changes,
    commit_and_push,
)


def _invoke(tool, ctx: RebrandCtx, **kwargs):
    tc = ToolContext(context=ctx, tool_name=tool.name, tool_call_id="1", tool_arguments="{}")
    return asyncio.run(tool.on_invoke_tool(tc, json.dumps(kwargs)))


def _proc(stdout="", stderr="", returncode=0):
    return MagicMock(stdout=stdout, stderr=stderr, returncode=returncode)


class TestRevertChanges:
    def test_reverts_and_clears_files_changed(self):
        ctx = RebrandCtx(repo_root="/repo", files_changed=["a.txt", "b.txt"])
        with patch.object(publishing_mod, "run", return_value=_proc()) as mock_run:
            result = _invoke(revert_changes, ctx)
        mock_run.assert_called_once_with(["git", "checkout", "--", "."], cwd="/repo")
        assert ctx.files_changed == []
        assert "Reverted" in result


class TestCommitAndPush:
    def test_reports_nothing_to_commit(self):
        ctx = RebrandCtx(repo_root="/repo", chosen_theme="Winter")
        with patch.object(publishing_mod, "run", return_value=_proc(stdout="")):
            result = _invoke(commit_and_push, ctx)
        assert "Nothing to commit" in result

    def test_reports_commit_failure(self):
        ctx = RebrandCtx(repo_root="/repo", chosen_theme="Winter")
        responses = [
            _proc(),  # config user.name
            _proc(),  # config user.email
            _proc(),  # add -A
            _proc(stdout=" M a.txt"),  # status --porcelain
            _proc(returncode=1, stderr="commit failed: hook rejected"),  # commit
        ]
        with patch.object(publishing_mod, "run", side_effect=responses):
            result = _invoke(commit_and_push, ctx)
        assert "ERROR: git commit failed" in result

    def test_commits_and_pushes_successfully(self):
        responses = [
            _proc(),  # config user.name
            _proc(),  # config user.email
            _proc(),  # add -A
            _proc(stdout=" M a.txt"),  # status --porcelain
            _proc(returncode=0),  # commit
            _proc(stdout="abc1234"),  # rev-parse --short HEAD
            _proc(returncode=0),  # pull --rebase
            _proc(returncode=0),  # push
        ]
        ctx = RebrandCtx(repo_root="/repo", chosen_theme="Winter")
        with patch.object(publishing_mod, "run", side_effect=responses):
            result = _invoke(commit_and_push, ctx)
        assert "Pushed successfully" in result
        assert "abc1234" in result

    def test_reports_push_failure_after_successful_commit_and_masks_token(self):
        responses = [
            _proc(),  # config user.name
            _proc(),  # config user.email
            _proc(),  # add -A
            _proc(stdout=" M a.txt"),  # status --porcelain
            _proc(returncode=0),  # commit
            _proc(stdout="abc1234"),  # rev-parse --short HEAD
            _proc(returncode=0),  # pull --rebase
            _proc(returncode=1, stderr="remote: github_pat_ABC123secret rejected"),  # push
        ]
        ctx = RebrandCtx(repo_root="/repo", chosen_theme="Winter")
        with patch.object(publishing_mod, "run", side_effect=responses):
            result = _invoke(commit_and_push, ctx)
        assert "push failed" in result
        assert "github_pat_" not in result
        assert "***TOKEN***" in result

    def test_continues_when_pull_rebase_warns(self, capsys):
        responses = [
            _proc(),  # config user.name
            _proc(),  # config user.email
            _proc(),  # add -A
            _proc(stdout=" M a.txt"),  # status --porcelain
            _proc(returncode=0),  # commit
            _proc(stdout="abc1234"),  # rev-parse --short HEAD
            _proc(returncode=1, stderr="conflict during rebase"),  # pull --rebase warning
            _proc(returncode=0),  # push
        ]
        ctx = RebrandCtx(repo_root="/repo", chosen_theme="Winter")
        with patch.object(publishing_mod, "run", side_effect=responses):
            result = _invoke(commit_and_push, ctx)
        assert "Pushed successfully" in result
