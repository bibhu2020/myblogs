from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from meridian_agents.news_agent import main as main_mod
from meridian_agents.news_agent.main import (
    _build_agent,
    _gather_articles,
    _run,
    run_news_agent,
)


class TestBuildAgent:
    def test_raises_without_gemini_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            _build_agent()

    def test_builds_an_agent_with_the_save_news_tool(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        agent = _build_agent()
        assert agent.name == "MeridianNewsAgent"
        assert agent.tools == [main_mod.save_news]


class TestGatherArticles:
    def test_aggregates_articles_across_all_regions(self):
        with patch.object(main_mod, "fetch_region_news", side_effect=lambda region, **kw: [{"region": region}]) as mock_fetch:
            articles = _gather_articles()
        assert mock_fetch.call_count == len(main_mod._REGIONS)
        assert len(articles) == len(main_mod._REGIONS)
        assert {a["region"] for a in articles} == set(main_mod._REGIONS)


class TestRun:
    def test_returns_the_final_output(self):
        import asyncio
        with patch.object(main_mod, "_build_agent", return_value=MagicMock()), \
             patch.object(main_mod.Runner, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = MagicMock(final_output="16 stories saved.")
            result = asyncio.run(_run([{"title": "A"}]))
        assert result == "16 stories saved."

    def test_falls_back_to_placeholder_when_no_output(self):
        import asyncio
        with patch.object(main_mod, "_build_agent", return_value=MagicMock()), \
             patch.object(main_mod.Runner, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = MagicMock(final_output=None)
            result = asyncio.run(_run([]))
        assert result == "(no output)"


class TestRunNewsAgent:
    def test_completes_successfully(self):
        with patch.object(main_mod, "start_run", return_value="run-1") as mock_start, \
             patch.object(main_mod, "_gather_articles", return_value=[{"title": "A"}]), \
             patch.object(main_mod, "asyncio") as mock_asyncio, \
             patch.object(main_mod, "complete_run") as mock_complete:
            mock_asyncio.run.return_value = "Saved 16 stories."
            run_news_agent()
        mock_start.assert_called_once()
        mock_complete.assert_called_once_with("run-1", "Saved 16 stories.")

    def test_marks_run_failed_and_reraises_on_error(self):
        with patch.object(main_mod, "start_run", return_value="run-1"), \
             patch.object(main_mod, "_gather_articles", side_effect=RuntimeError("feed fetch failed")), \
             patch.object(main_mod, "complete_run") as mock_complete:
            with pytest.raises(RuntimeError, match="feed fetch failed"):
                run_news_agent()
        mock_complete.assert_called_once_with("run-1", "feed fetch failed", failed=True)
