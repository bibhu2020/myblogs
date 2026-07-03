from io import BytesIO
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from meridian_agents.post_agent.nodes import images as images_mod
from meridian_agents.post_agent.nodes.images import (
    _is_good_image,
    _upload_image,
    _hf_infer,
    _try_flux_dev,
    _try_flux,
    _try_gemini,
    _try_unsplash,
    _generate_image,
    generate_images_node,
)


def _png_bytes(size=(100, 100), color=(255, 0, 0)):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _noisy_png_bytes(size=(100, 100)):
    import random
    img = Image.new("RGB", size)
    px = img.load()
    for x in range(size[0]):
        for y in range(size[1]):
            v = random.randint(0, 255)
            px[x, y] = (v, v, v)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestIsGoodImage:
    def test_rejects_tiny_payloads(self):
        assert _is_good_image(b"x" * 100) is False

    def test_rejects_solid_colour_images(self):
        assert _is_good_image(_png_bytes(color=(128, 128, 128))) is False

    def test_accepts_images_with_variance(self):
        assert _is_good_image(_noisy_png_bytes()) is True

    def test_accepts_unparseable_data_as_a_safe_default(self):
        assert _is_good_image(b"not a real image" * 200) is True


class TestUploadImage:
    def test_returns_the_uploaded_url(self):
        with patch.object(images_mod, "make_agent_jwt", return_value="jwt-token"), \
             patch("meridian_agents.post_agent.nodes.images.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, json=lambda: {"url": "/uploads/x.jpg"})
            url = _upload_image(b"data", "image/jpeg", "alt text", "https://server")
        assert url == "/uploads/x.jpg"

    def test_raises_when_upload_fails(self):
        with patch.object(images_mod, "make_agent_jwt", return_value="jwt-token"), \
             patch("meridian_agents.post_agent.nodes.images.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=False, status_code=500, text="server error")
            with pytest.raises(RuntimeError, match="Upload failed"):
                _upload_image(b"data", "image/jpeg", "alt", "https://server")

    def test_raises_when_response_has_no_url(self):
        with patch.object(images_mod, "make_agent_jwt", return_value="jwt-token"), \
             patch("meridian_agents.post_agent.nodes.images.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, json=lambda: {}, text="{}")
            with pytest.raises(RuntimeError, match="missing url"):
                _upload_image(b"data", "image/jpeg", "alt", "https://server")


class TestHfInfer:
    def test_raises_without_a_token(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        with pytest.raises(RuntimeError, match="HF_TOKEN"):
            _hf_infer("some/model", {})

    def test_returns_response_on_success(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "tok")
        with patch("meridian_agents.post_agent.nodes.images.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            res = _hf_infer("some/model", {})
        assert res.status_code == 200

    def test_retries_once_on_503(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "tok")
        first = MagicMock(status_code=503, json=lambda: {"estimated_time": 1})
        second = MagicMock(status_code=200)
        with patch("meridian_agents.post_agent.nodes.images.requests.post", side_effect=[first, second]), \
             patch("meridian_agents.post_agent.nodes.images.time.sleep") as mock_sleep:
            res = _hf_infer("some/model", {})
        assert res.status_code == 200
        mock_sleep.assert_called_once()


class TestTryFluxDev:
    def test_uses_flux_dev_when_available(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "tok")
        response = MagicMock(status_code=200, content=b"imgdata", headers={"content-type": "image/jpeg"})
        with patch.object(images_mod, "_hf_infer", return_value=response) as mock_infer:
            buf, mime = _try_flux_dev("a prompt")
        assert buf == b"imgdata"
        assert mime == "image/jpeg"
        assert mock_infer.call_count == 1

    def test_falls_back_to_schnell_on_410(self, monkeypatch):
        import requests as real_requests
        http_err = real_requests.HTTPError()
        http_err.response = MagicMock(status_code=410)
        schnell_response = MagicMock(content=b"schnell-data", headers={"content-type": "image/jpeg"})
        with patch.object(images_mod, "_hf_infer", side_effect=[http_err, schnell_response]):
            buf, mime = _try_flux_dev("a prompt")
        assert buf == b"schnell-data"

    def test_reraises_unexpected_http_errors(self):
        import requests as real_requests
        http_err = real_requests.HTTPError()
        http_err.response = MagicMock(status_code=403)
        with patch.object(images_mod, "_hf_infer", side_effect=http_err):
            with pytest.raises(real_requests.HTTPError):
                _try_flux_dev("a prompt")


class TestTryFlux:
    def test_returns_image_bytes(self):
        response = MagicMock(content=b"data", headers={"content-type": "image/jpeg"})
        with patch.object(images_mod, "_hf_infer", return_value=response):
            buf, mime = _try_flux("a prompt")
        assert buf == b"data"


class TestTryGemini:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            _try_gemini("prompt")

    def test_generates_an_image_via_imagen(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = MagicMock(text="enhanced prompt")
        fake_image = MagicMock()
        fake_image.image.image_bytes = b"imagen-bytes"
        fake_client.models.generate_images.return_value = MagicMock(generated_images=[fake_image])
        with patch("google.genai.Client", return_value=fake_client):
            buf, mime = _try_gemini("prompt")
        assert buf == b"imagen-bytes"
        assert mime == "image/jpeg"

    def test_falls_back_to_original_prompt_when_enhancement_fails(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        fake_client = MagicMock()
        fake_client.models.generate_content.side_effect = Exception("enhance failed")
        fake_image = MagicMock()
        fake_image.image.image_bytes = b"imagen-bytes"
        fake_client.models.generate_images.return_value = MagicMock(generated_images=[fake_image])
        with patch("google.genai.Client", return_value=fake_client):
            buf, mime = _try_gemini("prompt")
        assert buf == b"imagen-bytes"

    def test_raises_when_all_imagen_models_fail(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = MagicMock(text="")
        fake_client.models.generate_images.side_effect = Exception("quota exceeded")
        with patch("google.genai.Client", return_value=fake_client):
            with pytest.raises(RuntimeError, match="Gemini Imagen"):
                _try_gemini("prompt")


class TestTryUnsplash:
    def test_raises_without_access_key(self, monkeypatch):
        monkeypatch.delenv("UNSPLASH_ACCESS_KEY", raising=False)
        with pytest.raises(RuntimeError, match="UNSPLASH_ACCESS_KEY"):
            _try_unsplash("topic")

    def test_downloads_the_photo_and_returns_credit(self, monkeypatch):
        monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "key")
        search_resp = MagicMock()
        search_resp.raise_for_status.return_value = None
        search_resp.json.return_value = {
            "urls": {"regular": "https://images.unsplash.com/photo.jpg"},
            "user": {"name": "Jane Photographer"},
        }
        img_resp = MagicMock()
        img_resp.raise_for_status.return_value = None
        img_resp.content = b"photo-bytes"
        img_resp.headers = {"content-type": "image/jpeg"}
        with patch("meridian_agents.post_agent.nodes.images.requests.get", side_effect=[search_resp, img_resp]):
            buf, mime, credit = _try_unsplash("Paris travel")
        assert buf == b"photo-bytes"
        assert credit == "Jane Photographer"


class TestGenerateImage:
    def test_travel_category_uses_unsplash_first(self):
        with patch.object(images_mod, "_try_unsplash", return_value=(_noisy_png_bytes(), "image/jpeg", "Credit")) as mock_unsplash:
            result = _generate_image("prompt", category="Travel", unsplash_query="paris")
        assert result is not None
        mock_unsplash.assert_called_once()

    def test_travel_falls_back_to_ai_when_unsplash_fails(self):
        with patch.object(images_mod, "_try_unsplash", side_effect=Exception("no key")) as mock_unsplash, \
             patch.object(images_mod, "_try_gemini", return_value=(_noisy_png_bytes(), "image/jpeg")):
            result = _generate_image("prompt", category="Travel", unsplash_query="paris")
        assert result is not None

    def test_tries_providers_in_order_until_one_succeeds(self):
        with patch.object(images_mod, "_try_gemini", side_effect=Exception("no key")), \
             patch.object(images_mod, "_try_flux_dev", return_value=(_noisy_png_bytes(), "image/jpeg")) as mock_flux_dev:
            result = _generate_image("prompt", category="Tech")
        assert result is not None
        mock_flux_dev.assert_called_once()

    def test_skips_providers_that_return_bad_images(self):
        with patch.object(images_mod, "_try_gemini", return_value=(_png_bytes(color=(1, 1, 1)), "image/jpeg")), \
             patch.object(images_mod, "_try_flux_dev", side_effect=Exception("fail")), \
             patch.object(images_mod, "_try_flux", return_value=(_noisy_png_bytes(), "image/jpeg")):
            result = _generate_image("prompt", category="Tech")
        assert result is not None

    def test_falls_back_to_unsplash_stock_when_all_ai_providers_fail(self):
        with patch.object(images_mod, "_try_gemini", side_effect=Exception("fail")), \
             patch.object(images_mod, "_try_flux_dev", side_effect=Exception("fail")), \
             patch.object(images_mod, "_try_flux", side_effect=Exception("fail")), \
             patch.object(images_mod, "_try_unsplash", return_value=(_noisy_png_bytes(), "image/jpeg", None)):
            result = _generate_image("prompt", category="Tech")
        assert result is not None

    def test_returns_none_when_everything_fails(self):
        with patch.object(images_mod, "_try_gemini", side_effect=Exception("fail")), \
             patch.object(images_mod, "_try_flux_dev", side_effect=Exception("fail")), \
             patch.object(images_mod, "_try_flux", side_effect=Exception("fail")), \
             patch.object(images_mod, "_try_unsplash", side_effect=Exception("fail")):
            result = _generate_image("prompt", category="Tech")
        assert result is None


class TestGenerateImagesNode:
    STATE = {
        "category_name": "Tech",
        "post_featured_image_prompt": "A robot",
        "post_unsplash_query": None,
        "post_content": 'Intro text [[IMAGE: a diagram of the system]] more text.',
    }

    def test_uploads_featured_and_inline_images(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch.object(images_mod, "_generate_image", return_value=(b"data", "image/jpeg")), \
             patch.object(images_mod, "_upload_image", side_effect=["https://server/featured.jpg", "https://server/inline.jpg"]), \
             patch.object(images_mod, "time") as mock_time:
            result = generate_images_node(self.STATE)
        assert result["featured_image_url"] == "https://server/featured.jpg"
        assert "https://server/inline.jpg" in result["final_content"]
        assert "[[IMAGE:" not in result["final_content"]

    def test_removes_placeholder_when_image_generation_fails(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch.object(images_mod, "_generate_image", side_effect=[None, None]), \
             patch.object(images_mod, "time") as mock_time:
            result = generate_images_node(self.STATE)
        assert result["featured_image_url"] is None
        assert "[[IMAGE:" not in result["final_content"]

    def test_removes_placeholder_when_inline_upload_throws(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch.object(images_mod, "_generate_image", return_value=(b"data", "image/jpeg")), \
             patch.object(images_mod, "_upload_image", side_effect=["https://server/featured.jpg", Exception("upload failed")]), \
             patch.object(images_mod, "time") as mock_time:
            result = generate_images_node(self.STATE)
        assert "[[IMAGE:" not in result["final_content"]

    def test_no_inline_processing_when_no_placeholders(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        state = {**self.STATE, "post_content": "No placeholders here."}
        with patch.object(images_mod, "_generate_image", return_value=(b"data", "image/jpeg")), \
             patch.object(images_mod, "_upload_image", return_value="https://server/featured.jpg"):
            result = generate_images_node(state)
        assert result["final_content"] == "No placeholders here."
