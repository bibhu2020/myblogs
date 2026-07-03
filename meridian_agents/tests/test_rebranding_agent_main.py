"""Tests for rebranding_agent/main.py: _make_model, _detect_repo_root,
_run_pipeline, run_rebranding. Runner.run and asyncio are always mocked —
no real LLM calls, subprocess git calls only via mocked subprocess.run.
"""
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from meridian_agents.rebranding_agent import main as main_mod
from meridian_agents.rebranding_agent.main import (
    _make_model,
    _detect_repo_root,
    _run_pipeline,
    run_rebranding,
)


class TestMakeModel:
    def test_builds_a_gemini_model_when_google_api_key_present(self, monkeypatch):
        monkeypatch.setattr(main_mod, "_GOOGLE_API_KEY", "g-key")
        with patch("agents.models.openai_chatcompletions.OpenAIChatCompletionsModel") as mock_model_cls, \
             patch("openai.AsyncOpenAI") as mock_client_cls:
            _make_model()
        mock_client_cls.assert_called_once_with(api_key="g-key", base_url=main_mod._GEMINI_BASE_URL)
        mock_model_cls.assert_called_once()

    def test_falls_back_to_gpt4o_mini_string_without_google_key(self, monkeypatch):
        monkeypatch.setattr(main_mod, "_GOOGLE_API_KEY", None)
        assert _make_model() == "gpt-4o-mini"


class TestDetectRepoRoot:
    def test_uses_github_workspace_when_set(self, monkeypatch):
        monkeypatch.setenv("GITHUB_WORKSPACE", "/gha/workspace")
        assert _detect_repo_root() == "/gha/workspace"

    def test_falls_back_to_repo_root_env_var(self, monkeypatch):
        monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
        monkeypatch.setenv("REPO_ROOT", "/manual/root")
        assert _detect_repo_root() == "/manual/root"

    def test_falls_back_to_git_rev_parse(self, monkeypatch):
        monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
        monkeypatch.delenv("REPO_ROOT", raising=False)
        with patch.object(main_mod.subprocess, "run", return_value=MagicMock(returncode=0, stdout="/git/root\n")):
            assert _detect_repo_root() == "/git/root"

    def test_raises_when_nothing_available(self, monkeypatch):
        monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
        monkeypatch.delenv("REPO_ROOT", raising=False)
        with patch.object(main_mod.subprocess, "run", return_value=MagicMock(returncode=128, stdout="")):
            with pytest.raises(RuntimeError, match="Cannot find repo root"):
                _detect_repo_root()


class TestRunPipeline:
    def test_returns_the_final_output(self):
        with patch.object(main_mod, "_make_model", return_value="gpt-4o-mini"), \
             patch.object(main_mod, "build_pipeline", return_value=MagicMock()), \
             patch.object(main_mod.Runner, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = MagicMock(final_output="Pipeline complete.")
            result = asyncio.run(_run_pipeline("/repo", False))
        assert result == "Pipeline complete."

    def test_falls_back_to_placeholder_when_no_output(self):
        with patch.object(main_mod, "_make_model", return_value="gpt-4o-mini"), \
             patch.object(main_mod, "build_pipeline", return_value=MagicMock()), \
             patch.object(main_mod.Runner, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = MagicMock(final_output=None)
            result = asyncio.run(_run_pipeline("/repo", True))
        assert result == "(no output)"


class TestRunRebranding:
    def test_raises_without_any_api_key(self, monkeypatch):
        monkeypatch.setattr(main_mod, "_GOOGLE_API_KEY", None)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="No LLM API key found"):
            run_rebranding()

    def test_completes_successfully_and_marks_run_completed(self, monkeypatch):
        monkeypatch.setattr(main_mod, "_GOOGLE_API_KEY", "g-key")
        with patch.object(main_mod, "_detect_repo_root", return_value="/repo"), \
             patch.object(main_mod, "start_run", return_value="run-1") as mock_start, \
             patch.object(main_mod, "asyncio") as mock_asyncio, \
             patch.object(main_mod, "complete_run") as mock_complete:
            mock_asyncio.run.return_value = "Rebrand shipped successfully."
            run_rebranding()
        mock_start.assert_called_once()
        mock_complete.assert_called_once_with("run-1", "Rebrand shipped successfully.", failed=False)

    def test_marks_run_failed_when_summary_mentions_a_build_failure(self, monkeypatch):
        monkeypatch.setattr(main_mod, "_GOOGLE_API_KEY", "g-key")
        with patch.object(main_mod, "_detect_repo_root", return_value="/repo"), \
             patch.object(main_mod, "start_run", return_value="run-1"), \
             patch.object(main_mod, "asyncio") as mock_asyncio, \
             patch.object(main_mod, "complete_run") as mock_complete:
            mock_asyncio.run.return_value = "Phase 4: BUILD FAILED in tester."
            run_rebranding()
        mock_complete.assert_called_once_with("run-1", "Phase 4: BUILD FAILED in tester.", failed=True)

    def test_marks_run_failed_and_reraises_on_exception(self, monkeypatch):
        monkeypatch.setattr(main_mod, "_GOOGLE_API_KEY", "g-key")
        with patch.object(main_mod, "_detect_repo_root", return_value="/repo"), \
             patch.object(main_mod, "start_run", return_value="run-1"), \
             patch.object(main_mod, "asyncio") as mock_asyncio, \
             patch.object(main_mod, "complete_run") as mock_complete:
            mock_asyncio.run.side_effect = RuntimeError("pipeline crashed hard")
            with pytest.raises(RuntimeError, match="pipeline crashed hard"):
                run_rebranding()
        mock_complete.assert_called_once_with("run-1", "Pipeline crashed: pipeline crashed hard", failed=True)
