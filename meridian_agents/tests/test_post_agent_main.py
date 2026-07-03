import json
from unittest.mock import patch, MagicMock

import pytest

from meridian_agents.post_agent import main as main_mod
from meridian_agents.post_agent.main import (
    _append_pending,
    _load_pending,
    _remove_pending,
    run_agent,
    approve_post,
    reject_post,
    list_pending,
    _get_admin_token,
)


@pytest.fixture(autouse=True)
def isolated_pending_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main_mod, "_PENDING_FILE", tmp_path / "pending_posts.jsonl")


class TestPendingRegistry:
    def test_append_then_load_round_trips(self):
        _append_pending({"post_id": 1, "title": "Hello"})
        _append_pending({"post_id": 2, "title": "World"})
        entries = _load_pending()
        assert len(entries) == 2
        assert entries[0]["title"] == "Hello"

    def test_load_returns_empty_list_when_file_missing(self):
        assert _load_pending() == []

    def test_load_skips_malformed_lines(self):
        main_mod._PENDING_FILE.write_text("not json\n" + json.dumps({"post_id": 1}) + "\n")
        entries = _load_pending()
        assert entries == [{"post_id": 1}]

    def test_remove_pending_drops_the_matching_entry(self):
        _append_pending({"post_id": 1, "title": "Keep"})
        _append_pending({"post_id": 2, "title": "Remove"})
        _remove_pending(2)
        entries = _load_pending()
        assert len(entries) == 1
        assert entries[0]["post_id"] == 1

    def test_remove_pending_handles_now_empty_file(self):
        _append_pending({"post_id": 1})
        _remove_pending(1)
        assert _load_pending() == []


class TestListPending:
    def test_prints_no_pending_message_when_empty(self, capsys):
        list_pending()
        assert "No pending posts" in capsys.readouterr().out

    def test_prints_a_table_of_entries(self, capsys):
        _append_pending({"post_id": 1, "title": "Hello", "generated_at": "2026-01-01"})
        list_pending()
        out = capsys.readouterr().out
        assert "Hello" in out


class TestGetAdminToken:
    def test_uses_env_token_when_set(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "existing-token")
        assert _get_admin_token() == "existing-token"

    def test_logs_in_when_no_env_token(self, monkeypatch):
        monkeypatch.delenv("AGENT_JWT_TOKEN", raising=False)
        with patch("meridian_agents.post_agent.main.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.return_value = MagicMock(json=lambda: {"access_token": "fresh"})
            assert _get_admin_token() == "fresh"


class TestApprovePost:
    def test_approves_and_removes_from_pending(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        _append_pending({"post_id": 5, "title": "A Post"})
        with patch("meridian_agents.post_agent.main.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.patch.return_value = MagicMock(json=lambda: {"slug": "a-post"})
            approve_post(5)
        assert _load_pending() == []


class TestRejectPost:
    def test_rejects_and_removes_from_pending(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        _append_pending({"post_id": 5, "title": "A Post"})
        with patch("meridian_agents.post_agent.main.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.patch.return_value = MagicMock()
            reject_post(5)
        assert _load_pending() == []


class TestRunAgent:
    def test_raises_without_openai_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            run_agent()

    def test_runs_the_full_pipeline_and_records_the_pending_post(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        fake_graph = MagicMock()
        fake_graph.invoke.return_value = {
            "pending_post_id": 42, "pending_post_slug": "my-post", "post_title": "My Post",
        }
        with patch.object(main_mod, "cleanup_old_posts") as mock_cleanup, \
             patch.object(main_mod, "start_run", return_value="run-1") as mock_start, \
             patch.object(main_mod, "build_graph", return_value=fake_graph), \
             patch.object(main_mod, "complete_run") as mock_complete:
            result = run_agent()
        mock_cleanup.assert_called_once()
        mock_start.assert_called_once()
        assert result["pending_post_id"] == 42
        mock_complete.assert_called_once()
        entries = _load_pending()
        assert entries[0]["post_id"] == 42

    def test_marks_run_failed_and_reraises_on_graph_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        fake_graph = MagicMock()
        fake_graph.invoke.side_effect = RuntimeError("graph exploded")
        with patch.object(main_mod, "cleanup_old_posts"), \
             patch.object(main_mod, "start_run", return_value="run-1"), \
             patch.object(main_mod, "build_graph", return_value=fake_graph), \
             patch.object(main_mod, "complete_run") as mock_complete:
            with pytest.raises(RuntimeError, match="graph exploded"):
                run_agent()
        mock_complete.assert_called_once_with("run-1", "graph exploded", failed=True)
