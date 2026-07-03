import runpy
from unittest.mock import patch


def test_runs_the_news_agent_when_invoked_as_main():
    with patch("meridian_agents.news_agent.main.run_news_agent") as mock_run:
        runpy.run_module("meridian_agents.news_agent.__main__", run_name="__main__")
    mock_run.assert_called_once()
