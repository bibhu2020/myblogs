from unittest.mock import patch

from meridian_agents.story_agent.nodes import images as story_images_mod
from meridian_agents.story_agent.nodes.images import generate_story_images_node

STATE = {
    "featured_image_prompt": "A magical forest",
    "story_content": "Intro [[IMAGE: a glowing tree]] middle text.",
}


class TestGenerateStoryImagesNode:
    def test_uploads_cover_and_inline_images(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch.object(story_images_mod, "_generate_image", return_value=(b"data", "image/jpeg")), \
             patch.object(story_images_mod, "_upload_image", side_effect=["https://server/cover.jpg", "https://server/inline.jpg"]), \
             patch.object(story_images_mod, "time") as mock_time:
            result = generate_story_images_node(STATE)
        assert result["featured_image_url"] == "https://server/cover.jpg"
        assert "https://server/inline.jpg" in result["final_content"]
        assert "[[IMAGE:" not in result["final_content"]

    def test_publishes_without_cover_when_generation_fails(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch.object(story_images_mod, "_generate_image", return_value=None):
            result = generate_story_images_node(STATE)
        assert result["featured_image_url"] is None

    def test_removes_placeholder_when_inline_image_fails(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch.object(story_images_mod, "_generate_image", side_effect=[(b"data", "image/jpeg"), None]), \
             patch.object(story_images_mod, "_upload_image", return_value="https://server/cover.jpg"), \
             patch.object(story_images_mod, "time") as mock_time:
            result = generate_story_images_node(STATE)
        assert "[[IMAGE:" not in result["final_content"]

    def test_removes_placeholder_when_upload_throws(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch.object(story_images_mod, "_generate_image", return_value=(b"data", "image/jpeg")), \
             patch.object(story_images_mod, "_upload_image", side_effect=["https://server/cover.jpg", Exception("boom")]), \
             patch.object(story_images_mod, "time") as mock_time:
            result = generate_story_images_node(STATE)
        assert "[[IMAGE:" not in result["final_content"]

    def test_no_inline_processing_without_placeholders(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        state = {**STATE, "story_content": "No placeholders."}
        with patch.object(story_images_mod, "_generate_image", return_value=(b"data", "image/jpeg")), \
             patch.object(story_images_mod, "_upload_image", return_value="https://server/cover.jpg"):
            result = generate_story_images_node(state)
        assert result["final_content"] == "No placeholders."
