import runpy
from unittest.mock import patch

import pytest


class TestDunderMain:
    def test_runs_rebranding_successfully(self):
        with patch("meridian_agents.rebranding_agent.main.run_rebranding") as mock_run:
            runpy.run_module("meridian_agents.rebranding_agent.__main__", run_name="__main__")
        mock_run.assert_called_once()

    def test_exits_with_error_code_on_failure(self):
        with patch(
            "meridian_agents.rebranding_agent.main.run_rebranding",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                runpy.run_module("meridian_agents.rebranding_agent.__main__", run_name="__main__")
        assert exc_info.value.code == 1
