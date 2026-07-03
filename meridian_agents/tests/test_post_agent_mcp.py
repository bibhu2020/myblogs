from unittest.mock import patch, MagicMock

import pytest

from meridian_agents.post_agent.nodes import mcp as mcp_mod
from meridian_agents.post_agent.nodes.mcp import (
    mcp_call,
    _parse_mcp_items,
    _extract_slug_id,
    init_mcp_node,
    ensure_author_node,
    pick_taxonomy_node,
    save_pending_node,
    publish_approved_node,
)


def _resp(json_data):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = json_data
    return r


class TestMcpRequest:
    def test_returns_result_on_success(self):
        with patch("meridian_agents.post_agent.nodes.mcp.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.return_value = _resp({"jsonrpc": "2.0", "id": 1, "result": {"ok": True}})
            result = mcp_mod._mcp_request("ping")
        assert result == {"ok": True}

    def test_raises_on_error_response(self):
        with patch("meridian_agents.post_agent.nodes.mcp.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.return_value = _resp({"error": {"code": -32601, "message": "Method not found"}})
            with pytest.raises(RuntimeError, match="Method not found"):
                mcp_mod._mcp_request("bogus")

    def test_adds_auth_header_when_key_configured(self, monkeypatch):
        monkeypatch.setattr(mcp_mod, "MCP_KEY", "secret-key")
        with patch("meridian_agents.post_agent.nodes.mcp.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.return_value = _resp({"result": {}})
            mcp_mod._mcp_request("ping")
        _, kwargs = client.post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer secret-key"

    def test_omits_auth_header_when_no_key(self, monkeypatch):
        monkeypatch.setattr(mcp_mod, "MCP_KEY", "")
        with patch("meridian_agents.post_agent.nodes.mcp.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.return_value = _resp({"result": {}})
            mcp_mod._mcp_request("ping")
        _, kwargs = client.post.call_args
        assert "Authorization" not in kwargs["headers"]


class TestMcpCall:
    def test_raises_when_tool_reports_an_error(self):
        with patch.object(mcp_mod, "_mcp_request", return_value={"isError": True, "content": [{"text": "bad input"}]}):
            with pytest.raises(RuntimeError, match="bad input"):
                mcp_call("some_tool", {})

    def test_raises_when_no_content_returned(self):
        with patch.object(mcp_mod, "_mcp_request", return_value={"content": [{}]}):
            with pytest.raises(RuntimeError, match="no content"):
                mcp_call("some_tool", {})

    def test_parses_json_content(self):
        with patch.object(mcp_mod, "_mcp_request", return_value={"content": [{"text": '{"id": 1}'}]}):
            assert mcp_call("some_tool", {}) == {"id": 1}

    def test_returns_plain_text_when_not_json(self):
        with patch.object(mcp_mod, "_mcp_request", return_value={"content": [{"text": "plain text result"}]}):
            assert mcp_call("some_tool", {}) == "plain text result"


class TestParseMcpItems:
    def test_passes_through_a_list(self):
        assert _parse_mcp_items([{"id": 1}]) == [{"id": 1}]

    def test_parses_pipe_delimited_lines(self):
        text = "  ID: 1 | Name: Tech | Slug: tech\n  ID: 2 | Name: Science | Slug: science"
        result = _parse_mcp_items(text)
        assert result == [
            {"id": 1, "name": "Tech", "slug": "tech"},
            {"id": 2, "name": "Science", "slug": "science"},
        ]

    def test_ignores_unmatched_lines(self):
        assert _parse_mcp_items("no categories found") == []


class TestExtractSlugId:
    def test_extracts_from_dict(self):
        assert _extract_slug_id({"slug": "my-post", "id": 5}) == ("my-post", 5)

    def test_extracts_from_string(self):
        assert _extract_slug_id("Post created. ID: 7 | Slug: my-post") == ("my-post", 7)

    def test_returns_none_when_no_match(self):
        assert _extract_slug_id("no useful info here") == (None, None)


class TestInitMcpNode:
    def test_initializes_the_connection(self):
        with patch.object(mcp_mod, "_mcp_request") as mock_req:
            result = init_mcp_node({})
        mock_req.assert_called_once()
        assert mock_req.call_args[0][0] == "initialize"
        assert result == {}


class TestEnsureAuthorNode:
    STATE = {"author_name": "Agent", "author_email": "agent@test.com", "author_password": "pw"}

    def test_creates_author_successfully(self):
        with patch.object(mcp_mod, "mcp_call") as mock_call:
            result = ensure_author_node(self.STATE)
        mock_call.assert_called_once()
        assert result == {}

    def test_swallows_already_exists_error(self):
        with patch.object(mcp_mod, "mcp_call", side_effect=RuntimeError("User already exists")):
            result = ensure_author_node(self.STATE)  # must not raise
        assert result == {}

    def test_swallows_other_errors_with_warning(self):
        with patch.object(mcp_mod, "mcp_call", side_effect=RuntimeError("network down")):
            result = ensure_author_node(self.STATE)  # must not raise
        assert result == {}


class TestPickTaxonomyNode:
    CATEGORIES = [{"id": 1, "name": "Technology", "slug": "technology"}, {"id": 2, "name": "History", "slug": "history"}]
    TAGS = [
        {"id": 10, "name": "AI", "slug": "ai"},
        {"id": 11, "name": "Machine Learning", "slug": "machine-learning"},
        {"id": 12, "name": "Technology News", "slug": "technology-news"},
    ]

    def test_matches_category_and_tags_by_keyword(self):
        state = {
            "post_category_keywords": ["technology"],
            "post_tag_keywords": ["ai", "machine-learning"],
            "category_name": "AI & Machine Learning",
        }
        with patch.object(mcp_mod, "mcp_call", side_effect=[self.CATEGORIES, self.TAGS]):
            result = pick_taxonomy_node(state)
        assert result["category_id"] == 1
        assert 10 in result["tag_ids"]
        assert 11 in result["tag_ids"]

    def test_defaults_to_first_category_when_nothing_matches(self):
        state = {"post_category_keywords": ["nonexistent"], "post_tag_keywords": [], "category_name": "Nope"}
        with patch.object(mcp_mod, "mcp_call", side_effect=[self.CATEGORIES, []]):
            result = pick_taxonomy_node(state)
        assert result["category_id"] == 1
        assert result["tag_ids"] == []

    def test_handles_empty_categories_and_tags(self):
        state = {"post_category_keywords": [], "post_tag_keywords": [], "category_name": ""}
        with patch.object(mcp_mod, "mcp_call", side_effect=[[], []]):
            result = pick_taxonomy_node(state)
        assert result["category_id"] is None
        assert result["tag_ids"] == []

    def test_pads_tags_using_category_related_tags(self):
        state = {
            "post_category_keywords": ["technology"],
            "post_tag_keywords": ["ai"],
            "category_name": "Technology",
        }
        with patch.object(mcp_mod, "mcp_call", side_effect=[self.CATEGORIES, self.TAGS]):
            result = pick_taxonomy_node(state)
        # "ai" matches tag 10 directly; padding should pull in tag 12 ("Technology News")
        # since it relates to the matched "Technology" category.
        assert 10 in result["tag_ids"]
        assert len(result["tag_ids"]) >= 2


class TestSavePendingNode:
    def test_builds_minimal_args_and_returns_slug_id(self):
        state = {
            "post_title": "T", "final_content": "<p>c</p>", "post_excerpt": "e", "author_name": "Agent",
        }
        with patch.object(mcp_mod, "mcp_call", return_value={"slug": "t", "id": 9}) as mock_call:
            result = save_pending_node(state)
        args = mock_call.call_args[0][1]
        assert "category_id" not in args
        assert "tag_ids" not in args
        assert "featured_image" not in args
        assert result == {
            "pending_post_id": 9, "pending_post_slug": "t",
            "approved": None, "published_slug": None, "published_id": None,
        }

    def test_includes_optional_fields_when_present(self):
        state = {
            "post_title": "T", "final_content": "<p>c</p>", "post_excerpt": "e", "author_name": "Agent",
            "category_id": 3, "tag_ids": [1, 2], "featured_image_url": "https://img",
        }
        with patch.object(mcp_mod, "mcp_call", return_value={"slug": "t", "id": 9}) as mock_call:
            save_pending_node(state)
        args = mock_call.call_args[0][1]
        assert args["category_id"] == 3
        assert args["tag_ids"] == [1, 2]
        assert args["featured_image"] == "https://img"


class TestPublishApprovedNode:
    def test_no_op_when_no_pending_post_id(self):
        assert publish_approved_node({}) == {}

    def test_publishes_successfully(self):
        state = {"pending_post_id": 9, "pending_post_slug": "t", "server_base": "https://server"}
        with patch("meridian_agents.post_agent.nodes.mcp.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.patch.return_value = _resp({})
            result = publish_approved_node(state)
        assert result == {"published_slug": "t", "published_id": 9}

    def test_falls_back_gracefully_when_publish_api_call_fails(self):
        state = {"pending_post_id": 9, "pending_post_slug": "t", "server_base": "https://server"}
        with patch("meridian_agents.post_agent.nodes.mcp.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.patch.side_effect = Exception("down")
            result = publish_approved_node(state)
        assert result == {"published_slug": "t", "published_id": 9}
