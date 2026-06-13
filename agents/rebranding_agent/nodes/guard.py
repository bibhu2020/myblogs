"""Step 0: first-Sunday guard — skip if not the first Sunday of the month."""
import subprocess
from datetime import datetime, timezone
from ..state import RebrandState


def check_first_sunday_node(state: RebrandState) -> dict:
    """Only proceed if today is the first Sunday of the month (day 01–07)."""
    try:
        result = subprocess.run(["date", "+%d"], capture_output=True, text=True, check=True)
        day = int(result.stdout.strip())
    except Exception:
        day = datetime.now(timezone.utc).day

    if day > 7:
        msg = f"Not the first Sunday — day {day:02d} is after day 07. Skipping this run."
        print(msg)
        return {"is_first_sunday": False, "skip_reason": msg}

    print(f"First-Sunday guard passed (day {day:02d}). Proceeding with rebrand.")
    return {"is_first_sunday": True, "skip_reason": ""}
