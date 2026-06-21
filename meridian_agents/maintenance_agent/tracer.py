"""HTTP tracer — creates and updates AgentRun records via the Meridian API."""
import json
import os
import uuid
from datetime import datetime, timezone

import requests

SERVER_BASE = os.getenv("SERVER_BASE", "https://mishrabp-meridian.hf.space")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_run(metadata: dict = {}) -> str:
    """Create a maintenance_agent run record and return the run_id."""
    run_id = str(uuid.uuid4())
    try:
        requests.post(
            f"{SERVER_BASE}/api/agent-runs",
            json={
                "agentType": "maintenance_agent",
                "runId": run_id,
                "startedAt": _now_iso(),
                "metadata": json.dumps(metadata),
            },
            timeout=15,
        )
    except Exception as exc:
        print(f"[tracer] Warning: could not create run record: {exc}")
    return run_id


def complete_run(run_id: str, summary: str, findings: list, failed: bool = False) -> None:
    """Update the run record as completed or failed."""
    try:
        requests.put(
            f"{SERVER_BASE}/api/agent-runs/{run_id}",
            json={
                "status": "failed" if failed else "completed",
                "completedAt": _now_iso(),
                "summary": summary,
                "findings": json.dumps(findings),
            },
            timeout=15,
        )
    except Exception as exc:
        print(f"[tracer] Warning: could not update run record: {exc}")
