"""
Meridian Story Agent — weekly children's story generator.

Generates a 4000+ word illustrated story for ages 8–15 and saves it as PENDING
for admin review. The admin approves or rejects it from /admin/stories in the panel.

Usage:
  python3 -m meridian_agents.story_agent            # generate one story
  python3 -m meridian_agents.story_agent approve <id>
  python3 -m meridian_agents.story_agent reject  <id>
  python3 -m meridian_agents.story_agent pending
  python3 -m meridian_agents.story_agent schedule '0 6 * * 1'  # every Monday 06:00 UTC
"""
import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from .nodes.writer import pick_theme_node, write_story_node, expand_story_node, _MIN_WORDS  # noqa: E402
from .nodes.images import generate_story_images_node                              # noqa: E402
from .nodes.publisher import save_pending_node                                    # noqa: E402
from .tracer import start_run, complete_run                                       # noqa: E402

SERVER_BASE   = os.getenv("SERVER_BASE", "https://mishrabP-myblogs.hf.space")
AUTHOR_NAME   = os.getenv("STORY_AUTHOR_NAME", "Meridian Storyteller")

_PENDING_FILE = Path(__file__).parent / "pending_stories.jsonl"


# ── Registry helpers ──────────────────────────────────────────────────────────

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


def _remove_pending(story_id: int) -> None:
    entries = [e for e in _load_pending() if e.get("story_id") != story_id]
    _PENDING_FILE.write_text(
        "\n".join(json.dumps(e) for e in entries) + ("\n" if entries else ""),
        encoding="utf-8",
    )


# ── Phase 1: Generate story and save as PENDING ───────────────────────────────

def run_agent() -> dict:
    print("\n╔═══════════════════════════════════════════════╗")
    print("║   Meridian Story Agent — Daily Story Run      ║")
    print("║   Ages 3-7 / 8-15 / 16-20 (random pick)      ║")
    print("╚═══════════════════════════════════════════════╝\n")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required.")

    run_id = start_run({"authorName": AUTHOR_NAME})
    t0 = time.time()

    state: dict = {
        "server_base": SERVER_BASE,
        "author_name": AUTHOR_NAME,
        "age_group": "",
        "theme": "",
        "genre": "",
        "premise": "",
        "moral_lesson": "",
        "story_title": "",
        "story_excerpt": "",
        "story_content": "",
        "featured_image_prompt": "",
        "word_count": 0,
        "featured_image_url": None,
        "final_content": "",
        "pending_story_id": None,
        "pending_story_slug": None,
    }

    try:
        state.update(pick_theme_node(state))
        state.update(write_story_node(state))

        if state["word_count"] < _MIN_WORDS.get(state.get("age_group", "8-15"), 4000):
            state.update(expand_story_node(state))

        state.update(generate_story_images_node(state))
        state.update(save_pending_node(state))

    except Exception as exc:
        complete_run(run_id, str(exc), failed=True)
        raise

    elapsed = round(time.time() - t0)
    story_id   = state.get("pending_story_id")
    story_slug = state.get("pending_story_slug")
    title      = state.get("story_title", "(untitled)")

    _append_pending({
        "story_id": story_id,
        "slug": story_slug,
        "title": title,
        "genre": state.get("genre", ""),
        "run_id": run_id,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })

    complete_run(
        run_id,
        summary=f"Pending approval: '{title}' (ID: {story_id}) — {state['word_count']} words in {elapsed}s",
    )

    print(f"\n╔═══════════════════════════════════════════════════════╗")
    print(f"║  ⏸️   Story saved — AWAITING ADMIN APPROVAL           ║")
    print(f"╚═══════════════════════════════════════════════════════╝")
    print(f"  Title  : {title}")
    print(f"  Genre  : {state.get('genre', '—')}")
    print(f"  Words  : {state['word_count']}")
    print(f"  Story ID: {story_id}")
    print(f"  Time   : {elapsed}s\n")
    print(f"  Review in admin panel:")
    print(f"    {SERVER_BASE}/admin/stories  (Pending Approval tab)")
    print(f"\n  Or via CLI:")
    print(f"    python3 -m meridian_agents.story_agent approve {story_id}")
    print(f"    python3 -m meridian_agents.story_agent reject  {story_id}\n")

    return state


# ── Phase 2a: Approve ─────────────────────────────────────────────────────────

def approve_story(story_id: int) -> None:
    print(f"\n✅ Approving story #{story_id}...")
    token = _get_admin_token()
    with httpx.Client(timeout=15) as client:
        r = client.patch(
            f"{SERVER_BASE}/api/stories/{story_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
    data = r.json()
    slug = data.get("slug", "unknown")
    _remove_pending(story_id)
    print(f"  Published: {SERVER_BASE}/story/{slug}")


# ── Phase 2b: Reject ──────────────────────────────────────────────────────────

def reject_story(story_id: int) -> None:
    print(f"\n🗑️  Rejecting story #{story_id}...")
    token = _get_admin_token()
    with httpx.Client(timeout=15) as client:
        r = client.patch(
            f"{SERVER_BASE}/api/stories/{story_id}/reject",
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
    _remove_pending(story_id)
    print(f"  Story #{story_id} removed.\n")


# ── List pending ──────────────────────────────────────────────────────────────

def list_pending() -> None:
    entries = _load_pending()
    if not entries:
        print("  No pending stories.\n")
        return
    print(f"\n{'ID':>6}  {'Genre':<16}  {'Title':<45}  {'Generated'}")
    print("-" * 82)
    for e in entries:
        print(f"  {e.get('story_id', '?'):>4}  {e.get('genre', '?'):<16}  {e.get('title', '?')[:45]:<45}  {e.get('generated_at', '?')}")
    print()


# ── Auth helper ───────────────────────────────────────────────────────────────

def _get_admin_token() -> str:
    if token := os.getenv("AGENT_JWT_TOKEN"):
        return token
    admin_email    = os.getenv("ADMIN_EMAIL", "admin@myblogs.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    with httpx.Client(timeout=10) as client:
        r = client.post(
            f"{SERVER_BASE}/api/auth/login",
            json={"email": admin_email, "password": admin_password},
        )
        r.raise_for_status()
        return r.json()["access_token"]
