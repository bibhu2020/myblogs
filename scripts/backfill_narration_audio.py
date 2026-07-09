#!/usr/bin/env python3
"""
Backfill narration mp3s for existing published posts and stories that don't have one
yet (audioUrl is null) — e.g. content generated before the pre-rendered-audio pipeline
existed. News items are not covered here: the news agent replaces its entire table on
every run, so a stale item is never worth backfilling — just run the news agent again.

For each item: synthesizes an mp3 via the deployed TTS service (POST /api/tts,
format=mp3), uploads it to the media library named deterministically by content id
(post_<id>.mp3 / story_<id>.mp3 — same convention the agents use going forward), and
attaches the resulting URL via PUT /api/posts/:id or PUT /api/stories/:id.

Idempotent: items that already have an audioUrl are skipped, so this is safe to re-run.
A failure on one item is logged and does not block the rest of the batch.

Usage:
  python3 -m scripts.backfill_narration_audio             # posts + stories
  python3 -m scripts.backfill_narration_audio --posts-only
  python3 -m scripts.backfill_narration_audio --stories-only
  python3 -m scripts.backfill_narration_audio --dry-run    # list what would run, do nothing
"""
import argparse
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meridian_agents.auth import make_agent_jwt  # noqa: E402

_TIMEOUT = 20
_TTS_TIMEOUT = 280  # matches tts-service's own gunicorn timeout for a full-article synthesis


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "")


def _admin_headers() -> dict:
    return {"Authorization": f"Bearer {make_agent_jwt()}"}


def _fetch_items(server_base: str, kind: str) -> list[dict]:
    """kind: 'posts' or 'stories'."""
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.get(
            f"{server_base}/api/{kind}/admin",
            params={"status": "published", "limit": 500},
            headers=_admin_headers(),
        )
        r.raise_for_status()
        data = r.json()
        return data.get(kind, data) if isinstance(data, dict) else data


def _synthesize_mp3(server_base: str, text: str, style: str) -> bytes:
    with httpx.Client(timeout=_TTS_TIMEOUT) as client:
        r = client.post(
            f"{server_base}/api/tts",
            json={"text": text, "style": style, "format": "mp3"},
        )
        r.raise_for_status()
        mp3 = r.content
        if len(mp3) < 1024:
            raise RuntimeError("synthesis produced no audio")
        return mp3


def _upload_mp3(server_base: str, mp3: bytes, filename: str, alt: str) -> str:
    with httpx.Client(timeout=60) as client:
        r = client.post(
            f"{server_base}/api/media/upload",
            headers=_admin_headers(),
            files={"file": (f"{filename}.mp3", mp3, "audio/mpeg")},
            data={"alt": alt[:200]},
            params={"filename": filename},
        )
        r.raise_for_status()
        url = r.json().get("url")
        if not url:
            raise RuntimeError(f"upload response missing url: {r.text[:200]}")
        return url


def _attach_audio_url(server_base: str, kind: str, item_id: int, url: str) -> None:
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.put(
            f"{server_base}/api/{kind}/{item_id}",
            json={"audioUrl": url},
            headers=_admin_headers(),
        )
        r.raise_for_status()


def _backfill_kind(server_base: str, kind: str, style: str, filename_prefix: str, dry_run: bool) -> tuple[int, int]:
    items = _fetch_items(server_base, kind)
    pending = [it for it in items if not it.get("audioUrl")]
    print(f"\n{kind}: {len(items)} published, {len(pending)} missing audio")

    if dry_run:
        for it in pending:
            print(f"  [dry-run] would generate {filename_prefix}_{it['id']}.mp3 for \"{it.get('title', '')[:60]}\"")
        return 0, len(pending)

    succeeded = 0
    for it in pending:
        item_id = it["id"]
        title = it.get("title", "")[:60]
        text = _strip_html(it.get("content", "")).strip()
        if not text:
            print(f"  ✗ #{item_id} \"{title}\" — no content to narrate, skipping")
            continue
        try:
            print(f"  → #{item_id} \"{title}\" — synthesizing...")
            mp3 = _synthesize_mp3(server_base, text, style)
            filename = f"{filename_prefix}_{item_id}"
            url = _upload_mp3(server_base, mp3, filename, title or f"{filename_prefix} {item_id}")
            _attach_audio_url(server_base, kind, item_id, url)
            print(f"  ✓ #{item_id} — {url}")
            succeeded += 1
        except Exception as exc:
            print(f"  ✗ #{item_id} \"{title}\" — failed: {exc}")

    return succeeded, len(pending)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--posts-only", action="store_true")
    parser.add_argument("--stories-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    server_base = os.getenv("SERVER_BASE", "https://mishrabp-meridian.hf.space")
    print(f"Target: {server_base}")

    do_posts = not args.stories_only
    do_stories = not args.posts_only

    total_ok, total_pending = 0, 0
    if do_posts:
        ok, pending = _backfill_kind(server_base, "posts", "blog", "post", args.dry_run)
        total_ok += ok
        total_pending += pending
    if do_stories:
        ok, pending = _backfill_kind(server_base, "stories", "story", "story", args.dry_run)
        total_ok += ok
        total_pending += pending

    print(f"\nDone — {total_ok}/{total_pending} narration mp3s generated and attached.")


if __name__ == "__main__":
    main()
