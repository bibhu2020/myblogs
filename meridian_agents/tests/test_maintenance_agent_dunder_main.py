"""Tests for maintenance_agent/__main__.py.

SAFETY NOTE: the 'schedule' branch of __main__.py contains a `while True` loop
with no built-in exit condition (it's meant to run forever until Ctrl+C). To
exercise it without ever actually hanging or sleeping in real time, every test
that enters the loop mocks time.sleep to raise a sentinel exception after a
fixed, small number of calls — this deterministically unwinds the loop via
pytest.raises rather than relying on real timing. No test lets the loop run
unbounded, and run_maintenance is always mocked so no real maintenance pipeline
(and no real subprocess/git/network calls) ever executes.
"""
import runpy
import sys
from unittest.mock import patch

import pytest


class _StopLoop(Exception):
    """Sentinel used to deterministically break out of the scheduler's while True loop."""


class TestNonScheduleMode:
    def test_runs_maintenance_successfully(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["maintenance_agent"])
        with patch("meridian_agents.maintenance_agent.main.run_maintenance") as mock_run:
            runpy.run_module("meridian_agents.maintenance_agent.__main__", run_name="__main__")
        mock_run.assert_called_once()

    def test_exits_with_error_code_on_failure(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["maintenance_agent"])
        with patch(
            "meridian_agents.maintenance_agent.main.run_maintenance",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                runpy.run_module("meridian_agents.maintenance_agent.__main__", run_name="__main__")
        assert exc_info.value.code == 1


class TestScheduleModeValidation:
    def test_requires_a_cron_expression_argument(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["maintenance_agent", "schedule"])
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("meridian_agents.maintenance_agent.__main__", run_name="__main__")
        assert exc_info.value.code == 1

    def test_rejects_an_invalid_cron_expression(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["maintenance_agent", "schedule", "not-a-cron"])
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("meridian_agents.maintenance_agent.__main__", run_name="__main__")
        assert exc_info.value.code == 1


class TestScheduleModeLoop:
    def test_computes_next_run_and_sleeps(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["maintenance_agent", "schedule", "0 0 1 * *"])
        with patch("meridian_agents.maintenance_agent.main.run_maintenance"), \
             patch("time.sleep", side_effect=_StopLoop):
            with pytest.raises(_StopLoop):
                runpy.run_module("meridian_agents.maintenance_agent.__main__", run_name="__main__")

    def test_runs_maintenance_then_loops_again(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["maintenance_agent", "schedule", "0 0 1 * *"])
        # First sleep call is a no-op (lets the loop proceed into run_maintenance),
        # second sleep call raises — bounding execution to exactly one full iteration.
        with patch("meridian_agents.maintenance_agent.main.run_maintenance") as mock_run, \
             patch("time.sleep", side_effect=[None, _StopLoop()]):
            with pytest.raises(_StopLoop):
                runpy.run_module("meridian_agents.maintenance_agent.__main__", run_name="__main__")
        mock_run.assert_called_once()

    def test_catches_and_reports_run_maintenance_failure_then_continues(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["maintenance_agent", "schedule", "0 0 1 * *"])
        with patch(
            "meridian_agents.maintenance_agent.main.run_maintenance",
            side_effect=RuntimeError("scheduled run boom"),
        ), patch("time.sleep", side_effect=[None, _StopLoop()]):
            with pytest.raises(_StopLoop):
                runpy.run_module("meridian_agents.maintenance_agent.__main__", run_name="__main__")
        assert "Scheduled run failed: scheduled run boom" in capsys.readouterr().out
