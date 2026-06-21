"""
Shared cleanup utility — deletes published posts and stories older than N days
and removes their associated /uploads/ media files from the media library.

Called at the start of each post_agent and story_agent run.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone, timedelta

import httpx


_DEFAULT_DAYS = int(os.getenv("CLEANUP_MAX_AGE_DAYS", "30"))
_TIMEOUT = 20


def _admin_token(server_base: str) -> str:
    """Login as admin and return JWT, or use AGENT_JWT_TOKEN env var."""
    if token := os.getenv("AGENT_JWT_TOKEN"):
        return token
    email    = os.getenv("ADMIN_EMAIL", "admin@myblogs.com")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.post(
            f"{server_base}/api/auth/login",
            json={"email": email, "password": password},
        )
        r.raise_for_status()
        return r.json()["access_token"]


def _uploads_filename(url: str | None) -> str | None:
    """Extract bare filename from a /uploads/<uuid.ext> path, or None."""
    if not url:
        return None
    m = re.search(r"/uploads/([^/?#]+)", url)
    return m.group(1) if m else None


def _delete_media_by_filename(
    client: httpx.Client,
    server_base: str,
    auth: str,
    filename: str,
) -> None:
    """Find a media record by filename and delete it (best-effort)."""
    try:
        r = client.get(
            f"{server_base}/api/media",
            headers={"Authorization": auth},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        records = r.json() if isinstance(r.json(), list) else r.json().get("media", [])
        for rec in records:
            if rec.get("filename") == filename or rec.get("url", "").endswith(filename):
                mid = rec.get("id")
                dr = client.delete(
                    f"{server_base}/api/media/{mid}",
                    headers={"Authorization": auth},
                    timeout=_TIMEOUT,
                )
                dr.raise_for_status()
                print(f"    🗑  media deleted: {filename} (id={mid})")
                return
        print(f"    ℹ  media not found in library: {filename}")
    except Exception as exc:
        print(f"    ⚠  could not delete media {filename}: {exc}")


def cleanup_old_posts(
    server_base: str,
    days: int = _DEFAULT_DAYS,
    dry_run: bool = False,
) -> int:
    """Delete published posts older than `days` days and their media. Returns count deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    print(f"\n🧹 [cleanup] Checking for posts published before {cutoff.date()} (>{days} days old)...")

    try:
        token = _admin_token(server_base)
        auth = f"Bearer {token}"
    except Exception as exc:
        print(f"  ⚠  cleanup skipped — auth failed: {exc}")
        return 0

    deleted = 0
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(
                f"{server_base}/api/posts/admin?limit=500&status=published",
                headers={"Authorization": auth},
            )
            r.raise_for_status()
            data = r.json()
            posts = data.get("posts", data) if isinstance(data, dict) else data

            for post in posts:
                created = post.get("createdAt") or post.get("publishedAt") or ""
                if not created:
                    continue
                try:
                    ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if ts >= cutoff:
                    continue

                pid  = post.get("id")
                title = post.get("title", "?")[:60]
                img   = post.get("featuredImage") or ""
                fname = _uploads_filename(img)

                print(f"  → post #{pid} '{title}' ({ts.date()})", end="")
                if dry_run:
                    print(" [dry-run]")
                    continue

                try:
                    dr = client.delete(
                        f"{server_base}/api/posts/{pid}",
                        headers={"Authorization": auth},
                        timeout=_TIMEOUT,
                    )
                    dr.raise_for_status()
                    print(" ✓ deleted")
                    deleted += 1
                except Exception as exc:
                    print(f" ✗ failed: {exc}")
                    continue

                if fname:
                    _delete_media_by_filename(client, server_base, auth, fname)

    except Exception as exc:
        print(f"  ⚠  post cleanup error: {exc}")

    print(f"  ✅ posts cleanup done — {deleted} deleted")
    return deleted


def cleanup_old_stories(
    server_base: str,
    days: int = _DEFAULT_DAYS,
    dry_run: bool = False,
) -> int:
    """Delete published stories older than `days` days and their media. Returns count deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    print(f"\n🧹 [cleanup] Checking for stories published before {cutoff.date()} (>{days} days old)...")

    try:
        token = _admin_token(server_base)
        auth = f"Bearer {token}"
    except Exception as exc:
        print(f"  ⚠  cleanup skipped — auth failed: {exc}")
        return 0

    deleted = 0
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(
                f"{server_base}/api/stories/admin?limit=500",
                headers={"Authorization": auth},
            )
            r.raise_for_status()
            data = r.json()
            stories = data.get("stories", data) if isinstance(data, dict) else data

            for story in stories:
                status = story.get("status", "")
                if status != "published":
                    continue

                created = story.get("createdAt") or ""
                if not created:
                    continue
                try:
                    ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if ts >= cutoff:
                    continue

                sid   = story.get("id")
                title = story.get("title", "?")[:60]
                img   = story.get("featuredImage") or ""
                fname = _uploads_filename(img)

                print(f"  → story #{sid} '{title}' ({ts.date()})", end="")
                if dry_run:
                    print(" [dry-run]")
                    continue

                try:
                    dr = client.delete(
                        f"{server_base}/api/stories/{sid}",
                        headers={"Authorization": auth},
                        timeout=_TIMEOUT,
                    )
                    dr.raise_for_status()
                    print(" ✓ deleted")
                    deleted += 1
                except Exception as exc:
                    print(f" ✗ failed: {exc}")
                    continue

                if fname:
                    _delete_media_by_filename(client, server_base, auth, fname)

    except Exception as exc:
        print(f"  ⚠  story cleanup error: {exc}")

    print(f"  ✅ stories cleanup done — {deleted} deleted")
    return deleted
