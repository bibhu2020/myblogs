"""Shared mutable context that flows through every agent in the pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RebrandCtx:
    repo_root: str
    force_rebrand: bool = False

    # Populated by IdeationAgent
    chosen_theme: str = ""
    mood: str = "neutral"
    world_events: str = ""
    rebrand_plan: dict = field(default_factory=dict)

    # Populated by CodingAgent
    files_changed: list = field(default_factory=list)
    patch_errors: list = field(default_factory=list)

    # Feedback loop state
    review_feedback: str = ""   # set by ReviewerAgent when sending back
    test_feedback: str = ""     # set by TesterAgent when sending back
    review_cycles: int = 0      # incremented each time we loop back; capped at 3
