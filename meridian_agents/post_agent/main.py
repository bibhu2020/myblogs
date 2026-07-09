"""
Meridian Post Agent — human-in-the-loop edition.

Phase 1 (generate):
  python3 -m meridian_agents.post_agent
  → Runs the full pipeline: research → write → images → taxonomy → save as PENDING
  → Prints the post URL in the admin panel for review

Phase 2 (admin decision — via admin UI or CLI):
  # Approve (publish the post):
  python3 -m meridian_agents.post_agent approve <post_id>

  # Reject (delete the post):
  python3 -m meridian_agents.post_agent reject <post_id>

The admin UI at /admin/posts (Pending Approval tab) offers the same approve/reject
actions via buttons without needing the CLI.
"""
import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from .graph import build_graph  # noqa: E402
from .tracer import complete_run, start_run  # noqa: E402
from ..cleanup import cleanup_empty_categories, cleanup_old_posts, cleanup_orphaned_media  # noqa: E402
from ..observability import flush_observability, get_langchain_handler, init_observability, traced_run  # noqa: E402

init_observability("post_agent")

SERVER_BASE     = os.getenv("SERVER_BASE", "https://mishrabp-meridian.hf.space")
AUTHOR_NAME     = os.getenv("AGENT_AUTHOR_NAME", "Meridian AI Researcher")
AUTHOR_EMAIL    = os.getenv("AGENT_AUTHOR_EMAIL", "ai.researcher@meridian.blog")
AUTHOR_PASSWORD = os.getenv("AGENT_AUTHOR_PASSWORD", f"MeridianAI{time.strftime('%Y')}!rsch")

# Path to the pending-posts registry (one JSON line per pending post)
_PENDING_FILE = Path(__file__).parent / "pending_posts.jsonl"


def _append_pending(entry: dict) -> None:
    with _PENDING_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _load_pending() -> list[dict]:
    if not _PENDING_FILE.exists():
        return []
    entries = []
    for line in _PENDING_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def _remove_pending(post_id: int) -> None:
    entries = [e for e in _load_pending() if e.get("post_id") != post_id]
    _PENDING_FILE.write_text(
        "\n".join(json.dumps(e) for e in entries) + ("\n" if entries else ""),
        encoding="utf-8",
    )


# ── Phase 1: Generate and save as PENDING ────────────────────────────────────

def run_agent() -> dict:
    print("\n╔══════════════════════════════════════════╗")
    print("║   Meridian Post Agent — Generate Phase   ║")
    print("║   Human-in-the-Loop Approval Flow        ║")
    print("╚══════════════════════════════════════════╝\n")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required.")

    cleanup_old_posts(SERVER_BASE)
    cleanup_empty_categories(SERVER_BASE)
    cleanup_orphaned_media(SERVER_BASE)

    run_id = start_run({"authorName": AUTHOR_NAME, "authorEmail": AUTHOR_EMAIL})
    graph = build_graph()
    t0 = time.time()

    initial: dict = {
        "server_base": SERVER_BASE,
        "author_name": AUTHOR_NAME,
        "author_email": AUTHOR_EMAIL,
        "author_password": AUTHOR_PASSWORD,
        "series_key": None, "series_index": None, "series_topic": None,
        "category_name": "", "category_pool": "", "category_research_style": "",
        "trend": "", "technical": "", "reactions": "", "implications": "",
        "post_title": "", "post_excerpt": "", "post_content": "",
        "post_featured_image_prompt": "", "post_category_keywords": [],
        "post_tag_keywords": [], "post_unsplash_query": None, "word_count": 0,
        "featured_image_url": None, "final_content": "",
        "audio_url": None,
        "category_id": None, "tag_ids": [],
        "pending_post_id": None, "pending_post_slug": None,
        "approved": None, "published_slug": None, "published_id": None,
    }

    try:
        with traced_run("post_agent"):
            handler = get_langchain_handler()
            final = graph.invoke(initial, config={"callbacks": [handler]} if handler else None)
    except Exception as exc:
        complete_run(run_id, str(exc), failed=True)
        raise
    finally:
        flush_observability()

    elapsed = round(time.time() - t0)
    post_id   = final.get("pending_post_id")
    post_slug = final.get("pending_post_slug")
    title     = final.get("post_title", "(untitled)")

    _append_pending({
        "post_id": post_id,
        "slug": post_slug,
        "title": title,
        "run_id": run_id,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })

    complete_run(
        run_id,
        summary=f"Pending approval: '{title}' (ID: {post_id}) — generated in {elapsed}s",
    )

    print(f"\n╔══════════════════════════════════════════════════════╗")
    print(f"║  ⏸️   Post saved — AWAITING ADMIN APPROVAL           ║")
    print(f"╚══════════════════════════════════════════════════════╝")
    print(f"  Title  : {title}")
    print(f"  Post ID: {post_id}")
    print(f"  Time   : {elapsed}s\n")
    print(f"  Review in admin panel:")
    print(f"    {SERVER_BASE}/admin/posts  (Pending Approval tab)")
    print(f"\n  Or via CLI:")
    print(f"    python3 -m meridian_agents.post_agent approve {post_id}")
    print(f"    python3 -m meridian_agents.post_agent reject  {post_id}\n")

    return final


# ── Phase 2a: Admin approves ──────────────────────────────────────────────────

def approve_post(post_id: int) -> None:
    print(f"\n✅ Approving post #{post_id}...")
    token = _get_admin_token()
    with httpx.Client(timeout=15) as client:
        r = client.patch(
            f"{SERVER_BASE}/api/posts/{post_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()

    data = r.json()
    slug = data.get("slug", "unknown")
    _remove_pending(post_id)
    print(f"  Published: {SERVER_BASE}/blog/{slug}")
    print(f"  Post is now live.\n")


# ── Phase 2b: Admin rejects ───────────────────────────────────────────────────

def reject_post(post_id: int) -> None:
    print(f"\n🗑️  Rejecting post #{post_id}...")
    token = _get_admin_token()
    with httpx.Client(timeout=15) as client:
        r = client.patch(
            f"{SERVER_BASE}/api/posts/{post_id}/reject",
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()

    _remove_pending(post_id)
    print(f"  Post #{post_id} has been removed.\n")


# ── List pending posts ────────────────────────────────────────────────────────

def list_pending() -> None:
    entries = _load_pending()
    if not entries:
        print("  No pending posts.\n")
        return
    print(f"\n{'ID':>6}  {'Title':<50}  {'Generated'}")
    print("-" * 72)
    for e in entries:
        print(f"  {e.get('post_id', '?'):>4}  {e.get('title', '?')[:50]:<50}  {e.get('generated_at', '?')}")
    print()


# ── Admin auth helper ─────────────────────────────────────────────────────────

def _get_admin_token() -> str:
    """Obtain a JWT by logging in as admin, or use AGENT_JWT_TOKEN env var."""
    if token := os.getenv("AGENT_JWT_TOKEN"):
        return token
    # Try logging in with admin credentials
    admin_email    = os.getenv("ADMIN_EMAIL", "admin@myblogs.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    with httpx.Client(timeout=10) as client:
        r = client.post(
            f"{SERVER_BASE}/api/auth/login",
            json={"email": admin_email, "password": admin_password},
        )
        r.raise_for_status()
        return r.json()["access_token"]


# Alias for backward-compatibility
run_post_agent = run_agent
