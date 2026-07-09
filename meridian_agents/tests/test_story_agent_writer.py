import json
from unittest.mock import patch

from meridian_agents.story_agent.nodes.writer import (
    CATEGORIES,
    _word_count,
    _pick_theme,
    _system_prompt,
    pick_theme_node,
    write_story_node,
    expand_story_node,
    _MIN_WORDS,
)

FAKE_STORY_JSON = json.dumps({
    "title": "The Brave Little Robot",
    "excerpt": "A robot learns what matters most.",
    "featuredImagePrompt": "A small robot in a garden",
    "moralLesson": "Backpropagation lets a network learn from its mistakes.",
    "content": "<p>" + " ".join(["word"] * 40) + "</p>",
})

STATE = {
    "category": "AI",
    "genre": "Thriller",
    "premise": "A student discovers a self-driving delivery bot can be tricked by a few pixels",
    "moral_lesson": "Adversarial examples and model brittleness",
    "story_title": "Old Title",
    "story_excerpt": "Old excerpt",
    "story_content": "<p>Old content</p>",
    "featured_image_prompt": "Old prompt",
    "word_count": 300,
}


class TestWordCount:
    def test_strips_html_tags(self):
        assert _word_count("<p>one two three</p>") == 3


class TestCategoryBank:
    def test_exactly_three_categories(self):
        assert set(CATEGORIES) == {"AI", "Robotics", "Quantum"}

    def test_every_premise_is_genre_tagged_with_a_real_genre(self):
        for pool in CATEGORIES.values():
            for premise in pool:
                assert premise["genre"] in {"Horror", "Sci-Fi", "Thriller"}

    def test_every_premise_names_a_concrete_concept(self):
        for pool in CATEGORIES.values():
            for premise in pool:
                assert premise["concept"]
                assert premise["premise"]

    def test_each_category_has_multiple_genres_represented(self):
        for name, pool in CATEGORIES.items():
            genres = {p["genre"] for p in pool}
            assert len(genres) > 1, f"{name} pool should rotate genres"


class TestPickTheme:
    def test_picks_from_the_requested_category(self):
        theme = _pick_theme("Robotics")
        assert theme["category"] == "Robotics"
        assert theme["premise"] in [p["premise"] for p in CATEGORIES["Robotics"]]

    def test_picks_randomly_across_categories_when_none_given(self):
        theme = _pick_theme()
        assert theme["category"] in CATEGORIES

    def test_falls_back_to_random_category_for_unknown_name(self):
        theme = _pick_theme("Not A Real Category")
        assert theme["category"] in CATEGORIES

    def test_forced_category_env_var_overrides_argument(self, monkeypatch):
        monkeypatch.setenv("STORY_CATEGORY", "quantum")
        theme = _pick_theme("AI")
        assert theme["category"] == "Quantum"

    def test_forced_genre_env_var_filters_the_pool(self, monkeypatch):
        monkeypatch.setenv("STORY_GENRE", "horror")
        theme = _pick_theme("AI")
        assert theme["genre"] == "Horror"

    def test_falls_back_to_full_pool_when_forced_genre_unknown(self, monkeypatch):
        monkeypatch.setenv("STORY_GENRE", "Not A Real Genre")
        theme = _pick_theme("AI")
        assert theme["category"] == "AI"


class TestSystemPrompt:
    def test_includes_the_category_and_audience(self):
        prompt = _system_prompt("Quantum", "Horror")
        assert "Quantum" in prompt
        assert "high school students and above" in prompt

    def test_includes_the_genre_specific_tts_style(self):
        prompt = _system_prompt("AI", "Horror")
        assert "HORROR" in prompt
        assert "dread" in prompt.lower()

    def test_falls_back_to_thriller_style_for_unknown_genre(self):
        prompt = _system_prompt("AI", "Not A Real Genre")
        assert "THRILLER" in prompt


class TestPickThemeNode:
    def test_returns_category_genre_premise_and_concept(self, monkeypatch):
        monkeypatch.delenv("STORY_CATEGORY", raising=False)
        monkeypatch.delenv("STORY_GENRE", raising=False)
        result = pick_theme_node({})
        assert result["category"] in CATEGORIES
        assert result["genre"] in {"Horror", "Sci-Fi", "Thriller"}
        assert "premise" in result
        assert "moral_lesson" in result
        assert result["age_group"] == "High School+"


class TestWriteStoryNode:
    def test_returns_parsed_story_fields(self):
        with patch("meridian_agents.story_agent.nodes.writer.chat_completion") as mock_chat:
            mock_chat.return_value = (FAKE_STORY_JSON, "gpt-4o")
            result = write_story_node(STATE)
        assert result["story_title"] == "The Brave Little Robot"
        assert result["word_count"] == 40

    def test_defaults_category_and_genre_when_missing_from_state(self):
        state_without_category = {k: v for k, v in STATE.items() if k not in ("category", "genre")}
        with patch("meridian_agents.story_agent.nodes.writer.chat_completion") as mock_chat:
            mock_chat.return_value = (FAKE_STORY_JSON, "gpt-4o")
            result = write_story_node(state_without_category)
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

    def test_min_words_is_a_single_constant(self):
        assert isinstance(_MIN_WORDS, int)
        assert _MIN_WORDS > 0
