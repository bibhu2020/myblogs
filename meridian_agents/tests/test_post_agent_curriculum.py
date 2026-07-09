from unittest.mock import MagicMock, patch

from meridian_agents.post_agent.nodes.curriculum import _next_topic, resolve_curriculum_node
from meridian_agents.post_agent.nodes.research import EDUCATIONAL_TRACKS


def _resp(json_data):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = json_data
    return r


class TestNextTopic:
    def test_starts_at_general_relativity_topic_zero_when_no_posts_exist(self):
        series_key, series_index, topic = _next_topic([])
        assert series_key == "general-relativity"
        assert series_index == 0
        assert topic == EDUCATIONAL_TRACKS["general-relativity"][0]

    def test_round_robins_to_the_least_progressed_track(self):
        posts = [
            {"seriesKey": "general-relativity", "seriesIndex": 2},
            {"seriesKey": "special-relativity", "seriesIndex": 0},
        ]
        # quantum-physics hasn't been touched at all (-1) so it's least progressed
        series_key, series_index, _ = _next_topic(posts)
        assert series_key == "quantum-physics"
        assert series_index == 0

    def test_advances_within_a_track_from_its_highest_published_index(self):
        posts = [
            {"seriesKey": "general-relativity", "seriesIndex": 3},
            {"seriesKey": "special-relativity", "seriesIndex": 3},
            {"seriesKey": "quantum-physics", "seriesIndex": 5},
        ]
        # general-relativity and special-relativity are tied at 3 — fixed tie-break order
        # picks general-relativity first.
        series_key, series_index, topic = _next_topic(posts)
        assert series_key == "general-relativity"
        assert series_index == 4
        assert topic == EDUCATIONAL_TRACKS["general-relativity"][4]

    def test_wraps_and_frames_as_a_revisit_when_a_track_is_exhausted(self):
        last_index = len(EDUCATIONAL_TRACKS["general-relativity"]) - 1
        posts = [
            {"seriesKey": "general-relativity", "seriesIndex": last_index},
            {"seriesKey": "special-relativity", "seriesIndex": last_index},
            {"seriesKey": "quantum-physics", "seriesIndex": last_index},
        ]
        series_key, series_index, topic = _next_topic(posts)
        assert series_key == "general-relativity"
        assert series_index == last_index + 1
        assert topic.startswith("Revisiting and synthesizing:")

    def test_ignores_posts_with_unknown_or_missing_series_keys(self):
        posts = [{"seriesKey": None, "seriesIndex": None}, {"seriesKey": "unknown-track", "seriesIndex": 9}]
        series_key, series_index, _ = _next_topic(posts)
        assert series_key == "general-relativity"
        assert series_index == 0


class TestResolveCurriculumNode:
    def test_returns_next_topic_from_published_educational_posts(self):
        with patch("meridian_agents.post_agent.nodes.curriculum.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = _resp({"posts": [{"seriesKey": "general-relativity", "seriesIndex": 0}]})
            result = resolve_curriculum_node({"server_base": "https://server"})
        assert result["series_key"] == "special-relativity"
        assert result["series_index"] == 0
        assert result["series_topic"] == EDUCATIONAL_TRACKS["special-relativity"][0]

    def test_queries_the_educational_published_posts_endpoint_with_admin_auth(self):
        with patch("meridian_agents.post_agent.nodes.curriculum.httpx.Client") as MockClient, \
             patch("meridian_agents.post_agent.nodes.curriculum.make_agent_jwt", return_value="jwt-token"):
            client = MockClient.return_value.__enter__.return_value
            client.get.return_value = _resp([])
            resolve_curriculum_node({"server_base": "https://server"})
        args, kwargs = client.get.call_args
        assert args[0] == "https://server/api/posts/admin"
        assert kwargs["params"] == {"category": "educational", "status": "published", "limit": 200}
        assert kwargs["headers"]["Authorization"] == "Bearer jwt-token"

    def test_falls_back_to_track_start_when_lookup_fails(self):
        with patch("meridian_agents.post_agent.nodes.curriculum.httpx.Client") as MockClient:
            client = MockClient.return_value.__enter__.return_value
            client.get.side_effect = Exception("network down")
            result = resolve_curriculum_node({"server_base": "https://server"})
        assert result["series_key"] == "general-relativity"
        assert result["series_index"] == 0
        assert result["series_topic"] == EDUCATIONAL_TRACKS["general-relativity"][0]
