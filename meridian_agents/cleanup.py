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

# The post agent's fixed taxonomy — these categories are never auto-deleted even
# if they're temporarily empty. Any other category is a leftover that should be
# swept once its last post has aged out.
FIXED_CATEGORY_SLUGS = {"technology", "education", "travel", "history"}


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


def _all_upload_filenames(item: dict, image_field: str = "featuredImage") -> list[str]:
    """Every /uploads/<filename> a post, story, or news item references — its hero
    image field plus every inline image embedded in HTML body content — so a
    deleted item never leaves orphaned files behind in the media library."""
    filenames: list[str] = []
    hero = _uploads_filename(item.get(image_field))
    if hero:
        filenames.append(hero)
    content = item.get("content") or ""
    filenames.extend(m.group(1) for m in re.finditer(r"/uploads/([^\"'?#\s]+)", content))
    return list(dict.fromkeys(filenames))  # de-duplicate, preserve order


def _referenced_filenames(items: list[dict], image_field: str = "featuredImage") -> set[str]:
    """Union of every /uploads/<filename> referenced across a list of posts/stories/
    news items."""
    referenced: set[str] = set()
    for item in items:
        referenced.update(_all_upload_filenames(item, image_field))
    return referenced


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
                if post.get("doNotDelete"):
                    continue

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
                fnames = _all_upload_filenames(post)

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

                for fname in fnames:
                    _delete_media_by_filename(client, server_base, auth, fname)

    except Exception as exc:
        print(f"  ⚠  post cleanup error: {exc}")

    print(f"  ✅ posts cleanup done — {deleted} deleted")
    return deleted


def cleanup_empty_categories(server_base: str, dry_run: bool = False) -> int:
    """Delete any category outside the fixed taxonomy once it has zero posts left
    (of any status). Run this after cleanup_old_posts so newly-emptied categories
    are caught the same run. Returns count deleted."""
    print("\n🧹 [cleanup] Checking for empty non-fixed categories...")

    try:
        token = _admin_token(server_base)
        auth = f"Bearer {token}"
    except Exception as exc:
        print(f"  ⚠  category cleanup skipped — auth failed: {exc}")
        return 0

    deleted = 0
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(f"{server_base}/api/categories")
            r.raise_for_status()
            categories = r.json()

            for cat in categories:
                slug = (cat.get("slug") or "").lower()
                if slug in FIXED_CATEGORY_SLUGS:
                    continue

                cid = cat.get("id")
                name = cat.get("name", "?")
                try:
                    cr = client.get(
                        f"{server_base}/api/posts/admin",
                        params={"category": cat.get("slug"), "limit": 1},
                        headers={"Authorization": auth},
                    )
                    cr.raise_for_status()
                    cdata = cr.json()
                    total = cdata.get("total", 0) if isinstance(cdata, dict) else len(cdata)
                except Exception as exc:
                    print(f"  ⚠  could not check post count for category '{name}': {exc}")
                    continue

                if total > 0:
                    continue

                print(f"  → category '{name}' has 0 posts", end="")
                if dry_run:
                    print(" [dry-run]")
                    continue

                try:
                    dr = client.delete(
                        f"{server_base}/api/categories/{cid}",
                        headers={"Authorization": auth},
                        timeout=_TIMEOUT,
                    )
                    dr.raise_for_status()
                    print(" ✓ deleted")
                    deleted += 1
                except Exception as exc:
                    print(f" ✗ failed: {exc}")

    except Exception as exc:
        print(f"  ⚠  category cleanup error: {exc}")

    print(f"  ✅ category cleanup done — {deleted} deleted")
    return deleted


def cleanup_orphaned_media(server_base: str, dry_run: bool = False) -> int:
    """Delete every media library file that isn't referenced by any live post,
    story, or news item. This is the media library's own safety net — it catches
    leaks that per-item cleanup misses (manual admin deletes/edits, news refreshes
    that replace the whole news_items table, failed uploads, etc.), on top of what
    cleanup_old_posts/cleanup_old_stories already remove when they delete an aged-out
    item. Returns count deleted."""
    print("\n🧹 [cleanup] Checking for orphaned media files...")

    try:
        token = _admin_token(server_base)
        auth = f"Bearer {token}"
    except Exception as exc:
        print(f"  ⚠  media cleanup skipped — auth failed: {exc}")
        return 0

    deleted = 0
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            referenced: set[str] = set()

            pr = client.get(
                f"{server_base}/api/posts/admin",
                params={"limit": 1000},
                headers={"Authorization": auth},
            )
            pr.raise_for_status()
            pdata = pr.json()
            posts = pdata.get("posts", pdata) if isinstance(pdata, dict) else pdata
            referenced |= _referenced_filenames(posts)

            sr = client.get(
                f"{server_base}/api/stories/admin",
                params={"limit": 1000},
                headers={"Authorization": auth},
            )
            sr.raise_for_status()
            sdata = sr.json()
            stories = sdata.get("stories", sdata) if isinstance(sdata, dict) else sdata
            referenced |= _referenced_filenames(stories)

            nr = client.get(f"{server_base}/api/news")
            nr.raise_for_status()
            ndata = nr.json()
            news_items = ndata.get("items", ndata) if isinstance(ndata, dict) else ndata
            referenced |= _referenced_filenames(news_items, image_field="imageUrl")

            mr = client.get(f"{server_base}/api/media", headers={"Authorization": auth})
            mr.raise_for_status()
            mdata = mr.json()
            media = mdata if isinstance(mdata, list) else mdata.get("media", [])

            for rec in media:
                filename = rec.get("filename") or _uploads_filename(rec.get("url"))
                if not filename or filename in referenced:
                    continue

                mid = rec.get("id")
                print(f"  → media #{mid} '{filename}' — not referenced anywhere", end="")
                if dry_run:
                    print(" [dry-run]")
                    continue

                try:
                    dr = client.delete(
                        f"{server_base}/api/media/{mid}",
                        headers={"Authorization": auth},
                        timeout=_TIMEOUT,
                    )
                    dr.raise_for_status()
                    print(" ✓ deleted")
                    deleted += 1
                except Exception as exc:
                    print(f" ✗ failed: {exc}")

    except Exception as exc:
        print(f"  ⚠  media cleanup error: {exc}")

    print(f"  ✅ media cleanup done — {deleted} deleted")
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
                fnames = _all_upload_filenames(story)

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

                for fname in fnames:
                    _delete_media_by_filename(client, server_base, auth, fname)

    except Exception as exc:
        print(f"  ⚠  story cleanup error: {exc}")

    print(f"  ✅ stories cleanup done — {deleted} deleted")
    return deleted
