"""Steps 5 + 9: verify build, revert on failure, commit and push on success."""
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from ..state import RebrandState


def _run(args: list, cwd: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def _mask_token(text: str) -> str:
    return re.sub(r"github_pat_[A-Za-z0-9_]+", "***TOKEN***", text)


# ── Step 5 ────────────────────────────────────────────────────────────────────

def verify_build_node(state: RebrandState) -> dict:
    """Run `npm run build` in frontend/ and report pass/fail."""
    repo_root = state["repo_root"]
    frontend_dir = str(Path(repo_root) / "frontend")
    print("[build] Running npm run build...")
    t0 = time.time()
    try:
        result = _run(["npm", "run", "build"], cwd=frontend_dir, timeout=300)
    except subprocess.TimeoutExpired:
        return {"build_passed": False, "build_output": "Build timed out after 300s"}

    elapsed = round(time.time() - t0, 1)
    passed = result.returncode == 0
    output = (result.stdout or "")[-2000:]
    if result.stderr:
        output += "\n" + (result.stderr or "")[-1000:]

    print(f"[build] {'PASSED' if passed else 'FAILED'} in {elapsed}s")
    if not passed:
        print(output[-600:])
    return {"build_passed": passed, "build_output": output}


# ── Revert (called when build fails) ─────────────────────────────────────────

def revert_changes_node(state: RebrandState) -> dict:
    """Discard all uncommitted changes after a build failure."""
    repo_root = state["repo_root"]
    _run(["git", "checkout", "--", "."], cwd=repo_root)
    print("[revert] All changes reverted — repo left at HEAD.")
    return {"changes_reverted": True}


# ── Step 9 ────────────────────────────────────────────────────────────────────

def commit_push_node(state: RebrandState) -> dict:
    """Commit all rebrand file changes and push to origin main."""
    repo_root = state["repo_root"]
    chosen_theme = state.get("chosen_theme", "monthly theme")
    now = datetime.now(timezone.utc)
    month_year = now.strftime("%B %Y")
    commit_msg = f"rebrand: {chosen_theme} rebranding for {month_year}"

    def git(*args, timeout: int = 60) -> subprocess.CompletedProcess:
        return _run(["git"] + list(args), cwd=repo_root, timeout=timeout)

    # Set identity (idempotent — GHA may have already done this)
    git("config", "user.name", "Claude Theme Bot")
    git("config", "user.email", "bm80177@gmail.com")

    # Pull latest to avoid conflicts with concurrent pushes
    pull = git("pull", "--rebase", "origin", "main", timeout=90)
    if pull.returncode != 0:
        err = _mask_token(pull.stderr or pull.stdout)
        print(f"[publish] git pull warning: {err[:200]}")

    # Stage everything
    git("add", "-A")

    # Nothing to commit?
    status = git("status", "--porcelain")
    if not status.stdout.strip():
        print("[publish] Working tree is clean — nothing to commit.")
        return {"commit_sha": "", "push_success": True, "push_error": ""}

    # Commit
    commit = git("commit", "-m", commit_msg)
    if commit.returncode != 0:
        err = _mask_token(commit.stderr or commit.stdout)
        return {"push_success": False, "push_error": f"git commit failed: {err[:300]}"}

    sha_r = git("rev-parse", "--short", "HEAD")
    commit_sha = sha_r.stdout.strip()
    print(f"[publish] Committed {commit_sha}: {commit_msg}")

    # Push
    push = git("push", "origin", "main", timeout=90)
    push_ok = push.returncode == 0
    push_error = "" if push_ok else _mask_token(push.stderr or push.stdout)[:400]

    if push_ok:
        print(f"[publish] Pushed to origin/main successfully.")
    else:
        print(f"[publish] Push failed: {push_error}")

    return {"commit_sha": commit_sha, "push_success": push_ok, "push_error": push_error}
