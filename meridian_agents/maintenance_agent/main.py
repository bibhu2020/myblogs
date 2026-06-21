"""Main entry point for the Meridian maintenance agent."""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from .agents import run_team  # noqa: E402
from .tracer import complete_run, start_run  # noqa: E402

REPO_ROOT = str(Path(__file__).parent.parent.parent)
SERVER_BASE = os.getenv("SERVER_BASE", "https://mishrabp-meridian.hf.space")


def run_maintenance() -> None:
    print("\n╔══════════════════════════════════════════╗")
    print("║     Meridian Maintenance Agent           ║")
    print("║   Dependabot · Sitemap · SEO/ADA         ║")
    print("╚══════════════════════════════════════════╝\n")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required. Add it to .env or export it first.")

    github_repo = os.getenv("GITHUB_REPO", "")
    print(f"Repo root  : {REPO_ROOT}")
    print(f"Server     : {SERVER_BASE}")
    print(f"GitHub repo: {github_repo or '(not set — Dependabot phase will be skipped)'}")
    print()

    run_id = start_run({"repo": REPO_ROOT, "serverBase": SERVER_BASE})
    print(f"Run ID: {run_id}\n")

    try:
        summary, findings = asyncio.run(run_team(REPO_ROOT, SERVER_BASE))
        complete_run(run_id, summary, findings)
        print(f"\n✅ Maintenance complete. Findings: {len(findings)}")
        if summary:
            print(f"\nSummary:\n{summary[:800]}")
    except Exception as exc:
        complete_run(run_id, str(exc), [], failed=True)
        raise
