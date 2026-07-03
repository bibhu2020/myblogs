import runpy
import sys
from unittest.mock import patch

import pytest


def _run_main(argv):
    with patch.object(sys, "argv", ["prog"] + argv):
        runpy.run_module("meridian_agents.story_agent.__main__", run_name="__main__")


class TestApproveCommand:
    def test_requires_a_story_id(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            _run_main(["approve"])
        assert exc_info.value.code == 1
        assert "Usage" in capsys.readouterr().out

    def test_approves_successfully(self):
        with patch("meridian_agents.story_agent.main.approve_story") as mock_approve:
            _run_main(["approve", "7"])
        mock_approve.assert_called_once_with(7)

    def test_exits_nonzero_when_approve_raises(self, capsys):
        with patch("meridian_agents.story_agent.main.approve_story", side_effect=Exception("boom")):
            with pytest.raises(SystemExit) as exc_info:
                _run_main(["approve", "7"])
        assert exc_info.value.code == 1
        assert "Approve failed" in capsys.readouterr().err


class TestRejectCommand:
    def test_requires_a_story_id(self):
        with pytest.raises(SystemExit):
            _run_main(["reject"])

    def test_rejects_successfully(self):
        with patch("meridian_agents.story_agent.main.reject_story") as mock_reject:
            _run_main(["reject", "7"])
        mock_reject.assert_called_once_with(7)

    def test_exits_nonzero_when_reject_raises(self):
        with patch("meridian_agents.story_agent.main.reject_story", side_effect=Exception("boom")):
            with pytest.raises(SystemExit):
                _run_main(["reject", "7"])


class TestPendingCommand:
    def test_lists_pending_stories(self):
        with patch("meridian_agents.story_agent.main.list_pending") as mock_list:
            _run_main(["pending"])
        mock_list.assert_called_once()


class TestScheduleCommand:
    # Loop body intentionally not exercised — see post_agent's equivalent test
    # for why: no pytest-timeout safety net is installed in this environment.
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
        with patch("meridian_agents.story_agent.main.run_agent") as mock_run:
            _run_main([])
        mock_run.assert_called_once()

    def test_exits_nonzero_when_run_agent_raises(self, capsys):
        with patch("meridian_agents.story_agent.main.run_agent", side_effect=Exception("boom")):
            with pytest.raises(SystemExit) as exc_info:
                _run_main([])
        assert exc_info.value.code == 1
        assert "Story agent failed" in capsys.readouterr().err
