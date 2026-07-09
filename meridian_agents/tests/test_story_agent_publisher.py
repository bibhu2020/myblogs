from unittest.mock import patch, MagicMock

from meridian_agents.story_agent.nodes.publisher import save_pending_node, attach_story_audio_node

STATE = {
    "server_base": "https://server",
    "story_title": "The Brave Fox",
    "final_content": "<p>content</p>",
    "story_excerpt": "excerpt",
    "author_name": "Story Agent",
    "genre": "Thriller",
    "category": "AI",
    "age_group": "High School+",
    "moral_lesson": "Adversarial examples and model brittleness",
}


def _resp(json_data):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = json_data
    return r


class TestSavePendingNode:
    def test_saves_and_returns_id_and_slug(self):
        with patch("meridian_agents.story_agent.nodes.publisher.make_agent_jwt", return_value="jwt"), \
             patch("meridian_agents.story_agent.nodes.publisher.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.return_value = _resp({"id": 3, "slug": "the-brave-fox"})
            result = save_pending_node(STATE)
        assert result == {"pending_story_id": 3, "pending_story_slug": "the-brave-fox"}

    def test_includes_featured_image_when_present(self):
        state = {**STATE, "featured_image_url": "https://server/cover.jpg"}
        with patch("meridian_agents.story_agent.nodes.publisher.make_agent_jwt", return_value="jwt"), \
             patch("meridian_agents.story_agent.nodes.publisher.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.return_value = _resp({"id": 3, "slug": "the-brave-fox"})
            save_pending_node(state)
        _, kwargs = client.post.call_args
        assert kwargs["json"]["featuredImage"] == "https://server/cover.jpg"

    def test_omits_featured_image_when_absent(self):
        with patch("meridian_agents.story_agent.nodes.publisher.make_agent_jwt", return_value="jwt"), \
             patch("meridian_agents.story_agent.nodes.publisher.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.return_value = _resp({"id": 3, "slug": "the-brave-fox"})
            save_pending_node(STATE)
        _, kwargs = client.post.call_args
        assert "featuredImage" not in kwargs["json"]

    def test_includes_category(self):
        with patch("meridian_agents.story_agent.nodes.publisher.make_agent_jwt", return_value="jwt"), \
             patch("meridian_agents.story_agent.nodes.publisher.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.return_value = _resp({"id": 3, "slug": "the-brave-fox"})
            save_pending_node(STATE)
        _, kwargs = client.post.call_args
        assert kwargs["json"]["category"] == "AI"

    def test_never_includes_audio_url(self):
        # audio_url is intentionally attached in a separate step (attach_story_audio_node)
        # AFTER this save, since the story doesn't have an id yet when this runs.
        state = {**STATE, "audio_url": "https://server/uploads/narration.mp3"}
        with patch("meridian_agents.story_agent.nodes.publisher.make_agent_jwt", return_value="jwt"), \
             patch("meridian_agents.story_agent.nodes.publisher.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.return_value = _resp({"id": 3, "slug": "the-brave-fox"})
            save_pending_node(state)
        _, kwargs = client.post.call_args
        assert "audioUrl" not in kwargs["json"]


class TestAttachStoryAudioNode:
    def test_attaches_audio_url_via_put(self):
        state = {**STATE, "pending_story_id": 3, "audio_url": "https://server/uploads/story_3.mp3"}
        with patch("meridian_agents.story_agent.nodes.publisher.make_agent_jwt", return_value="jwt"), \
             patch("meridian_agents.story_agent.nodes.publisher.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.put.return_value = _resp({})
            result = attach_story_audio_node(state)
        client.put.assert_called_once_with(
            "https://server/api/stories/3",
            json={"audioUrl": "https://server/uploads/story_3.mp3"},
            headers={"Authorization": "Bearer jwt"},
        )
        assert result == {}

    def test_no_op_when_audio_url_missing(self):
        state = {**STATE, "pending_story_id": 3, "audio_url": None}
        with patch("meridian_agents.story_agent.nodes.publisher.httpx.Client") as MockClient:
            attach_story_audio_node(state)
            MockClient.assert_not_called()

    def test_no_op_when_story_id_missing(self):
        state = {**STATE, "pending_story_id": None, "audio_url": "https://server/uploads/story.mp3"}
        with patch("meridian_agents.story_agent.nodes.publisher.httpx.Client") as MockClient:
            attach_story_audio_node(state)
            MockClient.assert_not_called()

    def test_swallows_request_errors(self):
        state = {**STATE, "pending_story_id": 3, "audio_url": "https://server/uploads/story_3.mp3"}
        with patch("meridian_agents.story_agent.nodes.publisher.make_agent_jwt", return_value="jwt"), \
             patch("meridian_agents.story_agent.nodes.publisher.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.put.side_effect = Exception("network down")
            result = attach_story_audio_node(state)
        assert result == {}
