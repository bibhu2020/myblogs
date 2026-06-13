#!/usr/bin/env python3
"""
Remove media files (uploads + DB records) that are not referenced by any blog post.

References are searched in:
  - posts.featuredImage  (full URL or /uploads/<filename>)
  - posts.content        (HTML body — may embed /uploads/ paths)
  - posts.gallery        (JSON array of URLs)

Runs locally or in GitHub Actions against the committed SQLite DB files.
After deletion the caller (CI) commits the changes back to the repo.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOG_DB   = ROOT / "blog-service"  / "blog.db"
MEDIA_DB  = ROOT / "media-service" / "media.db"
UPLOADS   = ROOT / "media-service" / "uploads"


def _referenced_filenames() -> set[str]:
    """Return the set of bare filenames (no path) referenced in any blog post."""
    conn = sqlite3.connect(BLOG_DB)
    rows = conn.execute(
        'SELECT "featuredImage", content, gallery FROM posts'
    ).fetchall()
    conn.close()

    refs: set[str] = set()
    pattern = re.compile(r'/uploads/([^\s"\'<>\]]+)')

    for featured, content, gallery in rows:
        for field in (featured, content, gallery):
            if not field:
                continue
            for m in pattern.finditer(str(field)):
                refs.add(m.group(1).split("?")[0])  # strip any query string

    return refs


def _media_records() -> list[tuple]:
    """Return list of (id, filename) from media_media."""
    conn = sqlite3.connect(MEDIA_DB)
    rows = conn.execute('SELECT id, filename FROM media_media').fetchall()
    conn.close()
    return rows


def cleanup(dry_run: bool = False) -> int:
    referenced = _referenced_filenames()
    records    = _media_records()

    orphans = [(rid, fn) for rid, fn in records if fn not in referenced]

    if not orphans:
        print("✓ No orphaned media files found — store is clean.")
        return 0

    print(f"Found {len(orphans)} orphaned file(s):")

    conn = sqlite3.connect(MEDIA_DB)
    deleted = 0
    for rid, filename in orphans:
        filepath = UPLOADS / filename
        status = ""
        if filepath.exists():
            if not dry_run:
                filepath.unlink()
            status = "deleted" if not dry_run else "would delete"
        else:
            status = "already missing"

        if not dry_run:
            conn.execute("DELETE FROM media_media WHERE id = ?", (rid,))
        print(f"  [{status}] {filename}")
        deleted += 1

    if not dry_run:
        conn.commit()
    conn.close()

    print(f"\n{'Would remove' if dry_run else 'Removed'} {deleted} orphaned record(s).")
    return deleted


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        print("=== DRY RUN — no files will be deleted ===\n")
    sys.exit(0 if cleanup(dry_run=dry) >= 0 else 1)
