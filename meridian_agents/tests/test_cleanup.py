from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from meridian_agents.cleanup import (
    _admin_token,
    _uploads_filename,
    _all_upload_filenames,
    _delete_media_by_filename,
    cleanup_old_posts,
    cleanup_old_stories,
    cleanup_empty_categories,
    cleanup_orphaned_media,
)


def _resp(json_data=None, raise_exc=None):
    r = MagicMock()
    r.json.return_value = json_data
    if raise_exc:
        r.raise_for_status.side_effect = raise_exc
    else:
        r.raise_for_status.return_value = None
    return r


class TestAdminToken:
    def test_uses_env_token_when_set(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "existing-token")
        assert _admin_token("https://server") == "existing-token"

    def test_logs_in_when_no_env_token(self, monkeypatch):
        monkeypatch.delenv("AGENT_JWT_TOKEN", raising=False)
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.return_value = _resp({"access_token": "fresh-token"})
            token = _admin_token("https://server")
        assert token == "fresh-token"


class TestAllUploadFilenames:
    def test_collects_featured_image_and_inline_images(self):
        item = {
            "featuredImage": "/uploads/hero.jpg",
            "content": '<p>intro</p><img src="/uploads/inline1.png" alt="">'
                       '<figure><img src="/uploads/inline2.png"/></figure>',
        }
        assert _all_upload_filenames(item) == ["hero.jpg", "inline1.png", "inline2.png"]

    def test_uses_custom_image_field_for_news_items(self):
        item = {"imageUrl": "/uploads/news.jpg"}
        assert _all_upload_filenames(item, image_field="imageUrl") == ["news.jpg"]

    def test_deduplicates_and_ignores_missing_fields(self):
        item = {"featuredImage": "/uploads/a.jpg", "content": '<img src="/uploads/a.jpg">'}
        assert _all_upload_filenames(item) == ["a.jpg"]

    def test_returns_empty_list_for_bare_item(self):
        assert _all_upload_filenames({}) == []


class TestUploadsFilename:
    def test_returns_none_for_missing_url(self):
        assert _uploads_filename(None) is None
        assert _uploads_filename("") is None

    def test_returns_none_when_no_uploads_segment(self):
        assert _uploads_filename("https://unsplash.com/photo.jpg") is None

    def test_extracts_filename_from_uploads_path(self):
        assert _uploads_filename("/uploads/abc123.jpg") == "abc123.jpg"

    def test_extracts_filename_ignoring_query_string(self):
        assert _uploads_filename("/uploads/abc123.jpg?w=200") == "abc123.jpg"

    def test_extracts_filename_from_github_raw_uploads_path(self):
        assert _uploads_filename(
            "https://raw.githubusercontent.com/bibhu2020/media/main/myblogs/uploads/abc123.jpg"
        ) == "abc123.jpg"

    def test_extracts_filename_from_github_raw_audio_path(self):
        assert _uploads_filename(
            "https://raw.githubusercontent.com/bibhu2020/media/main/myblogs/audio/narration-1.mp3"
        ) == "narration-1.mp3"


class TestDeleteMediaByFilename:
    def test_deletes_when_found_by_filename(self):
        client = MagicMock()
        client.get.return_value = _resp([{"id": 1, "filename": "abc.jpg"}])
        client.delete.return_value = _resp()
        _delete_media_by_filename(client, "https://server", "Bearer t", "abc.jpg")
        client.delete.assert_called_once_with(
            "https://server/api/media/1", headers={"Authorization": "Bearer t"}, timeout=20,
        )

    def test_deletes_when_found_by_url_suffix(self):
        client = MagicMock()
        client.get.return_value = _resp([{"id": 2, "url": "/uploads/abc.jpg"}])
        client.delete.return_value = _resp()
        _delete_media_by_filename(client, "https://server", "Bearer t", "abc.jpg")
        client.delete.assert_called_once()

    def test_handles_dict_response_shape(self):
        client = MagicMock()
        client.get.return_value = _resp({"media": [{"id": 3, "filename": "abc.jpg"}]})
        client.delete.return_value = _resp()
        _delete_media_by_filename(client, "https://server", "Bearer t", "abc.jpg")
        client.delete.assert_called_once()

    def test_does_nothing_when_not_found(self):
        client = MagicMock()
        client.get.return_value = _resp([{"id": 1, "filename": "other.jpg"}])
        _delete_media_by_filename(client, "https://server", "Bearer t", "abc.jpg")
        client.delete.assert_not_called()

    def test_swallows_errors(self):
        client = MagicMock()
        client.get.side_effect = Exception("network down")
        _delete_media_by_filename(client, "https://server", "Bearer t", "abc.jpg")  # must not raise


