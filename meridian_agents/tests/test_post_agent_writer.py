import json
from unittest.mock import patch

from meridian_agents.post_agent.nodes.writer import (
    _system_prompt,
    _word_count,
    _user_prompt,
    write_post_node,
    expand_post_node,
)

STATE = {
    "category_name": "Technology",
    "trend": "LLMs are getting bigger",
    "technical": "Scaling laws",
    "reactions": "Researchers are excited",
    "implications": "More capable assistants",
    "post_title": "Old Title",
    "post_excerpt": "Old excerpt",
    "post_content": "<p>Old content</p>",
    "post_featured_image_prompt": "Old prompt",
    "post_category_keywords": ["ai"],
    "post_tag_keywords": ["llm"],
    "post_unsplash_query": None,
}

FAKE_POST_JSON = json.dumps({
    "title": "The Rise of Large Language Models",
    "excerpt": "How LLMs are reshaping software.",
    "suggestedCategoryKeywords": ["ai", "machine-learning"],
    "suggestedTagKeywords": ["llm", "transformer"],
    "featuredImagePrompt": "A glowing neural network",
    "content": "<p>" + " ".join(["word"] * 50) + "</p>",
})


class TestSystemPrompt:
    def test_uses_the_matching_persona(self):
        prompt = _system_prompt("Technology")
        assert "senior technology journalist" in prompt

    def test_falls_back_to_default_persona_for_unknown_category(self):
        prompt = _system_prompt("Nonexistent Category")
        assert "senior editorial journalist" in prompt

    def test_appends_travel_addendum_only_for_travel(self):
        travel_prompt = _system_prompt("Travel")
        other_prompt = _system_prompt("History")
        assert "unsplashSearchQuery" in travel_prompt
        assert "unsplashSearchQuery" not in other_prompt

    def test_includes_image_consistency_directive_for_every_category(self):
        for category in ("Technology", "Education", "Travel", "History"):
            prompt = _system_prompt(category)
            assert "coherent visual narrative" in prompt


class TestWordCount:
    def test_strips_html_tags_before_counting(self):
        assert _word_count("<p>one two three</p>") == 3

    def test_counts_zero_for_empty_content(self):
        assert _word_count("") == 0


class TestUserPrompt:
    def test_includes_category_and_research_sections(self):
        prompt = _user_prompt(STATE)
        assert "Technology" in prompt
        assert "LLMs are getting bigger" in prompt
        assert "Scaling laws" in prompt
        assert "Researchers are excited" in prompt
        assert "More capable assistants" in prompt


class TestWritePostNode:
    def test_returns_parsed_post_fields(self):
        with patch("meridian_agents.post_agent.nodes.writer.chat_completion") as mock_chat:
            mock_chat.return_value = (FAKE_POST_JSON, "gpt-4o")
            result = write_post_node(STATE)
        assert result["post_title"] == "The Rise of Large Language Models"
        assert result["post_category_keywords"] == ["ai", "machine-learning"]
        assert result["word_count"] == 50

    def test_defaults_optional_fields_when_missing_from_response(self):
        minimal = json.dumps({
            "title": "T", "excerpt": "E", "featuredImagePrompt": "P", "content": "<p>hi</p>",
        })
        with patch("meridian_agents.post_agent.nodes.writer.chat_completion") as mock_chat:
            mock_chat.return_value = (minimal, "gpt-4o")
            result = write_post_node(STATE)
        assert result["post_category_keywords"] == []
        assert result["post_tag_keywords"] == []
        assert result["post_unsplash_query"] is None


class TestExpandPostNode:
    def test_returns_expanded_post_fields(self):
        with patch("meridian_agents.post_agent.nodes.writer.chat_completion") as mock_chat:
            mock_chat.return_value = (FAKE_POST_JSON, "gpt-4o")
            result = expand_post_node(STATE)
        assert result["post_title"] == "The Rise of Large Language Models"
        assert result["word_count"] == 50

    def test_falls_back_to_prior_state_values_when_missing(self):
        minimal = json.dumps({
            "title": "T", "excerpt": "E", "featuredImagePrompt": "P", "content": "<p>hi</p>",
        })
        with patch("meridian_agents.post_agent.nodes.writer.chat_completion") as mock_chat:
            mock_chat.return_value = (minimal, "gpt-4o")
            result = expand_post_node(STATE)
        assert result["post_category_keywords"] == STATE["post_category_keywords"]
        assert result["post_tag_keywords"] == STATE["post_tag_keywords"]
        assert result["post_unsplash_query"] == STATE["post_unsplash_query"]
