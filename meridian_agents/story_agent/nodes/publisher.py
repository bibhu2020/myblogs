"""Save the generated story to the Meridian /api/stories endpoint as PENDING."""
import base64
import hashlib
import hmac
import json
import os
import re
import time

import httpx

from ..state import StoryAgentState


def _make_agent_jwt() -> str:
    secret = os.getenv("JWT_SECRET", "myblogs-secret-key-2024").encode()
    now = int(time.time())

    def b64url(obj: dict) -> str:
        return (
            base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode())
            .rstrip(b"=")
            .decode()
        )

    header = b64url({"alg": "HS256", "typ": "JWT"})
    payload = b64url({
        "sub": 0, "id": 0,
        "email": "story-agent@meridian.internal",
        "name": "Story Agent",
        "role": "admin",
        "iat": now,
        "exp": now + 3600,
    })
    signing_input = f"{header}.{payload}".encode()
    sig = (
        base64.urlsafe_b64encode(
            hmac.new(secret, signing_input, hashlib.sha256).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    return f"{header}.{payload}.{sig}"


def save_pending_node(state: StoryAgentState) -> dict:
    print("\n⏸️  Saving story as PENDING (awaiting admin approval)...")
    server_base = state.get("server_base", "")
    token = _make_agent_jwt()

    payload = {
        "title": state["story_title"],
        "content": state["final_content"],
        "excerpt": state["story_excerpt"],
        "status": "pending",
        "authorName": state.get("author_name", "Meridian Storyteller"),
        "genre": state.get("genre", ""),
        "ageGroup": "8-15",
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
