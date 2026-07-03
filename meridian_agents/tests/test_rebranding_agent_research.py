"""Tests for rebranding_agent/tools/research.py: check_schedule,
research_world_events. subprocess.run and the OpenAI client are always
mocked — no real date-shell calls or API calls.
"""
import asyncio
import json
from unittest.mock import patch, MagicMock

from agents.tool_context import ToolContext

from meridian_agents.rebranding_agent.context import RebrandCtx
from meridian_agents.rebranding_agent.tools import research as research_mod
from meridian_agents.rebranding_agent.tools.research import (
    check_schedule,
    research_world_events,
)


def _invoke(tool, ctx: RebrandCtx, **kwargs):
    tc = ToolContext(context=ctx, tool_name=tool.name, tool_call_id="1", tool_arguments="{}")
    return asyncio.run(tool.on_invoke_tool(tc, json.dumps(kwargs)))


def _proc(stdout=""):
    return MagicMock(stdout=stdout)


class TestCheckSchedule:
    def test_proceeds_when_force_rebrand_is_set(self):
        ctx = RebrandCtx(repo_root="/repo", force_rebrand=True)
        with patch.object(research_mod.subprocess, "run") as mock_run:
            result = _invoke(check_schedule, ctx)
        assert result.startswith("PROCEED")
        mock_run.assert_not_called()

    def test_proceeds_on_the_first_sunday_window(self):
        ctx = RebrandCtx(repo_root="/repo")
        with patch.object(research_mod.subprocess, "run", return_value=_proc("03\n")):
            result = _invoke(check_schedule, ctx)
        assert result.startswith("PROCEED")
        assert "day 03" in result

    def test_skips_after_day_seven(self):
        ctx = RebrandCtx(repo_root="/repo")
        with patch.object(research_mod.subprocess, "run", return_value=_proc("15\n")):
            result = _invoke(check_schedule, ctx)
        assert result.startswith("SKIP")

    def test_falls_back_to_utcnow_when_date_command_fails(self):
        ctx = RebrandCtx(repo_root="/repo")
        with patch.object(research_mod.subprocess, "run", side_effect=Exception("no date binary")):
            result = _invoke(check_schedule, ctx)
        assert result.startswith("PROCEED") or result.startswith("SKIP")


class TestResearchWorldEvents:
    def test_populates_context_from_a_valid_response(self):
        ctx = RebrandCtx(repo_root="/repo")
        client = MagicMock()
        classification = json.dumps({
            "chosen_theme": "Lunar New Year",
            "mood": "celebratory",
            "events_summary": "Celebrations across Asia.",
        })
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=classification))]
        )
        with patch.object(research_mod, "OpenAI", return_value=client), \
             patch.object(research_mod, "web_search", return_value="raw search text"):
            result = _invoke(research_world_events, ctx)
        assert ctx.chosen_theme == "Lunar New Year"
        assert ctx.mood == "celebratory"
        assert ctx.world_events == "Celebrations across Asia."
        assert "Lunar New Year" in result

    def test_defaults_to_neutral_mood_when_classification_is_invalid(self):
        ctx = RebrandCtx(repo_root="/repo")
        client = MagicMock()
        classification = json.dumps({
            "chosen_theme": "Some theme",
            "mood": "excited",  # not one of the three valid moods
            "events_summary": "summary",
        })
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=classification))]
        )
        with patch.object(research_mod, "OpenAI", return_value=client), \
             patch.object(research_mod, "web_search", return_value="raw"):
            _invoke(research_world_events, ctx)
        assert ctx.mood == "neutral"

    def test_uses_raw_search_text_when_events_summary_missing(self):
        ctx = RebrandCtx(repo_root="/repo")
        client = MagicMock()
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="{}"))]
        )
        with patch.object(research_mod, "OpenAI", return_value=client), \
             patch.object(research_mod, "web_search", return_value="raw fallback text"):
            _invoke(research_world_events, ctx)
        assert ctx.world_events == "raw fallback text"
        assert ctx.mood == "neutral"
