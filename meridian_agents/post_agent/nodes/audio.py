"""Pre-rendered TTS mp3 generation — synthesizes the whole post once at publish time via
the Kokoro-82M service and stores it in the media library, so blog readers get instant,
smooth playback instead of today's live per-chunk generation (see BlogPost.vue).

Mirrors the graceful-skip precedent already used by generate_images_node: any failure here
(TTS unreachable, empty audio, upload error) logs a warning and lets the post publish
without audio rather than failing the whole run.
"""
import os
import time
from io import BytesIO

import requests

from ...auth import make_agent_jwt
from ..state import AgentState
from .writer import strip_html

_TTS_TIMEOUT = 280  # matches the api-gateway's mp3-branch AbortSignal timeout


def _upload_audio(buf: bytes, alt: str, server_base: str) -> str:
    jwt = make_agent_jwt()
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


# ── LangGraph node ────────────────────────────────────────────────────────────

def generate_audio_node(state: AgentState) -> dict:
    server_base = os.getenv("SERVER_BASE", "https://mishrabp-meridian.hf.space")
    print("🔊 Synthesizing narration mp3...")

    text = strip_html(state["final_content"]).strip()
    if not text:
        print("  ⚠️  No content to narrate — skipping audio")
        return {"audio_url": None}

    try:
        res = requests.post(
            f"{server_base}/api/tts",
            json={"text": text, "style": "blog", "format": "mp3"},
            timeout=_TTS_TIMEOUT,
        )
        res.raise_for_status()
        mp3 = res.content
        if len(mp3) < 1024:
            raise RuntimeError("synthesis produced no audio")

        url = _upload_audio(mp3, state["post_title"][:120], server_base)
        print(f"  ✅ Narration: {url}")
        return {"audio_url": url}
    except Exception as e:
        print(f"  ⚠️  Audio generation failed ({e}) — publishing without narration")
        return {"audio_url": None}
