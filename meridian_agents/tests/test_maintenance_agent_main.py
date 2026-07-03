"""Tests for maintenance_agent/main.py (run_maintenance).

No test in this file ever calls asyncio.run(run_team(...)) for real — run_team
is always mocked, so no LLM calls or subprocess/git commands are made.
"""
from unittest.mock import patch

import pytest

from meridian_agents.maintenance_agent import main as main_mod
from meridian_agents.maintenance_agent.main import run_maintenance


class TestRunMaintenance:
    def test_raises_without_openai_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            run_maintenance()

    def test_completes_successfully(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "key")
        with patch.object(main_mod, "start_run", return_value="run-1") as mock_start, \
             patch.object(main_mod, "asyncio") as mock_asyncio, \
             patch.object(main_mod, "complete_run") as mock_complete:
            mock_asyncio.run.return_value = ("did stuff", [{"area": "build"}])
            run_maintenance()
        mock_start.assert_called_once()
        mock_complete.assert_called_once_with("run-1", "did stuff", [{"area": "build"}])

    def test_marks_run_failed_and_reraises_on_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "key")
        with patch.object(main_mod, "start_run", return_value="run-1"), \
             patch.object(main_mod, "asyncio") as mock_asyncio, \
             patch.object(main_mod, "complete_run") as mock_complete:
            mock_asyncio.run.side_effect = RuntimeError("pipeline exploded")
            with pytest.raises(RuntimeError, match="pipeline exploded"):
                run_maintenance()
        mock_complete.assert_called_once_with("run-1", "pipeline exploded", [], failed=True)
