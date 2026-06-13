"""Entry point for the rebranding agent."""
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from .graph import build_graph         # noqa: E402
from .tracer import complete_run, start_run  # noqa: E402


def _detect_repo_root() -> str:
    """Resolve the myblogs repo root from env vars or the git workspace."""
    if ws := os.getenv("GITHUB_WORKSPACE"):
        return ws
    if rr := os.getenv("REPO_ROOT"):
        return rr
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    raise RuntimeError(
        "Cannot find repo root. Set GITHUB_WORKSPACE or REPO_ROOT, "
        "or run from within the myblogs git repository."
    )


def _build_summary(state: dict) -> str:
    if not state.get("is_first_sunday"):
        return state.get("skip_reason", "Skipped — not the first Sunday.")

    lines = [
        f"Theme : {state.get('chosen_theme', '—')}",
        f"Mood  : {state.get('mood', '—')}",
        f"Events: {state.get('world_events', '—')[:200]}",
        "",
        f"Files changed : {', '.join(state.get('files_changed', [])) or 'none'}",
    ]
    if state.get("patch_errors"):
        lines.append(f"Patch warnings: {'; '.join(state['patch_errors'])}")

    if state.get("build_passed"):
        lines.append("Build         : PASSED")
        if state.get("push_success"):
            sha = state.get("commit_sha", "")
            lines.append(f"Push          : OK (commit {sha})")
        else:
            lines.append(f"Push          : FAILED — {state.get('push_error', '')}")
    else:
        lines.append("Build         : FAILED — changes reverted")

    if state.get("error"):
        lines.append(f"Error: {state['error']}")

    return "\n".join(lines)


def run_rebranding() -> None:
    print("\n╔══════════════════════════════════════════╗")
    print("║      Meridian Rebranding Agent           ║")
    print("║      LangGraph / GPT-4o Edition          ║")
    print("╚══════════════════════════════════════════╝\n")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required. Add it to .env or export it first.")

    repo_root = _detect_repo_root()
    print(f"Repo root: {repo_root}\n")

    now = datetime.now(timezone.utc)
    run_id = start_run({
        "repo": repo_root,
        "date": now.isoformat(),
    })

    graph = build_graph()
    initial_state = {"repo_root": repo_root}

    try:
        final_state = graph.invoke(initial_state)
    except Exception as exc:
        summary = f"Agent crashed: {exc}"
        complete_run(run_id, summary, failed=True)
        raise

    summary = _build_summary(final_state)
    failed = bool(final_state.get("error")) or (
        final_state.get("is_first_sunday") and not final_state.get("push_success")
    )
    complete_run(run_id, summary, failed=failed)

    print(f"\n{'=' * 50}")
    print(summary)
    print("=" * 50)
