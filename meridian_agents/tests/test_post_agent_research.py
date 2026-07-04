from unittest.mock import patch, MagicMock

import pytest

from meridian_agents.post_agent.nodes.research import (
    CATEGORIES,
    _CATEGORY_WEIGHTS,
    _pick_category,
    _web_search_gemini,
    _web_search_openai,
    _web_search,
    discover_trend_node,
    deep_research_node,
)

TECH_STATE = {
    "category_name": "Technology",
    "category_research_style": "artificial intelligence, quantum computing, and modern "
                                "DevOps/DevSecOps engineering",
    "trend": "Some trend " * 30,
}


class TestPickCategory:
    def test_uses_weighted_random_when_no_mode_set(self, monkeypatch):
        monkeypatch.delenv("TOPIC_MODE", raising=False)
        with patch("meridian_agents.post_agent.nodes.research.random.choices") as mock_choices:
            mock_choices.return_value = [CATEGORIES[0]]
            result = _pick_category()
        mock_choices.assert_called_once_with(CATEGORIES, weights=_CATEGORY_WEIGHTS, k=1)
        assert result == CATEGORIES[0]

    def test_matches_a_category_by_name_case_insensitively(self, monkeypatch):
        monkeypatch.setenv("TOPIC_MODE", "history")
        result = _pick_category()
        assert result["name"] == "History"

    def test_falls_back_to_weighted_random_for_unknown_mode(self, monkeypatch):
        monkeypatch.setenv("TOPIC_MODE", "not-a-real-mode")
        with patch("meridian_agents.post_agent.nodes.research.random.choices") as mock_choices:
            mock_choices.return_value = [CATEGORIES[1]]
            result = _pick_category()
        mock_choices.assert_called_once_with(CATEGORIES, weights=_CATEGORY_WEIGHTS, k=1)
        assert result == CATEGORIES[1]

    def test_exactly_four_categories_in_priority_order(self):
        names = [c["name"] for c in CATEGORIES]
        assert names == ["Technology", "Education", "Travel", "History"]

    def test_technology_and_education_carry_subtopic_pools(self):
        by_name = {c["name"]: c for c in CATEGORIES}
        assert len(by_name["Technology"]["subtopics"]) == 6
        assert len(by_name["Education"]["subtopics"]) == 3
        assert "subtopics" not in by_name["Travel"]
        assert "subtopics" not in by_name["History"]


class TestWebSearchGemini:
    def test_returns_response_text(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = MagicMock(text="gemini result")
        with patch("google.genai.Client", return_value=fake_client):
            result = _web_search_gemini("prompt")
        assert result == "gemini result"

    def test_returns_empty_string_when_no_text(self, monkeypatch):
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = MagicMock(text=None)
        with patch("google.genai.Client", return_value=fake_client):
            result = _web_search_gemini("prompt")
        assert result == ""


class TestWebSearchOpenai:
    def test_uses_responses_api_when_available(self):
        fake_client = MagicMock()
        fake_client.responses.create.return_value = MagicMock(output_text="responses result")
        with patch("openai.OpenAI", return_value=fake_client):
            result = _web_search_openai("prompt")
        assert result == "responses result"

    def test_falls_back_to_search_preview_model(self):
        fake_client = MagicMock()
        fake_client.responses.create.side_effect = Exception("not available")
        fake_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="search-preview result"))]
        )
        with patch("openai.OpenAI", return_value=fake_client):
            result = _web_search_openai("prompt")
        assert result == "search-preview result"

    def test_falls_back_to_plain_gpt4o_when_both_fail(self):
        fake_client = MagicMock()
        fake_client.responses.create.side_effect = Exception("not available")
        fake_client.chat.completions.create.side_effect = [
            Exception("search-preview unavailable"),
            MagicMock(choices=[MagicMock(message=MagicMock(content="training-knowledge result"))]),
        ]
        with patch("openai.OpenAI", return_value=fake_client):
            result = _web_search_openai("prompt")
        assert result == "training-knowledge result"


class TestWebSearch:
    def test_uses_gemini_when_api_key_present_and_successful(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        with patch("meridian_agents.post_agent.nodes.research._web_search_gemini", return_value="gemini text"), \
             patch("meridian_agents.post_agent.nodes.research._web_search_openai") as mock_openai:
            result = _web_search("prompt")
        assert result == "gemini text"
        mock_openai.assert_not_called()

    def test_falls_back_to_openai_when_gemini_returns_blank(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        with patch("meridian_agents.post_agent.nodes.research._web_search_gemini", return_value="   "), \
             patch("meridian_agents.post_agent.nodes.research._web_search_openai", return_value="openai text") as mock_openai:
            result = _web_search("prompt")
        assert result == "openai text"
        mock_openai.assert_called_once()

    def test_falls_back_to_openai_when_gemini_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        with patch("meridian_agents.post_agent.nodes.research._web_search_gemini", side_effect=Exception("boom")), \
             patch("meridian_agents.post_agent.nodes.research._web_search_openai", return_value="openai text") as mock_openai:
            result = _web_search("prompt")
        assert result == "openai text"
        mock_openai.assert_called_once()

    def test_goes_straight_to_openai_without_a_gemini_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with patch("meridian_agents.post_agent.nodes.research._web_search_gemini") as mock_gemini, \
             patch("meridian_agents.post_agent.nodes.research._web_search_openai", return_value="openai text"):
            result = _web_search("prompt")
        assert result == "openai text"
        mock_gemini.assert_not_called()


class TestDiscoverTrendNode:
    def test_returns_category_metadata_and_trend_for_a_category_with_subtopics(self, monkeypatch):
        monkeypatch.delenv("TOPIC_MODE", raising=False)
        with patch("meridian_agents.post_agent.nodes.research._pick_category", return_value=CATEGORIES[0]), \
             patch("meridian_agents.post_agent.nodes.research._web_search", return_value="Discovered trend text"):
            result = discover_trend_node({})
        assert result["category_name"] == CATEGORIES[0]["name"] == "Technology"
        assert result["trend"] == "Discovered trend text"

    def test_returns_category_metadata_and_trend_for_a_category_without_subtopics(self, monkeypatch):
        monkeypatch.delenv("TOPIC_MODE", raising=False)
        travel = next(c for c in CATEGORIES if c["name"] == "Travel")
        with patch("meridian_agents.post_agent.nodes.research._pick_category", return_value=travel), \
             patch("meridian_agents.post_agent.nodes.research._web_search", return_value="Travel trend text"):
            result = discover_trend_node({})
        assert result["category_name"] == "Travel"
        assert result["trend"] == "Travel trend text"


class TestDeepResearchNode:
    def test_runs_three_parallel_queries_and_aggregates_results(self):
        def fake_search(prompt):
            if "Deep research" in prompt:
                return "technical details"
            if "reactions to" in prompt:
                return "community reactions"
            if "implications of" in prompt:
                return "real-world implications"
            return "unexpected"

        with patch("meridian_agents.post_agent.nodes.research._web_search", side_effect=fake_search):
            result = deep_research_node(TECH_STATE)

        assert result["technical"] == "technical details"
        assert result["reactions"] == "community reactions"
        assert result["implications"] == "real-world implications"
