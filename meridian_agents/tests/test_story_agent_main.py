import json
from unittest.mock import patch, MagicMock

import pytest

from meridian_agents.story_agent import main as main_mod
from meridian_agents.story_agent.main import (
    _append_pending,
    _load_pending,
    _remove_pending,
    run_agent,
    approve_story,
    reject_story,
    list_pending,
    _get_admin_token,
)


@pytest.fixture(autouse=True)
def isolated_pending_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main_mod, "_PENDING_FILE", tmp_path / "pending_stories.jsonl")


class TestPendingRegistry:
    def test_append_then_load_round_trips(self):
        _append_pending({"story_id": 1, "title": "Hello"})
        entries = _load_pending()
        assert entries == [{"story_id": 1, "title": "Hello"}]

    def test_load_returns_empty_list_when_file_missing(self):
        assert _load_pending() == []

    def test_load_skips_malformed_lines(self):
        main_mod._PENDING_FILE.write_text("not json\n" + json.dumps({"story_id": 1}) + "\n")
        assert _load_pending() == [{"story_id": 1}]

    def test_remove_pending_drops_the_matching_entry(self):
        _append_pending({"story_id": 1})
        _append_pending({"story_id": 2})
        _remove_pending(2)
        assert _load_pending() == [{"story_id": 1}]


class TestListPending:
    def test_prints_no_pending_message_when_empty(self, capsys):
        list_pending()
        assert "No pending stories" in capsys.readouterr().out

    def test_prints_a_table_of_entries(self, capsys):
        _append_pending({"story_id": 1, "title": "Hello", "genre": "Adventure", "generated_at": "2026-01-01"})
        list_pending()
        assert "Hello" in capsys.readouterr().out


class TestGetAdminToken:
    def test_uses_env_token_when_set(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "existing-token")
        assert _get_admin_token() == "existing-token"

    def test_logs_in_when_no_env_token(self, monkeypatch):
        monkeypatch.delenv("AGENT_JWT_TOKEN", raising=False)
        with patch("meridian_agents.story_agent.main.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.return_value = MagicMock(json=lambda: {"access_token": "fresh"})
            assert _get_admin_token() == "fresh"


class TestApproveStory:
    def test_approves_and_removes_from_pending(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        _append_pending({"story_id": 5, "title": "A Story"})
        with patch("meridian_agents.story_agent.main.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.patch.return_value = MagicMock(json=lambda: {"slug": "a-story"})
            approve_story(5)
        assert _load_pending() == []


class TestRejectStory:
    def test_rejects_and_removes_from_pending(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        _append_pending({"story_id": 5, "title": "A Story"})
        with patch("meridian_agents.story_agent.main.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.patch.return_value = MagicMock()
            reject_story(5)
        assert _load_pending() == []


class TestRunAgent:
    def test_raises_without_openai_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            run_agent()

    def test_runs_the_full_pipeline_without_expansion_when_long_enough(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with patch.object(main_mod, "cleanup_old_stories") as mock_cleanup, \
             patch.object(main_mod, "start_run", return_value="run-1"), \
             patch.object(main_mod, "pick_theme_node", return_value={"age_group": "High School+", "category": "AI", "genre": "Thriller"}), \
             patch.object(main_mod, "write_story_node", return_value={"story_title": "T", "word_count": 5000}), \
             patch.object(main_mod, "expand_story_node") as mock_expand, \
             patch.object(main_mod, "generate_story_images_node", return_value={"featured_image_url": None, "final_content": "c"}), \
             patch.object(main_mod, "save_pending_node", return_value={"pending_story_id": 9, "pending_story_slug": "t"}), \
             patch.object(main_mod, "complete_run") as mock_complete:
            result = run_agent()
        mock_cleanup.assert_called_once()
        mock_expand.assert_not_called()
        assert result["pending_story_id"] == 9
        mock_complete.assert_called_once()
        assert _load_pending()[0]["story_id"] == 9

    def test_expands_when_word_count_below_minimum(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with patch.object(main_mod, "cleanup_old_stories"), \
             patch.object(main_mod, "start_run", return_value="run-1"), \
             patch.object(main_mod, "pick_theme_node", return_value={"age_group": "High School+", "category": "AI", "genre": "Thriller"}), \
             patch.object(main_mod, "write_story_node", return_value={"story_title": "T", "word_count": 100}), \
             patch.object(main_mod, "expand_story_node", return_value={"word_count": 900}) as mock_expand, \
             patch.object(main_mod, "generate_story_images_node", return_value={"featured_image_url": None, "final_content": "c"}), \
             patch.object(main_mod, "save_pending_node", return_value={"pending_story_id": 9, "pending_story_slug": "t"}), \
             patch.object(main_mod, "complete_run"):
            run_agent()
        mock_expand.assert_called_once()

    def test_marks_run_failed_and_reraises_on_pipeline_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with patch.object(main_mod, "cleanup_old_stories"), \
             patch.object(main_mod, "start_run", return_value="run-1"), \
             patch.object(main_mod, "pick_theme_node", side_effect=RuntimeError("theme picking failed")), \
             patch.object(main_mod, "complete_run") as mock_complete:
            with pytest.raises(RuntimeError, match="theme picking failed"):
                run_agent()
        mock_complete.assert_called_once_with("run-1", "theme picking failed", failed=True)
