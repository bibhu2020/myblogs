from unittest.mock import patch, MagicMock

from meridian_agents.news_agent.publisher import save_news_items


class TestSaveNewsItems:
    def test_posts_items_and_returns_response_json(self):
        with patch("meridian_agents.news_agent.publisher.make_agent_jwt", return_value="jwt"), \
             patch("meridian_agents.news_agent.publisher.requests.post") as mock_post:
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"count": 2}
            mock_post.return_value = resp
            result = save_news_items([{"title": "A"}, {"title": "B"}])
        assert result == {"count": 2}
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["items"] == [{"title": "A"}, {"title": "B"}]
