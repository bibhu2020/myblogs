"""
Meridian Content Cleanup Script

Deletes blog posts and stories older than 30 days (configurable via --days flag),
along with their associated uploaded media files.

Usage:
    python3 -m meridian_agents.cleanup              # delete content older than 30 days
    python3 -m meridian_agents.cleanup --days 14    # use a different age threshold
    python3 -m meridian_agents.cleanup --dry-run    # preview what would be deleted
"""
import argparse
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from .auth import make_agent_jwt  # noqa: E402

SERVER_BASE  = os.getenv("SERVER_BASE", "http://localhost:3000")
UPLOADS_DIR  = Path(__file__).parent.parent / "media-service" / "uploads"


def _auth_headers() -> dict:
    jwt = make_agent_jwt(name="Cleanup Agent", email="cleanup@meridian.internal")
    return {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}


def _cutoff(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        # ISO 8601 with or without trailing Z
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _delete_media_file(url: str | None) -> None:
    """Remove uploaded file from disk if the URL points to /uploads/."""
    if not url or "/uploads/" not in url:
        return
    # Extract filename from URL like /uploads/uuid.ext or http://host/uploads/uuid.ext
    m = re.search(r"/uploads/([^/?#]+)", url)
    if not m:
        return
    fname = m.group(1)
    fpath = UPLOADS_DIR / fname
    if fpath.exists():
        fpath.unlink()
        print(f"      🗑  Deleted file: {fname}")


def cleanup_posts(days: int, dry_run: bool) -> int:
    """Delete published posts older than `days` days. Returns count deleted."""
    cut = _cutoff(days)
    headers = _auth_headers()

    try:
        resp = requests.get(
            f"{SERVER_BASE}/api/posts",
            params={"limit": 500, "status": "published"},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        posts = data.get("posts", data) if isinstance(data, dict) else data
    except Exception as exc:
        print(f"  ✗ Could not fetch posts: {exc}")
        return 0

    old = [p for p in posts if _parse_date(p.get("createdAt")) and _parse_date(p.get("createdAt")) < cut]
    print(f"\n📰 Posts: {len(old)} of {len(posts)} are older than {days} days")

    deleted = 0
    for p in old:
        age = (datetime.now(timezone.utc) - _parse_date(p["createdAt"])).days
        print(f"  {'[DRY RUN] Would delete' if dry_run else 'Deleting'} post #{p['id']}  ({age}d old): {p.get('title','?')[:60]}")
        if not dry_run:
            _delete_media_file(p.get("featuredImage"))
            try:
                r = requests.delete(f"{SERVER_BASE}/api/posts/{p['id']}", headers=headers, timeout=15)
                if r.ok:
                    deleted += 1
                    print(f"      ✓ Deleted")
                else:
                    print(f"      ✗ HTTP {r.status_code}: {r.text[:100]}")
            except Exception as exc:
                print(f"      ✗ Error: {exc}")
        else:
            deleted += 1

    return deleted


def cleanup_stories(days: int, dry_run: bool) -> int:
    """Delete stories older than `days` days. Returns count deleted."""
    cut = _cutoff(days)
    headers = _auth_headers()

    try:
        resp = requests.get(
            f"{SERVER_BASE}/api/stories/admin",
            params={"limit": 500, "page": 1},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        stories = data.get("stories", data.get("items", data)) if isinstance(data, dict) else data
    except Exception as exc:
        print(f"  ✗ Could not fetch stories: {exc}")
        return 0

    old = [s for s in stories if _parse_date(s.get("createdAt")) and _parse_date(s.get("createdAt")) < cut]
    print(f"\n📖 Stories: {len(old)} of {len(stories)} are older than {days} days")

    deleted = 0
    for s in old:
        age = (datetime.now(timezone.utc) - _parse_date(s["createdAt"])).days
        print(f"  {'[DRY RUN] Would delete' if dry_run else 'Deleting'} story #{s['id']}  ({age}d old): {s.get('title','?')[:60]}")
        if not dry_run:
            _delete_media_file(s.get("featuredImage"))
            try:
                r = requests.delete(f"{SERVER_BASE}/api/stories/{s['id']}", headers=headers, timeout=15)
                if r.ok:
                    deleted += 1
                    print(f"      ✓ Deleted")
                else:
                    print(f"      ✗ HTTP {r.status_code}: {r.text[:100]}")
            except Exception as exc:
                print(f"      ✗ Error: {exc}")
        else:
            deleted += 1

    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete Meridian content older than N days")
    parser.add_argument("--days", type=int, default=30, help="Age threshold in days (default: 30)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without deleting")
    args = parser.parse_args()

    label = f"[DRY RUN] " if args.dry_run else ""
    print(f"\n╔══════════════════════════════════════════════╗")
    print(f"║  {label}Meridian Cleanup — content > {args.days} days")
    print(f"╚══════════════════════════════════════════════╝")
    print(f"  Server : {SERVER_BASE}")
    print(f"  Cutoff : {_cutoff(args.days).strftime('%Y-%m-%d %H:%M UTC')}\n")

    posts_deleted   = cleanup_posts(args.days, args.dry_run)
    stories_deleted = cleanup_stories(args.days, args.dry_run)

    print(f"\n{'─' * 50}")
    action = "Would delete" if args.dry_run else "Deleted"
    print(f"  {action} {posts_deleted} post(s) and {stories_deleted} story/stories")
    if args.dry_run:
        print("  Run without --dry-run to apply deletions.\n")
    else:
        print("  Cleanup complete.\n")


if __name__ == "__main__":
    main()
