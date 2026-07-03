import json
from unittest.mock import patch, MagicMock

import pytest

from meridian_agents.post_agent import tracer as post_tracer
from meridian_agents.story_agent import tracer as story_tracer
from meridian_agents.news_agent import tracer as news_tracer
from meridian_agents.maintenance_agent import tracer as maintenance_tracer
from meridian_agents.rebranding_agent import tracer as rebranding_tracer

TRACERS = [post_tracer, story_tracer, news_tracer, maintenance_tracer, rebranding_tracer]


@pytest.mark.parametrize("tracer", TRACERS)
def test_start_run_returns_a_uuid_and_posts_the_run_record(tracer):
    with patch.object(tracer, "requests") as mock_requests:
        run_id = tracer.start_run({"key": "value"})
        assert len(run_id) == 36  # uuid4 string length
        mock_requests.post.assert_called_once()
        _, kwargs = mock_requests.post.call_args
        assert kwargs["json"]["runId"] == run_id
        assert json.loads(kwargs["json"]["metadata"]) == {"key": "value"}


@pytest.mark.parametrize("tracer", TRACERS)
def test_start_run_swallows_request_errors(tracer):
    with patch.object(tracer, "requests") as mock_requests:
        mock_requests.post.side_effect = Exception("network down")
        run_id = tracer.start_run()
        assert len(run_id) == 36


@pytest.mark.parametrize("tracer", TRACERS)
def test_complete_run_marks_completed_by_default(tracer):
    with patch.object(tracer, "requests") as mock_requests:
        _call_complete_run(tracer, "run-1", "All good")
        _, kwargs = mock_requests.put.call_args
        assert kwargs["json"]["status"] == "completed"
        assert kwargs["json"]["summary"] == "All good"


@pytest.mark.parametrize("tracer", TRACERS)
def test_complete_run_marks_failed_when_requested(tracer):
    with patch.object(tracer, "requests") as mock_requests:
        _call_complete_run(tracer, "run-1", "Something broke", failed=True)
        _, kwargs = mock_requests.put.call_args
        assert kwargs["json"]["status"] == "failed"


@pytest.mark.parametrize("tracer", TRACERS)
def test_complete_run_swallows_request_errors(tracer):
    with patch.object(tracer, "requests") as mock_requests:
        mock_requests.put.side_effect = Exception("network down")
        _call_complete_run(tracer, "run-1", "All good")  # must not raise


def _call_complete_run(tracer, run_id, summary, failed=False):
    import inspect
    params = inspect.signature(tracer.complete_run).parameters
    if "findings" in params:
        tracer.complete_run(run_id, summary, findings=[{"severity": "low"}], failed=failed)
    else:
        tracer.complete_run(run_id, summary, failed=failed)
