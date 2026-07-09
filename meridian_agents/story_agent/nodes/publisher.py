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
        "category": state.get("category", ""),
        "ageGroup": state.get("age_group", "High School+"),
        "moralLesson": state.get("moral_lesson", ""),
    }
    if state.get("featured_image_url"):
        payload["featuredImage"] = state["featured_image_url"]
    # audio_url is intentionally NOT set here — narration is generated and attached by
    # generate_story_audio_node/attach_story_audio_node *after* this save, since the mp3
    # filename is named deterministically from the story id this call returns
    # (story_<id>.mp3).

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


@observe(name="attach_story_audio")
def attach_story_audio_node(state: StoryAgentState) -> dict:
    """Attach the narration mp3 (generated after save_pending_node, once the story id is
    known — see nodes/audio.py) to the just-created story via a direct PUT. No-op if audio
    generation failed or was skipped."""
    audio_url = state.get("audio_url")
    story_id = state.get("pending_story_id")
    if not audio_url or not story_id:
        return {}

    server_base = state.get("server_base", "")
    try:
        token = make_agent_jwt(name="Story Agent", email="story-agent@meridian.internal")
        with httpx.Client(timeout=15) as client:
            r = client.put(
                f"{server_base}/api/stories/{story_id}",
                json={"audioUrl": audio_url},
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
        print(f"✅ Narration attached to story #{story_id}")
    except Exception as exc:
        print(f"⚠️  Could not attach narration to story #{story_id}: {exc}")
    return {}
