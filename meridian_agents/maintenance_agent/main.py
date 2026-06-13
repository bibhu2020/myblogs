"""Main entry point for the Meridian maintenance agent."""
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from .agents import run_team  # noqa: E402
from .tracer import complete_run, start_run  # noqa: E402

REPO_ROOT = str(Path(__file__).parent.parent.parent)
SERVER_BASE = os.getenv("SERVER_BASE", "https://mishrabP-myblogs.hf.space")


def _check_schedule(force: bool) -> bool:
    """Return True (proceed) or False (skip).

    Maintenance runs on the 1st of each month.  The force flag bypasses
    the guard so operators can trigger a run on any day.
    """
    if force:
        print("[schedule] Force flag set — bypassing first-of-month guard.")
        return True
    day = datetime.now(timezone.utc).day
    if day != 1:
        print(f"[schedule] SKIP: Not the first of the month (day {day:02d}).")
        return False
    print(f"[schedule] First of the month confirmed (day {day:02d}). Proceeding.")
    return True


def run_maintenance() -> None:
    print("\n╔══════════════════════════════════════════╗")
    print("║     Meridian Maintenance Agent           ║")
    print("║         AutoGen / GPT-5 Edition          ║")
    print("╚══════════════════════════════════════════╝\n")

    force = os.getenv("FORCE_MAINTENANCE", "").lower() in ("1", "true", "yes")
    print(f"Force maintenance: {force}")

    if not _check_schedule(force):
        return

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required. Add it to .env or export it first.")

    run_id = start_run({"repo": REPO_ROOT, "serverBase": SERVER_BASE})
    print(f"Run ID: {run_id}\n")

    try:
        summary, findings = asyncio.run(run_team(REPO_ROOT, SERVER_BASE))
        complete_run(run_id, summary, findings)
        print(f"\n✅ Maintenance complete. Findings: {len(findings)}")
        if summary:
            print(f"\nSummary:\n{summary[:500]}")
    except Exception as exc:
        complete_run(run_id, str(exc), [], failed=True)
        raise
