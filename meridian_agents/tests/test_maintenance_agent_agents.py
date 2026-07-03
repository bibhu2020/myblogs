"""Tests for maintenance_agent/agents.py: _make_client, _run_agent, _extract_findings,
and run_team's phase-skipping/aggregation logic (with _run_agent fully mocked so no
real LLM calls or autogen team execution ever happens).
"""
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from meridian_agents.maintenance_agent import agents as agents_mod
from meridian_agents.maintenance_agent.agents import (
    _make_client,
    _run_agent,
    _extract_findings,
    run_team,
)


class TestMakeClient:
    # _GOOGLE_API_KEY is a module-level constant resolved once at import time
    # from the real environment, so tests must patch the module attribute
    # directly rather than the underlying env vars.

    def test_uses_gemini_when_google_api_key_present(self, monkeypatch):
        monkeypatch.setattr(agents_mod, "_GOOGLE_API_KEY", "g-key")
        with patch.object(agents_mod, "OpenAIChatCompletionClient") as mock_cls:
            _make_client()
        _, kwargs = mock_cls.call_args
        assert kwargs["api_key"] == "g-key"
        assert "generativelanguage" in kwargs["base_url"]

    def test_falls_back_to_known_openai_model_without_google_key(self, monkeypatch):
        monkeypatch.setattr(agents_mod, "_GOOGLE_API_KEY", None)
        monkeypatch.setenv("MAINTENANCE_MODEL", "gpt-4o-mini")
        with patch.object(agents_mod, "OpenAIChatCompletionClient") as mock_cls:
            _make_client()
        mock_cls.assert_called_once_with(model="gpt-4o-mini")

    def test_falls_back_to_unknown_openai_model_with_model_info(self, monkeypatch):
        monkeypatch.setattr(agents_mod, "_GOOGLE_API_KEY", None)
        monkeypatch.setenv("MAINTENANCE_MODEL", "some-custom-model")
        with patch.object(agents_mod, "OpenAIChatCompletionClient") as mock_cls:
            _make_client()
        _, kwargs = mock_cls.call_args
        assert kwargs["model"] == "some-custom-model"
        assert kwargs["model_info"]["family"] == "gpt-4o"

    def test_defaults_to_gpt4o_mini_when_no_model_env_set(self, monkeypatch):
        monkeypatch.setattr(agents_mod, "_GOOGLE_API_KEY", None)
        monkeypatch.delenv("MAINTENANCE_MODEL", raising=False)
        with patch.object(agents_mod, "OpenAIChatCompletionClient") as mock_cls:
            _make_client()
        mock_cls.assert_called_once_with(model="gpt-4o-mini")


class TestExtractFindings:
    def test_extracts_a_count_and_kind(self):
        findings = _extract_findings("Found 3 issues in the sitemap scan.", "sitemap")
        assert findings == [{
            "area": "sitemap",
            "severity": "info",
            "message": "3 issue(s) found in sitemap phase",
            "detail": "Found 3 issues in the sitemap scan.",
        }]

    def test_returns_empty_list_when_count_is_zero(self):
        assert _extract_findings("0 problems found.", "seo_ada") == []

    def test_returns_empty_list_when_no_match(self):
        assert _extract_findings("Everything looks great!", "build") == []


class TestRunAgent:
    def test_returns_the_last_text_message_before_task_result(self):
        from autogen_agentchat.base import TaskResult

        msg1 = MagicMock(content="first", source="agent")
        msg2 = MagicMock(content="  ", source="agent")  # blank/whitespace, skipped
        msg3 = MagicMock(content="final answer", source="agent")
        result = TaskResult(messages=[], stop_reason="done")

        async def fake_stream(task):
            for m in (msg1, msg2, msg3, result):
                yield m

        fake_team = MagicMock()
        fake_team.run_stream = fake_stream

        with patch.object(agents_mod, "RoundRobinGroupChat", return_value=fake_team):
            output = asyncio.run(_run_agent(MagicMock(), "do the task"))
        assert output == "final answer"

    def test_returns_empty_string_when_no_content_messages(self):
        from autogen_agentchat.base import TaskResult

        result = TaskResult(messages=[], stop_reason="done")

        async def fake_stream(task):
            yield result

        fake_team = MagicMock()
        fake_team.run_stream = fake_stream

        with patch.object(agents_mod, "RoundRobinGroupChat", return_value=fake_team):
            output = asyncio.run(_run_agent(MagicMock(), "do the task"))
        assert output == ""


class TestRunTeam:
    def _patch_common(self):
        return patch.object(agents_mod, "_make_client", return_value=MagicMock())

    def test_skips_dependabot_phase_without_github_repo(self, monkeypatch):
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        with self._patch_common(), \
             patch.object(agents_mod, "AssistantAgent", return_value=MagicMock()), \
             patch.object(agents_mod, "_run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "0 issues found."
            summary, findings = asyncio.run(run_team("/repo", "https://example.com"))
        assert "Skipped — GITHUB_REPO not configured" in summary
        # 3 phases run (sitemap, seo_ada, build) since dependabot is skipped
        assert mock_run.call_count == 3

    def test_runs_dependabot_phase_when_github_repo_set(self, monkeypatch):
        monkeypatch.setenv("GITHUB_REPO", "owner/repo")
        with self._patch_common(), \
             patch.object(agents_mod, "AssistantAgent", return_value=MagicMock()), \
             patch.object(agents_mod, "_run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Merged: 2 | Skipped (non-Dependabot): 1"
            summary, findings = asyncio.run(run_team("/repo", "https://example.com"))
        assert "Phase 1 (Dependabot)" in summary
        assert mock_run.call_count == 4

    def test_aggregates_findings_across_phases(self, monkeypatch):
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        with self._patch_common(), \
             patch.object(agents_mod, "AssistantAgent", return_value=MagicMock()), \
             patch.object(agents_mod, "_run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Found 5 issues during the audit."
            summary, findings = asyncio.run(run_team("/repo", "https://example.com"))
        assert len(findings) == 3
        assert all(f["message"] == "5 issue(s) found in " + f["area"] + " phase" for f in findings)
