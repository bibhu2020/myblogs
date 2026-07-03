import json
from unittest.mock import patch

from meridian_agents.story_agent.nodes.writer import (
    AGE_GROUPS,
    THEMES_3_7,
    THEMES_8_15,
    THEMES_16_20,
    _word_count,
    _pick_age_group,
    _pick_theme,
    pick_theme_node,
    write_story_node,
    expand_story_node,
)

FAKE_STORY_JSON = json.dumps({
    "title": "The Brave Little Robot",
    "excerpt": "A robot learns what matters most.",
    "featuredImagePrompt": "A small robot in a garden",
    "moralLesson": "Kindness matters most.",
    "content": "<p>" + " ".join(["word"] * 40) + "</p>",
})

STATE = {
    "age_group": "8-15",
    "genre": "AI & Machine Learning",
    "premise": "A robot learns to paint",
    "moral_lesson": "Kindness matters",
    "story_title": "Old Title",
    "story_excerpt": "Old excerpt",
    "story_content": "<p>Old content</p>",
    "featured_image_prompt": "Old prompt",
    "word_count": 300,
}


class TestWordCount:
    def test_strips_html_tags(self):
        assert _word_count("<p>one two three</p>") == 3


class TestPickAgeGroup:
    def test_uses_forced_age_group_when_valid(self, monkeypatch):
        monkeypatch.setenv("STORY_AGE_GROUP", "16-20")
        assert _pick_age_group() == "16-20"

    def test_ignores_invalid_forced_age_group(self, monkeypatch):
        monkeypatch.setenv("STORY_AGE_GROUP", "99-100")
        with patch("meridian_agents.story_agent.nodes.writer.random.choice", return_value="8-15") as mock_choice:
            result = _pick_age_group()
        mock_choice.assert_called_once_with(AGE_GROUPS)
        assert result == "8-15"

    def test_picks_randomly_when_unset(self, monkeypatch):
        monkeypatch.delenv("STORY_AGE_GROUP", raising=False)
        with patch("meridian_agents.story_agent.nodes.writer.random.choice", return_value="3-7"):
            assert _pick_age_group() == "3-7"


class TestPickTheme:
    def test_uses_the_3_7_pool_for_that_age_group(self):
        theme = _pick_theme("3-7")
        assert any(t["genre"] == theme["genre"] for t in THEMES_3_7)

    def test_uses_the_16_20_pool_for_that_age_group(self):
        theme = _pick_theme("16-20")
        assert any(t["genre"] == theme["genre"] for t in THEMES_16_20)

    def test_defaults_to_8_15_pool_for_other_age_groups(self):
        theme = _pick_theme("8-15")
        assert any(t["genre"] == theme["genre"] for t in THEMES_8_15)

    def test_forced_genre_matches_case_insensitively(self, monkeypatch):
        monkeypatch.setenv("STORY_GENRE", "quantum adventure")
        theme = _pick_theme("8-15")
        assert theme["genre"] == "Quantum Adventure"

    def test_falls_back_to_random_when_forced_genre_unknown(self, monkeypatch):
        monkeypatch.setenv("STORY_GENRE", "Not A Real Genre")
        theme = _pick_theme("8-15")
        assert any(t["genre"] == theme["genre"] for t in THEMES_8_15)


class TestPickThemeNode:
    def test_returns_age_genre_premise_and_moral(self, monkeypatch):
        monkeypatch.delenv("STORY_AGE_GROUP", raising=False)
        monkeypatch.delenv("STORY_GENRE", raising=False)
        result = pick_theme_node({})
        assert result["age_group"] in AGE_GROUPS
        assert "genre" in result
        assert "premise" in result
        assert "moral_lesson" in result


class TestWriteStoryNode:
    def test_returns_parsed_story_fields(self):
        with patch("meridian_agents.story_agent.nodes.writer.chat_completion") as mock_chat:
            mock_chat.return_value = (FAKE_STORY_JSON, "gpt-4o")
            result = write_story_node(STATE)
        assert result["story_title"] == "The Brave Little Robot"
        assert result["word_count"] == 40

    def test_defaults_age_group_when_missing_from_state(self):
        state_without_age = {k: v for k, v in STATE.items() if k != "age_group"}
        with patch("meridian_agents.story_agent.nodes.writer.chat_completion") as mock_chat:
            mock_chat.return_value = (FAKE_STORY_JSON, "gpt-4o")
            result = write_story_node(state_without_age)
        assert result["story_title"] == "The Brave Little Robot"


class TestExpandStoryNode:
    def test_returns_expanded_fields(self):
        with patch("meridian_agents.story_agent.nodes.writer.chat_completion") as mock_chat:
            mock_chat.return_value = (FAKE_STORY_JSON, "gpt-4o")
            result = expand_story_node(STATE)
        assert result["word_count"] == 40

    def test_falls_back_to_prior_image_prompt_when_missing(self):
        minimal = json.dumps({
            "title": "T", "excerpt": "E", "moralLesson": "M", "content": "<p>hi</p>",
        })
        with patch("meridian_agents.story_agent.nodes.writer.chat_completion") as mock_chat:
            mock_chat.return_value = (minimal, "gpt-4o")
            result = expand_story_node(STATE)
        assert result["featured_image_prompt"] == STATE["featured_image_prompt"]
