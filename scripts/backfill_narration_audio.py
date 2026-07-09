#!/usr/bin/env python3
"""
Generate/correct narration mp3s for existing published posts, stories, and news items.

Covers two cases per item:
  - missing audio entirely (audioUrl is null) — generate fresh
  - audio exists but was uploaded before the myblogs/audio path split and the
    post_<id>/story_<id>/news_<id> deterministic-naming fix (i.e. its audioUrl still
    points at myblogs/uploads/<random-uuid>.mp3) — regenerate under the correct path/
    name and delete the old orphaned file

For each item: synthesizes an mp3 via the deployed TTS service (POST /api/tts,
format=mp3), uploads it to the media library named deterministically by content id
(post_<id>.mp3 / story_<id>.mp3 / news_<id>.mp3), and attaches the resulting URL
(PUT /api/posts/:id, PUT /api/stories/:id, or PATCH /api/news/:id).

Idempotent: items whose audioUrl already points at myblogs/audio are left alone, so
this is safe to re-run. A failure on one item is logged and does not block the batch.
Runs strictly sequentially — the deployed TTS service is a single worker with inference
serialized behind an internal lock, so concurrency here only adds contention, not speed.

Usage:
  python3 -m scripts.backfill_narration_audio                  # posts + stories + news
  python3 -m scripts.backfill_narration_audio --posts-only
  python3 -m scripts.backfill_narration_audio --stories-only
  python3 -m scripts.backfill_narration_audio --news-only
  python3 -m scripts.backfill_narration_audio --dry-run         # list what would run, do nothing
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
_TTS_TIMEOUT = 900  # matches tts-service's own gunicorn timeout for a full-article synthesis
_CORRECT_PATH_SEGMENT = "/myblogs/audio/"


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "")


def _admin_headers() -> dict:
    return {"Authorization": f"Bearer {make_agent_jwt()}"}


def _needs_audio(item: dict) -> bool:
    """True if this item has no audio yet, or its audio predates the myblogs/audio
    path split and deterministic-naming fix (still sitting under myblogs/uploads)."""
    url = item.get("audioUrl")
    if not url:
        return True
    return _CORRECT_PATH_SEGMENT not in url


def _fetch_posts_or_stories(server_base: str, kind: str) -> list[dict]:
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.get(
            f"{server_base}/api/{kind}/admin",
            params={"status": "published", "limit": 500},
            headers=_admin_headers(),
        )
        r.raise_for_status()
        data = r.json()
        return data.get(kind, data) if isinstance(data, dict) else data


def _fetch_news(server_base: str) -> list[dict]:
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.get(f"{server_base}/api/news")
        r.raise_for_status()
        data = r.json()
        return data.get("items", data) if isinstance(data, dict) else data


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


def _attach_audio_url_put(server_base: str, kind: str, item_id: int, url: str) -> None:
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.put(
            f"{server_base}/api/{kind}/{item_id}",
            json={"audioUrl": url},
            headers=_admin_headers(),
        )
        r.raise_for_status()


def _attach_audio_url_patch_news(server_base: str, item_id: int, url: str) -> None:
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.patch(
            f"{server_base}/api/news/{item_id}",
            json={"audioUrl": url},
            headers=_admin_headers(),
        )
        r.raise_for_status()


def _delete_old_file(server_base: str, old_url: str) -> None:
    old_filename = old_url.rsplit("/", 1)[-1]
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.delete(
                f"{server_base}/api/media/by-filename/{old_filename}",
                headers=_admin_headers(),
            )
            r.raise_for_status()
            print(f"      cleaned up old file: {old_filename}")
    except Exception as exc:
        print(f"      could not delete old file {old_filename}: {exc}")


def _backfill_posts_or_stories(server_base: str, kind: str, style: str, prefix: str, dry_run: bool) -> tuple[int, int]:
    items = _fetch_posts_or_stories(server_base, kind)
    pending = [it for it in items if _needs_audio(it)]
    print(f"\n{kind}: {len(items)} published, {len(pending)} need (re)generation")

    if dry_run:
        for it in pending:
            reason = "missing" if not it.get("audioUrl") else "wrong path"
            print(f"  [dry-run] {prefix}_{it['id']}.mp3 ({reason}) — \"{it.get('title', '')[:60]}\"")
        return 0, len(pending)

    succeeded = 0
    for it in pending:
        item_id = it["id"]
        title = it.get("title", "")[:60]
        old_url = it.get("audioUrl")
        text = _strip_html(it.get("content", "")).strip()
        if not text:
            print(f"  ✗ #{item_id} \"{title}\" — no content to narrate, skipping")
            continue
        try:
            print(f"  → #{item_id} \"{title}\" — synthesizing...")
            mp3 = _synthesize_mp3(server_base, text, style)
            filename = f"{prefix}_{item_id}"
            url = _upload_mp3(server_base, mp3, filename, title or f"{prefix} {item_id}")
            _attach_audio_url_put(server_base, kind, item_id, url)
            print(f"  ✓ #{item_id} — {url}")
            if old_url:
                _delete_old_file(server_base, old_url)
            succeeded += 1
        except Exception as exc:
            print(f"  ✗ #{item_id} \"{title}\" — failed: {exc}")

    return succeeded, len(pending)


def _backfill_news(server_base: str, dry_run: bool) -> tuple[int, int]:
    items = _fetch_news(server_base)
    pending = [it for it in items if _needs_audio(it)]
    print(f"\nnews: {len(items)} items, {len(pending)} need (re)generation")

    if dry_run:
        for it in pending:
            reason = "missing" if not it.get("audioUrl") else "wrong path"
            print(f"  [dry-run] news_{it['id']}.mp3 ({reason}) — \"{it.get('title', '')[:60]}\"")
        return 0, len(pending)

    succeeded = 0
    for it in pending:
        item_id = it["id"]
        title = it.get("title", "")[:60]
        old_url = it.get("audioUrl")
        text = f"{it.get('title', '')}. {it.get('summary', '')}".strip()
        if not text or text == ".":
            print(f"  ✗ #{item_id} \"{title}\" — no content to narrate, skipping")
            continue
        try:
            print(f"  → #{item_id} \"{title}\" — synthesizing...")
            mp3 = _synthesize_mp3(server_base, text, "news")
            filename = f"news_{item_id}"
            url = _upload_mp3(server_base, mp3, filename, title or f"news {item_id}")
            _attach_audio_url_patch_news(server_base, item_id, url)
            print(f"  ✓ #{item_id} — {url}")
            if old_url:
                _delete_old_file(server_base, old_url)
            succeeded += 1
        except Exception as exc:
            print(f"  ✗ #{item_id} \"{title}\" — failed: {exc}")

    return succeeded, len(pending)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--posts-only", action="store_true")
    parser.add_argument("--stories-only", action="store_true")
    parser.add_argument("--news-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    server_base = os.getenv("SERVER_BASE", "https://mishrabp-meridian.hf.space")
    print(f"Target: {server_base}")

    only_flags = (args.posts_only, args.stories_only, args.news_only)
    run_all = not any(only_flags)

    total_ok, total_pending = 0, 0
    if run_all or args.posts_only:
        ok, pending = _backfill_posts_or_stories(server_base, "posts", "blog", "post", args.dry_run)
        total_ok += ok
        total_pending += pending
    if run_all or args.stories_only:
        ok, pending = _backfill_posts_or_stories(server_base, "stories", "story", "story", args.dry_run)
        total_ok += ok
        total_pending += pending
    if run_all or args.news_only:
        ok, pending = _backfill_news(server_base, args.dry_run)
        total_ok += ok
        total_pending += pending

    print(f"\nDone — {total_ok}/{total_pending} narration mp3s generated and attached.")


if __name__ == "__main__":
    main()
