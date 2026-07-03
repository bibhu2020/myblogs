import runpy
import sys
from unittest.mock import patch

import pytest


def _run_main(argv):
    """Execute post_agent/__main__.py as if invoked via `python -m ...`, with
    the given argv. The module has real top-level side effects (no `if
    __name__` guard needed since it's __main__.py), so each invocation must
    reimport it fresh via runpy rather than plain `import`.
    """
    with patch.object(sys, "argv", ["prog"] + argv):
        runpy.run_module("meridian_agents.post_agent.__main__", run_name="__main__")


class TestApproveCommand:
    def test_requires_a_post_id(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            _run_main(["approve"])
        assert exc_info.value.code == 1
        assert "Usage" in capsys.readouterr().out

    def test_approves_successfully(self):
        with patch("meridian_agents.post_agent.main.approve_post") as mock_approve:
            _run_main(["approve", "42"])
        mock_approve.assert_called_once_with(42)

    def test_exits_nonzero_when_approve_raises(self, capsys):
        with patch("meridian_agents.post_agent.main.approve_post", side_effect=Exception("boom")):
            with pytest.raises(SystemExit) as exc_info:
                _run_main(["approve", "42"])
        assert exc_info.value.code == 1
        assert "Approve failed" in capsys.readouterr().err


class TestRejectCommand:
    def test_requires_a_post_id(self):
        with pytest.raises(SystemExit) as exc_info:
            _run_main(["reject"])
        assert exc_info.value.code == 1

    def test_rejects_successfully(self):
        with patch("meridian_agents.post_agent.main.reject_post") as mock_reject:
            _run_main(["reject", "42"])
        mock_reject.assert_called_once_with(42)

    def test_exits_nonzero_when_reject_raises(self):
        with patch("meridian_agents.post_agent.main.reject_post", side_effect=Exception("boom")):
            with pytest.raises(SystemExit):
                _run_main(["reject", "42"])


class TestPendingCommand:
    def test_lists_pending_posts(self):
        with patch("meridian_agents.post_agent.main.list_pending") as mock_list:
            _run_main(["pending"])
        mock_list.assert_called_once()


class TestRegistryRemoveCommand:
    # The file-manipulation branch resolves its target path directly from
    # __main__.py's own __file__ (not a monkeypatchable module constant like
    # main.py's _PENDING_FILE), and that file already holds real agent data
    # in this repo. Redirecting it safely would mean patching pathlib.Path
    # globally, which is too invasive for the payoff — so only the safe,
    # file-free validation guard is exercised here.
    def test_requires_a_post_id(self):
        with pytest.raises(SystemExit) as exc_info:
            _run_main(["registry-remove"])
        assert exc_info.value.code == 1


class TestScheduleCommand:
    # Only the file-free, no-loop validation guards are exercised here. The
    # `while True` scheduler body itself is deliberately not driven directly:
    # there's no pytest-timeout installed in this environment, so any gap in
    # mocking time.sleep/croniter would hang the suite indefinitely with no
    # safety net — not an acceptable trade for a handful of extra lines.
    def test_requires_a_cron_expression(self):
        with pytest.raises(SystemExit) as exc_info:
            _run_main(["schedule"])
        assert exc_info.value.code == 1

    def test_rejects_an_invalid_cron_expression(self):
        with pytest.raises(SystemExit) as exc_info:
            _run_main(["schedule", "not a cron expr"])
        assert exc_info.value.code == 1


class TestGenerateCommand:
    def test_runs_the_agent_by_default(self):
        with patch("meridian_agents.post_agent.main.run_agent") as mock_run:
            _run_main([])
        mock_run.assert_called_once()

    def test_exits_nonzero_when_run_agent_raises(self, capsys):
        with patch("meridian_agents.post_agent.main.run_agent", side_effect=Exception("boom")):
            with pytest.raises(SystemExit) as exc_info:
                _run_main([])
        assert exc_info.value.code == 1
        assert "Agent failed" in capsys.readouterr().err
