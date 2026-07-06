"""Save the generated story to the Meridian /api/stories endpoint as PENDING."""
import os
import re

import httpx

from ...auth import make_agent_jwt
from ...observability import observe
from ..state import StoryAgentState


@observe(name="save_pending")
def save_pending_node(state: StoryAgentState) -> dict:
    print("\n⏸️  Saving story as PENDING (awaiting admin approval)...")
    server_base = state.get("server_base", "")
    token = make_agent_jwt(name="Story Agent", email="story-agent@meridian.internal")

    payload = {
        "title": state["story_title"],
        "content": state["final_content"],
        "excerpt": state["story_excerpt"],
        "status": "pending",
        "authorName": state.get("author_name", "Meridian Storyteller"),
        "genre": state.get("genre", ""),
        "ageGroup": state.get("age_group", "8-15"),
        "moralLesson": state.get("moral_lesson", ""),
    }
    if state.get("featured_image_url"):
        payload["featuredImage"] = state["featured_image_url"]

    with httpx.Client(timeout=30) as client:
        r = client.post(
            f"{server_base}/api/stories",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()

    data = r.json()
    story_id = data.get("id")
    slug = data.get("slug")
    print(f"✅ Pending story saved — ID: {story_id}, slug: {slug}")
    return {
        "pending_story_id": story_id,
        "pending_story_slug": slug,
    }
