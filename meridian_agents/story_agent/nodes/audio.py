"""Pre-rendered TTS mp3 generation — synthesizes the whole story once at publish time via
the Kokoro-82M service and stores it in the media library, so readers get instant, smooth
playback instead of live per-chunk generation (see StoryDetail.vue).

Mirrors the graceful-skip precedent already used by generate_story_images_node (and its
post_agent equivalent, nodes/audio.py): any failure here (TTS unreachable, empty audio,
upload error) logs a warning and lets the story publish without audio rather than failing
the whole run.
"""
import os
import time
from io import BytesIO

import requests

from ...auth import make_agent_jwt
from ...observability import observe
from ...post_agent.nodes.writer import strip_html
from ..state import StoryAgentState

_TTS_TIMEOUT = 280  # matches the api-gateway's mp3-branch AbortSignal timeout


def _upload_audio(buf: bytes, alt: str, server_base: str) -> str:
    jwt = make_agent_jwt(name="Story Agent", email="story-agent@meridian.internal")
    files = {"file": (f"narration-{int(time.time())}.mp3", BytesIO(buf), "audio/mpeg")}
    res = requests.post(
        f"{server_base}/api/media/upload",
        headers={"Authorization": f"Bearer {jwt}"},
        files=files,
        data={"alt": alt[:200]},
        timeout=60,
    )
    if not res.ok:
        raise RuntimeError(f"Upload failed ({res.status_code}): {res.text[:300]}")
    url = res.json().get("url")
    if not url:
        raise RuntimeError(f"Upload response missing url: {res.text[:300]}")
    return url


@observe(name="generate_story_audio")
def generate_story_audio_node(state: StoryAgentState) -> dict:
    server_base = os.getenv("SERVER_BASE", "https://mishrabp-meridian.hf.space")
    print("🔊 Synthesizing narration mp3...")

    text = strip_html(state["final_content"]).strip()
    if not text:
        print("  ⚠️  No content to narrate — skipping audio")
        return {"audio_url": None}

    try:
        res = requests.post(
            f"{server_base}/api/tts",
            json={"text": text, "style": "story", "format": "mp3"},
            timeout=_TTS_TIMEOUT,
        )
        res.raise_for_status()
        mp3 = res.content
        if len(mp3) < 1024:
            raise RuntimeError("synthesis produced no audio")

        url = _upload_audio(mp3, state["story_title"][:120], server_base)
        print(f"  ✅ Narration: {url}")
        return {"audio_url": url}
    except Exception as e:
        print(f"  ⚠️  Audio generation failed ({e}) — publishing without narration")
        return {"audio_url": None}
