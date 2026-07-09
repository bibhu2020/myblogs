from unittest.mock import patch, MagicMock

import pytest

from meridian_agents.story_agent.nodes import audio as audio_mod
from meridian_agents.story_agent.nodes.audio import _upload_audio, generate_story_audio_node


class TestUploadAudio:
    def test_returns_the_uploaded_url(self):
        with patch.object(audio_mod, "make_agent_jwt", return_value="jwt-token"), \
             patch("meridian_agents.story_agent.nodes.audio.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, json=lambda: {"url": "/uploads/x.mp3"})
            url = _upload_audio(b"data", "My Story Title", "https://server")
        assert url == "/uploads/x.mp3"

    def test_sends_the_filename_as_a_query_param_when_provided(self):
        with patch.object(audio_mod, "make_agent_jwt", return_value="jwt-token"), \
             patch("meridian_agents.story_agent.nodes.audio.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, json=lambda: {"url": "/uploads/story_3.mp3"})
            _upload_audio(b"data", "alt", "https://server", filename="story_3")
        _, kwargs = mock_post.call_args
        assert kwargs["params"] == {"filename": "story_3"}
        assert kwargs["files"]["file"][0] == "story_3.mp3"

    def test_omits_the_filename_query_param_when_not_provided(self):
        with patch.object(audio_mod, "make_agent_jwt", return_value="jwt-token"), \
             patch("meridian_agents.story_agent.nodes.audio.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, json=lambda: {"url": "/uploads/x.mp3"})
            _upload_audio(b"data", "alt", "https://server")
        _, kwargs = mock_post.call_args
        assert kwargs["params"] == {}

    def test_raises_when_upload_fails(self):
        with patch.object(audio_mod, "make_agent_jwt", return_value="jwt-token"), \
             patch("meridian_agents.story_agent.nodes.audio.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=False, status_code=500, text="server error")
            with pytest.raises(RuntimeError, match="Upload failed"):
                _upload_audio(b"data", "alt", "https://server")

    def test_raises_when_response_has_no_url(self):
        with patch.object(audio_mod, "make_agent_jwt", return_value="jwt-token"), \
             patch("meridian_agents.story_agent.nodes.audio.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, json=lambda: {}, text="{}")
            with pytest.raises(RuntimeError, match="missing url"):
                _upload_audio(b"data", "alt", "https://server")


class TestGenerateStoryAudioNode:
    STATE = {
        "story_title": "The Brave Fox",
        "final_content": "<p>Hello <strong>world</strong>.</p>",
    }

    def test_synthesizes_and_uploads_narration(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch("meridian_agents.story_agent.nodes.audio.requests.post") as mock_post, \
             patch.object(audio_mod, "_upload_audio", return_value="https://server/uploads/narration.mp3") as mock_upload:
            mock_post.return_value = MagicMock(content=b"x" * 2048, raise_for_status=lambda: None)
            result = generate_story_audio_node(self.STATE)
        assert result["audio_url"] == "https://server/uploads/narration.mp3"
        tts_call = mock_post.call_args
        assert tts_call.args[0] == "https://server/api/tts"
        assert tts_call.kwargs["json"]["format"] == "mp3"
        assert tts_call.kwargs["json"]["style"] == "story"
        # HTML tags stripped before sending to TTS
        assert "<p>" not in tts_call.kwargs["json"]["text"]
        assert "Hello" in tts_call.kwargs["json"]["text"]
        mock_upload.assert_called_once()

    def test_names_the_mp3_by_the_story_id_once_it_exists(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        state = {**self.STATE, "pending_story_id": 7}
        with patch("meridian_agents.story_agent.nodes.audio.requests.post") as mock_post, \
             patch.object(audio_mod, "_upload_audio", return_value="https://server/uploads/story_7.mp3") as mock_upload:
            mock_post.return_value = MagicMock(content=b"x" * 2048, raise_for_status=lambda: None)
            generate_story_audio_node(state)
        assert mock_upload.call_args[0][3] == "story_7"

    def test_uses_no_filename_when_story_id_is_unknown(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch("meridian_agents.story_agent.nodes.audio.requests.post") as mock_post, \
             patch.object(audio_mod, "_upload_audio", return_value="https://server/uploads/x.mp3") as mock_upload:
            mock_post.return_value = MagicMock(content=b"x" * 2048, raise_for_status=lambda: None)
            generate_story_audio_node(self.STATE)
        assert mock_upload.call_args[0][3] is None

    def test_skips_gracefully_when_tts_request_fails(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch("meridian_agents.story_agent.nodes.audio.requests.post", side_effect=Exception("tts down")):
            result = generate_story_audio_node(self.STATE)
        assert result["audio_url"] is None

    def test_skips_gracefully_when_synthesis_produces_almost_no_audio(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch("meridian_agents.story_agent.nodes.audio.requests.post") as mock_post:
            mock_post.return_value = MagicMock(content=b"x" * 10, raise_for_status=lambda: None)
            result = generate_story_audio_node(self.STATE)
        assert result["audio_url"] is None

    def test_skips_gracefully_when_upload_fails(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch("meridian_agents.story_agent.nodes.audio.requests.post") as mock_post, \
             patch.object(audio_mod, "_upload_audio", side_effect=Exception("upload failed")):
            mock_post.return_value = MagicMock(content=b"x" * 2048, raise_for_status=lambda: None)
            result = generate_story_audio_node(self.STATE)
        assert result["audio_url"] is None

    def test_skips_when_content_has_no_text(self):
        result = generate_story_audio_node({**self.STATE, "final_content": "<img src='x.jpg'/>"})
        assert result["audio_url"] is None
