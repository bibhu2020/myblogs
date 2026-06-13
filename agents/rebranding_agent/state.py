"""LangGraph state for the rebranding agent."""
from __future__ import annotations
from typing import Optional
from typing_extensions import TypedDict


class RebrandState(TypedDict, total=False):
    repo_root: str
    # Step 0 — first-Sunday guard
    is_first_sunday: bool
    skip_reason: str
    # Step 1 — world mood research
    world_events: str
    chosen_theme: str
    mood: str           # "celebratory" | "somber" | "neutral"
    # Step 3-4 — generated rebrand plan
    rebrand_plan: dict  # palette_a, lb_accent, messaging, holiday_css, title_emoji
    # Step 4 apply — file patch results
    files_changed: list
    patch_errors: list
    # Step 5 — build verification
    build_passed: bool
    build_output: str
    # Step 9 — publish
    commit_sha: str
    push_success: bool
    push_error: str
    changes_reverted: bool
    # Final
    result_summary: str
    error: str
