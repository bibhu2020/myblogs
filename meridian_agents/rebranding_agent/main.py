"""Entry point for the Meridian rebranding agent (OpenAI Agents SDK)."""
import asyncio
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from agents import Runner  # noqa: E402
from .agent import rebrand_agent  # noqa: E402
from .tools import RebrandCtx  # noqa: E402
from .tracer import complete_run, start_run  # noqa: E402


def _detect_repo_root() -> str:
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


async def _run_agent(repo_root: str, force_rebrand: bool) -> str:
    """Run the agent and return the final output string."""
    ctx = RebrandCtx(repo_root=repo_root, force_rebrand=force_rebrand)
    result = await Runner.run(
        rebrand_agent,
        input=(
            "Run the monthly Meridian website rebrand now. "
            f"Repo root: {repo_root}. "
            f"Force rebrand (bypass schedule): {force_rebrand}."
        ),
        context=ctx,
    )
    return result.final_output or "(no output)"


def run_rebranding() -> None:
    print("\n╔══════════════════════════════════════════╗")
    print("║    Meridian Rebranding Agent             ║")
    print("║    OpenAI Agents SDK Edition             ║")
    print("╚══════════════════════════════════════════╝\n")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required. Add it to .env or export it first.")

    repo_root = _detect_repo_root()
    force_rebrand = os.getenv("FORCE_REBRAND", "").lower() in ("1", "true", "yes")

    print(f"Repo root      : {repo_root}")
    print(f"Force rebrand  : {force_rebrand}")
    print(f"Date (UTC)     : {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n")

    run_id = start_run({
        "repo": repo_root,
        "force": force_rebrand,
        "date": datetime.now(timezone.utc).isoformat(),
    })

    try:
        summary = asyncio.run(_run_agent(repo_root, force_rebrand))
    except Exception as exc:
        summary = f"Agent crashed: {exc}"
        complete_run(run_id, summary, failed=True)
        raise

    failed = any(kw in summary.lower() for kw in ("build failed", "error:", "crashed"))
    complete_run(run_id, summary, failed=failed)

    print(f"\n{'=' * 50}")
    print(summary)
    print("=" * 50)