class TestCleanupOldPosts:
    def test_returns_zero_when_auth_fails(self, monkeypatch):
        monkeypatch.delenv("AGENT_JWT_TOKEN", raising=False)
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.side_effect = Exception("bad credentials")
            assert cleanup_old_posts("https://server") == 0

    def test_deletes_posts_older_than_cutoff(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        recent_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = _resp({
                "posts": [
                    {"id": 1, "title": "Old post", "createdAt": old_date, "featuredImage": "/uploads/a.jpg"},
                    {"id": 2, "title": "Recent post", "createdAt": recent_date},
                ]
            })
            client.delete.return_value = _resp()
            deleted = cleanup_old_posts("https://server", days=30)
        assert deleted == 1
        client.delete.assert_any_call(
            "https://server/api/posts/1", headers={"Authorization": "Bearer t"}, timeout=20,
        )

    def test_dry_run_does_not_delete(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = _resp({"posts": [{"id": 1, "title": "Old", "createdAt": old_date}]})
            deleted = cleanup_old_posts("https://server", days=30, dry_run=True)
        assert deleted == 0
        client.delete.assert_not_called()

    def test_skips_posts_with_missing_or_invalid_dates(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = _resp({"posts": [
                {"id": 1, "title": "No date"},
                {"id": 2, "title": "Bad date", "createdAt": "not-a-date"},
            ]})
            deleted = cleanup_old_posts("https://server", days=30)
        assert deleted == 0

    def test_continues_after_a_failed_delete(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = _resp({"posts": [
                {"id": 1, "title": "Old", "createdAt": old_date},
                {"id": 2, "title": "Old2", "createdAt": old_date},
            ]})
            client.delete.side_effect = [Exception("boom"), _resp()]
            deleted = cleanup_old_posts("https://server", days=30)
        assert deleted == 1

    def test_skips_posts_marked_do_not_delete(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = _resp({"posts": [
                {"id": 1, "title": "Kept", "createdAt": old_date, "doNotDelete": True},
                {"id": 2, "title": "Not kept", "createdAt": old_date, "doNotDelete": False},
            ]})
            client.delete.return_value = _resp()
            deleted = cleanup_old_posts("https://server", days=30)
        assert deleted == 1
        client.delete.assert_called_once_with(
            "https://server/api/posts/2", headers={"Authorization": "Bearer t"}, timeout=20,
        )

    def test_handles_list_response_shape(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = _resp([{"id": 1, "title": "Old", "createdAt": old_date}])
            client.delete.return_value = _resp()
            deleted = cleanup_old_posts("https://server", days=30)
        assert deleted == 1

    def test_swallows_top_level_errors(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = Exception("down")
            assert cleanup_old_posts("https://server") == 0


class TestCleanupOldStories:
    def test_returns_zero_when_auth_fails(self, monkeypatch):
        monkeypatch.delenv("AGENT_JWT_TOKEN", raising=False)
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.side_effect = Exception("bad credentials")
            assert cleanup_old_stories("https://server") == 0

    def test_only_deletes_published_stories_older_than_cutoff(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = _resp({"stories": [
                {"id": 1, "title": "Old", "status": "published", "createdAt": old_date, "featuredImage": "/uploads/b.jpg"},
                {"id": 2, "title": "Draft", "status": "draft", "createdAt": old_date},
            ]})
            client.delete.return_value = _resp()
            deleted = cleanup_old_stories("https://server", days=30)
        assert deleted == 1
        client.delete.assert_any_call(
            "https://server/api/stories/1", headers={"Authorization": "Bearer t"}, timeout=20,
        )

    def test_dry_run_does_not_delete(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = _resp({"stories": [{"id": 1, "status": "published", "createdAt": old_date}]})
            deleted = cleanup_old_stories("https://server", days=30, dry_run=True)
        assert deleted == 0
        client.delete.assert_not_called()

    def test_skips_stories_marked_do_not_delete(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = _resp({"stories": [
                {"id": 1, "title": "Kept", "status": "published", "createdAt": old_date, "doNotDelete": True},
                {"id": 2, "title": "Not kept", "status": "published", "createdAt": old_date, "doNotDelete": False},
            ]})
            client.delete.return_value = _resp()
            deleted = cleanup_old_stories("https://server", days=30)
        assert deleted == 1
        client.delete.assert_called_once_with(
            "https://server/api/stories/2", headers={"Authorization": "Bearer t"}, timeout=20,
        )

    def test_swallows_top_level_errors(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = Exception("down")
            assert cleanup_old_stories("https://server") == 0


class TestCleanupEmptyCategories:
    def test_returns_zero_when_auth_fails(self, monkeypatch):
        monkeypatch.delenv("AGENT_JWT_TOKEN", raising=False)
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.side_effect = Exception("bad credentials")
            assert cleanup_empty_categories("https://server") == 0

    def test_skips_fixed_categories_entirely(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = _resp([
                {"id": 1, "name": "Technology", "slug": "technology"},
                {"id": 2, "name": "Educational", "slug": "educational"},
                {"id": 3, "name": "History", "slug": "history"},
            ])
            deleted = cleanup_empty_categories("https://server")
        assert deleted == 0
        # Only the initial /api/categories GET — no per-category lookups needed.
        assert client.get.call_count == 1
        client.delete.assert_not_called()

    def test_deletes_a_non_fixed_category_with_zero_posts(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = [
                _resp([{"id": 5, "name": "Knowledge", "slug": "knowledge"}]),
                _resp({"total": 0}),
            ]
            client.delete.return_value = _resp()
            deleted = cleanup_empty_categories("https://server")
        assert deleted == 1
        client.delete.assert_called_once_with(
            "https://server/api/categories/5", headers={"Authorization": "Bearer t"}, timeout=20,
        )

    def test_keeps_a_non_fixed_category_that_still_has_posts(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = [
                _resp([{"id": 5, "name": "Knowledge", "slug": "knowledge"}]),
                _resp({"total": 2}),
            ]
            deleted = cleanup_empty_categories("https://server")
        assert deleted == 0
        client.delete.assert_not_called()

    def test_dry_run_does_not_delete(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = [
                _resp([{"id": 5, "name": "Knowledge", "slug": "knowledge"}]),
                _resp({"total": 0}),
            ]
            deleted = cleanup_empty_categories("https://server", dry_run=True)
        assert deleted == 0
        client.delete.assert_not_called()

    def test_swallows_top_level_errors(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = Exception("down")
            assert cleanup_empty_categories("https://server") == 0


class TestCleanupOrphanedMedia:
    NO_POSTS = _resp({"posts": []})
    NO_STORIES = _resp({"stories": []})
    NO_NEWS = _resp({"items": []})

    def test_returns_zero_when_auth_fails(self, monkeypatch):
        monkeypatch.delenv("AGENT_JWT_TOKEN", raising=False)
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.post.side_effect = Exception("bad credentials")
            assert cleanup_orphaned_media("https://server") == 0

    def test_deletes_media_not_referenced_anywhere(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = [
                self.NO_POSTS, self.NO_STORIES, self.NO_NEWS,
                _resp([{"id": 1, "filename": "orphan.jpg"}]),
            ]
            client.delete.return_value = _resp()
            deleted = cleanup_orphaned_media("https://server")
        assert deleted == 1
        client.delete.assert_called_once_with(
            "https://server/api/media/1", headers={"Authorization": "Bearer t"}, timeout=20,
        )

    def test_keeps_media_referenced_by_a_post_featured_image(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = [
                _resp({"posts": [{"id": 1, "featuredImage": "/uploads/kept.jpg"}]}),
                self.NO_STORIES, self.NO_NEWS,
                _resp([{"id": 1, "filename": "kept.jpg"}]),
            ]
            deleted = cleanup_orphaned_media("https://server")
        assert deleted == 0
        client.delete.assert_not_called()

    def test_keeps_media_referenced_by_inline_post_content(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = [
                _resp({"posts": [{"id": 1, "content": '<img src="/uploads/inline.jpg">'}]}),
                self.NO_STORIES, self.NO_NEWS,
                _resp([{"id": 1, "filename": "inline.jpg"}]),
            ]
            deleted = cleanup_orphaned_media("https://server")
        assert deleted == 0
        client.delete.assert_not_called()

    def test_keeps_media_referenced_by_a_story(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = [
                self.NO_POSTS,
                _resp({"stories": [{"id": 1, "featuredImage": "/uploads/story.jpg"}]}),
                self.NO_NEWS,
                _resp([{"id": 1, "filename": "story.jpg"}]),
            ]
            deleted = cleanup_orphaned_media("https://server")
        assert deleted == 0
        client.delete.assert_not_called()

    def test_keeps_media_referenced_by_a_news_item(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = [
                self.NO_POSTS, self.NO_STORIES,
                _resp({"items": [{"id": 1, "imageUrl": "/uploads/news.jpg"}]}),
                _resp([{"id": 1, "filename": "news.jpg"}]),
            ]
            deleted = cleanup_orphaned_media("https://server")
        assert deleted == 0
        client.delete.assert_not_called()

    def test_falls_back_to_url_suffix_when_filename_missing(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = [
                self.NO_POSTS, self.NO_STORIES, self.NO_NEWS,
                _resp([{"id": 1, "url": "/uploads/orphan.jpg"}]),
            ]
            client.delete.return_value = _resp()
            deleted = cleanup_orphaned_media("https://server")
        assert deleted == 1

    def test_dry_run_does_not_delete(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = [
                self.NO_POSTS, self.NO_STORIES, self.NO_NEWS,
                _resp([{"id": 1, "filename": "orphan.jpg"}]),
            ]
            deleted = cleanup_orphaned_media("https://server", dry_run=True)
        assert deleted == 0
        client.delete.assert_not_called()

    def test_swallows_top_level_errors(self, monkeypatch):
        monkeypatch.setenv("AGENT_JWT_TOKEN", "t")
        with patch("meridian_agents.cleanup.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = Exception("down")
            assert cleanup_orphaned_media("https://server") == 0
