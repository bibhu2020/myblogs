from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from io import BytesIO
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from meridian_agents.news_agent import tools as tools_mod
from meridian_agents.news_agent.tools import (
    _is_within_hours,
    _rss_image,
    _fetch_og_image,
    _parse_feed,
    fetch_region_news,
    _validate_image,
    _download_image,
    _enhance_thumbnail,
    _upload_to_media,
    _fetch_item_image,
    _enhance_all_images,
    _synthesize_and_upload_audio,
    _generate_all_audio,
)


def _png_bytes(size=(200, 200), color=(200, 50, 50)):
    # A solid-colour PNG compresses to well under _MIN_BYTES (4096); fill with
    # per-pixel noise so the encoded size realistically exceeds that floor.
    import random
    buf = BytesIO()
    img = Image.new("RGB", size)
    px = img.load()
    for x in range(size[0]):
        for y in range(size[1]):
            px[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestIsWithinHours:
    def test_true_for_missing_date(self):
        assert _is_within_hours(None) is True

    def test_true_for_recent_date(self):
        recent = format_datetime(datetime.now(timezone.utc) - timedelta(hours=1))
        assert _is_within_hours(recent, hours=36) is True

    def test_false_for_old_date(self):
        old = format_datetime(datetime.now(timezone.utc) - timedelta(hours=100))
        assert _is_within_hours(old, hours=36) is False

    def test_true_for_unparseable_date(self):
        assert _is_within_hours("not a date") is True


class TestRssImage:
    def test_prefers_media_content(self):
        entry = MagicMock(media_content=[{"url": "https://img/a.jpg"}])
        assert _rss_image(entry) == "https://img/a.jpg"

    def test_falls_back_to_image_enclosure(self):
        entry = MagicMock(
            media_content=None,
            enclosures=[{"type": "image/jpeg", "href": "https://img/b.jpg"}],
        )
        assert _rss_image(entry) == "https://img/b.jpg"

    def test_falls_back_to_media_thumbnail(self):
        entry = MagicMock(media_content=None, enclosures=None, media_thumbnail=[{"url": "https://img/c.jpg"}])
        assert _rss_image(entry) == "https://img/c.jpg"

    def test_returns_none_when_nothing_present(self):
        entry = MagicMock(media_content=None, enclosures=None, media_thumbnail=None)
        assert _rss_image(entry) is None


class TestFetchOgImage:
    def test_extracts_og_image(self):
        html = '<meta property="og:image" content="https://example.com/a.jpg">'
        with patch("meridian_agents.news_agent.tools.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, text=html)
            assert _fetch_og_image("https://article") == "https://example.com/a.jpg"

    def test_extracts_twitter_image_as_fallback(self):
        html = '<meta name="twitter:image" content="https://example.com/b.jpg">'
        with patch("meridian_agents.news_agent.tools.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, text=html)
            assert _fetch_og_image("https://article") == "https://example.com/b.jpg"

    def test_returns_none_on_non_200(self):
        with patch("meridian_agents.news_agent.tools.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=404)
            assert _fetch_og_image("https://article") is None

    def test_returns_none_when_no_match(self):
        with patch("meridian_agents.news_agent.tools.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, text="<html></html>")
            assert _fetch_og_image("https://article") is None

    def test_returns_none_on_exception(self):
        with patch("meridian_agents.news_agent.tools.requests.get", side_effect=Exception("timeout")):
            assert _fetch_og_image("https://article") is None


class TestParseFeed:
    def test_normalises_entries(self):
        fake_feed = MagicMock()
        fake_feed.entries = [
            MagicMock(
                get=lambda k, d=None: {"title": "Headline", "link": "https://a", "summary": "<p>body</p>", "published": "2026-01-01"}.get(k, d),
                media_content=None, enclosures=None, media_thumbnail=None,
            )
        ]
        with patch("meridian_agents.news_agent.tools.feedparser.parse", return_value=fake_feed):
            result = _parse_feed("Source", "https://feed", "world")
        assert result[0]["title"] == "Headline"
        assert result[0]["body"] == "body"
        assert result[0]["region"] == "world"

    def test_skips_entries_without_title_or_link(self):
        fake_feed = MagicMock()
        fake_feed.entries = [MagicMock(get=lambda k, d=None: {"title": "", "link": "https://a"}.get(k, d))]
        with patch("meridian_agents.news_agent.tools.feedparser.parse", return_value=fake_feed):
            assert _parse_feed("Source", "https://feed", "world") == []

    def test_returns_empty_list_on_exception(self):
        with patch("meridian_agents.news_agent.tools.feedparser.parse", side_effect=Exception("down")):
            assert _parse_feed("Source", "https://feed", "world") == []


class TestFetchRegionNews:
    def test_returns_empty_for_unknown_region(self):
        assert fetch_region_news("mars") == []

    def test_aggregates_deduplicates_and_sorts(self):
        recent = format_datetime(datetime.now(timezone.utc) - timedelta(hours=1))
        older = format_datetime(datetime.now(timezone.utc) - timedelta(hours=2))
        articles = [
            {"title": "Same Story", "url": "u1", "body": "b", "image": None, "date": older, "source": "A", "region": "ai"},
            {"title": "Same Story", "url": "u2", "body": "b", "image": None, "date": recent, "source": "B", "region": "ai"},
            {"title": "Different Story", "url": "u3", "body": "b", "image": None, "date": recent, "source": "C", "region": "ai"},
        ]
        with patch.object(tools_mod, "_parse_feed", return_value=articles):
            result = fetch_region_news("ai", max_results=10)
        titles = [a["title"] for a in result]
        assert titles.count("Same Story") == 1  # deduplicated, first-seen kept
        assert "Different Story" in titles


class TestValidateImage:
    def test_rejects_tiny_payloads(self):
        assert _validate_image(b"x" * 10) == (False, "")

    def test_accepts_a_real_image(self):
        ok, mime = _validate_image(_png_bytes())
        assert ok is True
        assert mime == "image/png"

    def test_rejects_undersized_images(self):
        ok, mime = _validate_image(_png_bytes(size=(10, 10)))
        assert ok is False

    def test_rejects_malformed_data(self):
        assert _validate_image(b"not an image" * 500) == (False, "")


class TestDownloadImage:
    def test_returns_none_for_empty_url(self):
        assert _download_image("") is None

    def test_downloads_and_validates(self):
        with patch("meridian_agents.news_agent.tools.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, headers={"content-type": "image/png"}, content=_png_bytes())
            result = _download_image("https://img")
        assert result is not None
        assert result[1] == "image/png"

    def test_returns_none_for_non_200(self):
        with patch("meridian_agents.news_agent.tools.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=500)
            assert _download_image("https://img") is None

    def test_returns_none_for_non_image_content_type(self):
        with patch("meridian_agents.news_agent.tools.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, headers={"content-type": "text/html"})
            assert _download_image("https://img") is None

    def test_returns_none_on_exception(self):
        with patch("meridian_agents.news_agent.tools.requests.get", side_effect=Exception("timeout")):
            assert _download_image("https://img") is None


class TestEnhanceThumbnail:
    def test_crops_and_resizes_a_wide_image(self):
        result = _enhance_thumbnail(_png_bytes(size=(2000, 500)))
        img = Image.open(BytesIO(result))
        assert img.size == (800, 450)

    def test_crops_and_resizes_a_tall_image(self):
        result = _enhance_thumbnail(_png_bytes(size=(500, 2000)))
        img = Image.open(BytesIO(result))
        assert img.size == (800, 450)

    def test_handles_rgba_images(self):
        buf = BytesIO()
        Image.new("RGBA", (900, 500), (10, 20, 30, 128)).save(buf, format="PNG")
        result = _enhance_thumbnail(buf.getvalue())
        img = Image.open(BytesIO(result))
        assert img.size == (800, 450)

    def test_returns_original_bytes_on_error(self):
        garbage = b"not an image" * 500
        assert _enhance_thumbnail(garbage) == garbage


class TestUploadToMedia:
    def test_returns_the_uploaded_url(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch.object(tools_mod, "make_agent_jwt", return_value="jwt"), \
             patch("meridian_agents.news_agent.tools.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, json=lambda: {"url": "/uploads/x.jpg"})
            assert _upload_to_media(b"data", "image/jpeg", "alt") == "/uploads/x.jpg"

    def test_returns_none_when_upload_fails(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch.object(tools_mod, "make_agent_jwt", return_value="jwt"), \
             patch("meridian_agents.news_agent.tools.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=False)
            assert _upload_to_media(b"data", "image/jpeg", "alt") is None

    def test_returns_none_on_exception(self):
        with patch.object(tools_mod, "make_agent_jwt", side_effect=Exception("boom")):
            assert _upload_to_media(b"data", "image/jpeg", "alt") is None


class TestFetchItemImage:
    def test_uses_rss_image_when_it_works(self):
        # og:image is scraped unconditionally to build the candidate list, but
        # candidates are tried in order (RSS image first) and the loop returns
        # on the first success — so a working RSS image still wins even though
        # _fetch_og_image was called too.
        item = {"sourceUrl": "https://article", "imageUrl": "https://rss-img", "title": "Headline"}
        with patch.object(tools_mod, "_fetch_og_image", return_value="https://og-img"), \
             patch.object(tools_mod, "_download_image", return_value=(_png_bytes(), "image/png")), \
             patch.object(tools_mod, "_enhance_thumbnail", return_value=b"enhanced"), \
             patch.object(tools_mod, "_upload_to_media", return_value="https://hosted/img.jpg") as mock_upload:
            idx, url = _fetch_item_image((0, item))
        assert url == "https://hosted/img.jpg"
        mock_upload.assert_called_once()  # only the winning (first) candidate is uploaded

    def test_falls_back_to_og_image_scrape(self):
        item = {"sourceUrl": "https://article", "imageUrl": None, "title": "Headline"}
        with patch.object(tools_mod, "_fetch_og_image", return_value="https://og-img"), \
             patch.object(tools_mod, "_download_image", return_value=(_png_bytes(), "image/png")), \
             patch.object(tools_mod, "_enhance_thumbnail", return_value=b"enhanced"), \
             patch.object(tools_mod, "_upload_to_media", return_value="https://hosted/img.jpg"):
            idx, url = _fetch_item_image((1, item))
        assert url == "https://hosted/img.jpg"

    def test_returns_none_when_all_candidates_fail(self):
        item = {"sourceUrl": "https://article", "imageUrl": "https://rss-img", "title": "Headline"}
        with patch.object(tools_mod, "_fetch_og_image", return_value=None), \
             patch.object(tools_mod, "_download_image", return_value=None):
            idx, url = _fetch_item_image((2, item))
        assert url is None


class TestEnhanceAllImages:
    def test_returns_items_unchanged_when_empty(self):
        assert _enhance_all_images([]) == []

    def test_fills_in_image_urls_for_every_item(self):
        items = [{"title": "A", "imageUrl": None}, {"title": "B", "imageUrl": "https://x"}]
        with patch.object(tools_mod, "_fetch_item_image", side_effect=lambda pair: (pair[0], f"https://hosted/{pair[0]}.jpg")):
            result = _enhance_all_images(items)
        assert result[0]["imageUrl"] == "https://hosted/0.jpg"
        assert result[1]["imageUrl"] == "https://hosted/1.jpg"
        # original list must not be mutated
        assert items[0]["imageUrl"] is None


class TestSynthesizeAndUploadAudio:
    def test_returns_the_uploaded_url(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        item = {"title": "Headline", "summary": "Something happened."}
        with patch.object(tools_mod, "make_agent_jwt", return_value="jwt-token"), \
             patch("meridian_agents.news_agent.tools.requests.post") as mock_post:
            mock_post.side_effect = [
                MagicMock(content=b"x" * 2048, raise_for_status=lambda: None),
                MagicMock(ok=True, json=lambda: {"url": "https://server/uploads/news-3.mp3"}),
            ]
            idx, url = _synthesize_and_upload_audio((3, item))
        assert idx == 3
        assert url == "https://server/uploads/news-3.mp3"
        tts_call = mock_post.call_args_list[0]
        assert tts_call.args[0] == "https://server/api/tts"
        assert tts_call.kwargs["json"] == {
            "text": "Headline. Something happened.", "style": "news", "format": "mp3",
        }

    def test_returns_none_when_tts_request_fails(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch("meridian_agents.news_agent.tools.requests.post", side_effect=Exception("tts down")):
            idx, url = _synthesize_and_upload_audio((0, {"title": "A", "summary": "B"}))
        assert idx == 0
        assert url is None

    def test_returns_none_when_synthesis_produces_almost_no_audio(self, monkeypatch):
        monkeypatch.setenv("SERVER_BASE", "https://server")
        with patch("meridian_agents.news_agent.tools.requests.post") as mock_post:
            mock_post.return_value = MagicMock(content=b"x" * 10, raise_for_status=lambda: None)
            idx, url = _synthesize_and_upload_audio((1, {"title": "A", "summary": "B"}))
        assert idx == 1
        assert url is None

    def test_returns_none_for_empty_text(self):
        idx, url = _synthesize_and_upload_audio((0, {"title": "", "summary": ""}))
        assert idx == 0
        assert url is None


class TestGenerateAllAudio:
    def test_returns_items_unchanged_when_empty(self):
        assert _generate_all_audio([]) == []

    def test_assigns_sort_order_and_audio_url_for_every_item(self):
        items = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
        with patch.object(tools_mod, "_synthesize_and_upload_audio",
                           side_effect=lambda pair: (pair[0], f"https://hosted/news-{pair[0]}.mp3")):
            result = _generate_all_audio(items)
        assert [it["sortOrder"] for it in result] == [0, 1, 2]
        assert [it["audioUrl"] for it in result] == [
            "https://hosted/news-0.mp3", "https://hosted/news-1.mp3", "https://hosted/news-2.mp3",
        ]
        # original list must not be mutated
        assert "sortOrder" not in items[0]

    def test_leaves_audio_url_none_for_items_that_fail(self):
        items = [{"title": "A"}, {"title": "B"}]
        with patch.object(tools_mod, "_synthesize_and_upload_audio",
                           side_effect=[(0, None), (1, "https://hosted/news-1.mp3")]):
            result = _generate_all_audio(items)
        by_order = {it["sortOrder"]: it["audioUrl"] for it in result}
        assert by_order[0] is None
        assert by_order[1] == "https://hosted/news-1.mp3"
