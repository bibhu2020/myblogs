"""Tests for rebranding_agent/tools/planning.py: generate_rebrand_plan,
revise_rebrand_plan. The OpenAI client is always mocked — no real API calls.
"""
import asyncio
import json
from unittest.mock import patch, MagicMock

from agents.tool_context import ToolContext

from meridian_agents.rebranding_agent.context import RebrandCtx
from meridian_agents.rebranding_agent.tools import planning as planning_mod
from meridian_agents.rebranding_agent.tools.planning import (
    generate_rebrand_plan,
    revise_rebrand_plan,
)


def _invoke(tool, ctx: RebrandCtx, **kwargs):
    tc = ToolContext(context=ctx, tool_name=tool.name, tool_call_id="1", tool_arguments="{}")
    return asyncio.run(tool.on_invoke_tool(tc, json.dumps(kwargs)))


_FULL_PLAN = {
    "palette_a": {f"primary-{s}": "#111111" for s in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)},
    "lb_accent": {"lb-accent": "#222222"},
    "banner_a_html": "<div>a</div>",
    "hero_a_html": "<div>h</div>",
    "footer_html": "<p>f</p>",
    "banner_b_html": "<div>b</div>",
    "hero_b_html": "<div>hb</div>",
    "holiday_css": ".x{}",
}


def _mock_openai_with_content(content: str):
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=content))]
    )
    return client


class TestGenerateRebrandPlan:
    def test_errors_without_chosen_theme(self):
        ctx = RebrandCtx(repo_root="/repo")
        result = _invoke(generate_rebrand_plan, ctx)
        assert "ERROR" in result
        assert "research_world_events" in result

    def test_generates_a_valid_plan(self):
        ctx = RebrandCtx(repo_root="/repo", chosen_theme="Winter Holidays", mood="celebratory")
        client = _mock_openai_with_content(json.dumps(_FULL_PLAN))
        with patch.object(planning_mod, "OpenAI", return_value=client):
            result = _invoke(generate_rebrand_plan, ctx)
        assert ctx.rebrand_plan == _FULL_PLAN
        assert "Plan generated" in result

    def test_errors_on_invalid_json_response(self):
        ctx = RebrandCtx(repo_root="/repo", chosen_theme="Winter Holidays")
        client = _mock_openai_with_content("not valid json{{{")
        with patch.object(planning_mod, "OpenAI", return_value=client):
            result = _invoke(generate_rebrand_plan, ctx)
        assert "ERROR" in result
        assert "invalid JSON" in result

    def test_errors_when_required_keys_missing(self):
        ctx = RebrandCtx(repo_root="/repo", chosen_theme="Winter Holidays")
        incomplete = {"palette_a": _FULL_PLAN["palette_a"]}
        client = _mock_openai_with_content(json.dumps(incomplete))
        with patch.object(planning_mod, "OpenAI", return_value=client):
            result = _invoke(generate_rebrand_plan, ctx)
        assert "ERROR" in result
        assert "missing required keys" in result

    def test_errors_when_palette_shades_missing(self):
        ctx = RebrandCtx(repo_root="/repo", chosen_theme="Winter Holidays")
        plan = {**_FULL_PLAN, "palette_a": {"primary-50": "#111111"}}
        client = _mock_openai_with_content(json.dumps(plan))
        with patch.object(planning_mod, "OpenAI", return_value=client):
            result = _invoke(generate_rebrand_plan, ctx)
        assert "ERROR" in result
        assert "palette_a missing shades" in result


class TestReviseRebrandPlan:
    def test_errors_without_an_existing_plan(self):
        ctx = RebrandCtx(repo_root="/repo")
        result = _invoke(revise_rebrand_plan, ctx, feedback="fix contrast")
        assert "ERROR" in result
        assert "No existing plan" in result

    def test_revises_the_plan_and_increments_cycle_count(self):
        ctx = RebrandCtx(repo_root="/repo", rebrand_plan=_FULL_PLAN, review_cycles=0)
        revised = {**_FULL_PLAN, "palette_a": {**_FULL_PLAN["palette_a"], "primary-600": "#000000"}}
        client = _mock_openai_with_content(json.dumps(revised))
        with patch.object(planning_mod, "OpenAI", return_value=client):
            result = _invoke(revise_rebrand_plan, ctx, feedback="contrast too low")
        assert ctx.review_cycles == 1
        assert ctx.rebrand_plan["palette_a"]["primary-600"] == "#000000"
        assert ctx.review_feedback == ""
        assert "Plan revised" in result

    def test_stops_after_three_revision_cycles(self):
        ctx = RebrandCtx(repo_root="/repo", rebrand_plan=_FULL_PLAN, review_cycles=3)
        result = _invoke(revise_rebrand_plan, ctx, feedback="still bad")
        assert "ERROR" in result
        assert "Maximum revision cycles" in result
        assert ctx.review_cycles == 4

    def test_errors_on_invalid_json_response(self):
        ctx = RebrandCtx(repo_root="/repo", rebrand_plan=_FULL_PLAN, review_cycles=0)
        client = _mock_openai_with_content("{{not json")
        with patch.object(planning_mod, "OpenAI", return_value=client):
            result = _invoke(revise_rebrand_plan, ctx, feedback="fix it")
        assert "ERROR" in result
        assert "invalid JSON" in result
