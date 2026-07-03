"""Tests for rebranding_agent/pipeline.py: build_pipeline.

build_pipeline only constructs Agent objects and wires up tools/handoffs —
it never calls an LLM, so no mocking is needed.
"""
from unittest.mock import MagicMock

from meridian_agents.rebranding_agent.pipeline import build_pipeline
from meridian_agents.rebranding_agent.tools import (
    check_schedule, research_world_events, generate_rebrand_plan, revise_rebrand_plan,
    patch_frontend_files, read_frontend_file, write_frontend_file,
    review_seo_ada, verify_build, run_structural_tests, commit_and_push,
)


class TestBuildPipeline:
    def test_returns_the_ideation_agent_as_entry_point(self):
        agent = build_pipeline("gpt-4o-mini")
        assert agent.name == "IdeationAgent"

    def test_ideation_agent_has_its_tools_and_hands_off_to_coding(self):
        ideation = build_pipeline("gpt-4o-mini")
        assert ideation.tools == [
            check_schedule, research_world_events, generate_rebrand_plan, revise_rebrand_plan,
        ]
        assert [h.name for h in ideation.handoffs] == ["CodingAgent"]

    def test_coding_agent_hands_off_to_reviewer(self):
        ideation = build_pipeline("gpt-4o-mini")
        coding = ideation.handoffs[0]
        assert coding.name == "CodingAgent"
        assert coding.tools == [patch_frontend_files, read_frontend_file, write_frontend_file]
        assert [h.name for h in coding.handoffs] == ["ReviewerAgent"]

    def test_reviewer_agent_hands_off_to_ideation_coding_and_tester(self):
        ideation = build_pipeline("gpt-4o-mini")
        coding = ideation.handoffs[0]
        reviewer = coding.handoffs[0]
        assert reviewer.name == "ReviewerAgent"
        assert reviewer.tools == [review_seo_ada]
        assert [h.name for h in reviewer.handoffs] == ["IdeationAgent", "CodingAgent", "TesterAgent"]

    def test_tester_agent_hands_off_to_coding_and_publisher(self):
        ideation = build_pipeline("gpt-4o-mini")
        reviewer = ideation.handoffs[0].handoffs[0]
        tester = reviewer.handoffs[2]
        assert tester.name == "TesterAgent"
        assert tester.tools == [verify_build, run_structural_tests]
        assert [h.name for h in tester.handoffs] == ["CodingAgent", "PublisherAgent"]

    def test_publisher_agent_is_a_terminal_node(self):
        ideation = build_pipeline("gpt-4o-mini")
        tester = ideation.handoffs[0].handoffs[0].handoffs[2]
        publisher = tester.handoffs[1]
        assert publisher.name == "PublisherAgent"
        assert publisher.tools == [commit_and_push]
        assert publisher.handoffs == []

    def test_uses_the_provided_model_for_every_agent(self):
        from agents.models.interface import Model

        sentinel_model = MagicMock(spec=Model)
        ideation = build_pipeline(sentinel_model)
        coding = ideation.handoffs[0]
        reviewer = coding.handoffs[0]
        tester = reviewer.handoffs[2]
        publisher = tester.handoffs[1]
        assert ideation.model is sentinel_model
        assert coding.model is sentinel_model
        assert reviewer.model is sentinel_model
        assert tester.model is sentinel_model
        assert publisher.model is sentinel_model
