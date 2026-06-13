"""PublisherAgent tools: git commit and push."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from agents import RunContextWrapper, function_tool

from ..context import RebrandCtx
from ._helpers import mask_token, run


@function_tool
def revert_changes(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Discard all uncommitted file changes via `git checkout -- .`

    Call this only when the build or tests failed fatally and the pipeline
    cannot continue — restores the repo to the last committed state.
    """
    run(["git", "checkout", "--", "."], cwd=ctx.context.repo_root)
    ctx.context.files_changed = []
    print("[publisher] All changes reverted — repo restored to HEAD.")
    return "Reverted — repo is clean."


@function_tool
def commit_and_push(ctx: RunContextWrapper[RebrandCtx]) -> str:
    """Commit all rebrand file changes and push to origin/main.

    Call this only after the TesterAgent confirms BUILD PASSED and TESTS PASSED.
    Returns a short status: commit SHA and push result, or an error description.
    """
    repo_root = ctx.context.repo_root
    chosen_theme = ctx.context.chosen_theme or "monthly theme"
    now = datetime.now(timezone.utc)
    month_year = now.strftime("%B %Y")
    commit_msg = f"rebrand: {chosen_theme} rebranding for {month_year}"

    def git(*args: str, timeout: int = 60):
        return run(["git", *args], cwd=repo_root, timeout=timeout)

    git("config", "user.name", "Claude Theme Bot")
    git("config", "user.email", "bm80177@gmail.com")

    git("add", "-A")
    status = git("status", "--porcelain")
    if not status.stdout.strip():
        print("[publisher] Working tree is clean — nothing to commit.")
        return "Nothing to commit — working tree already clean."

    commit = git("commit", "-m", commit_msg)
    if commit.returncode != 0:
        err = mask_token(commit.stderr or commit.stdout)
        return f"ERROR: git commit failed: {err[:300]}"

    sha = git("rev-parse", "--short", "HEAD").stdout.strip()
    print(f"[publisher] Committed {sha}: {commit_msg}")

    pull = git("pull", "--rebase", "origin", "main", timeout=90)
    if pull.returncode != 0:
        print(f"[publisher] git pull warning: {mask_token(pull.stderr or pull.stdout)[:200]}")

    push = git("push", "origin", "main", timeout=90)
    if push.returncode == 0:
        print("[publisher] Pushed to origin/main successfully.")
        return f"Pushed successfully. Commit: {sha}"

    err = mask_token(push.stderr or push.stdout)[:400]
    print(f"[publisher] Push failed: {err}")
    return f"Commit {sha} created but push failed: {err}"
