"""Entry point: python -m meridian_agents.post_agent [approve|reject|pending|registry-remove|schedule] [args]"""
import sys
import time

cmd = sys.argv[1] if len(sys.argv) >= 2 else "generate"

# ── approve <post_id> ─────────────────────────────────────────────────────────
if cmd == "approve":
    if len(sys.argv) < 3:
        print("Usage: python3 -m meridian_agents.post_agent approve <post_id>")
        sys.exit(1)
    from .main import approve_post
    try:
        approve_post(int(sys.argv[2]))
    except Exception as e:
        print(f"❌ Approve failed: {e}", file=sys.stderr)
        sys.exit(1)

# ── reject <post_id> ──────────────────────────────────────────────────────────
elif cmd == "reject":
    if len(sys.argv) < 3:
        print("Usage: python3 -m meridian_agents.post_agent reject <post_id>")
        sys.exit(1)
    from .main import reject_post
    try:
        reject_post(int(sys.argv[2]))
    except Exception as e:
        print(f"❌ Reject failed: {e}", file=sys.stderr)
        sys.exit(1)

# ── pending — list pending posts ──────────────────────────────────────────────
elif cmd == "pending":
    from .main import list_pending
    list_pending()

# ── schedule <cron_expr> ──────────────────────────────────────────────────────
elif cmd == "schedule":
    cron_expr = sys.argv[2] if len(sys.argv) >= 3 else ""
    if not cron_expr:
        print("Usage: python3 -m meridian_agents.post_agent schedule '0 8 * * 1'")
        sys.exit(1)

    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")

    from croniter import croniter
    from datetime import datetime

    if not croniter.is_valid(cron_expr):
        print(f'❌ Invalid cron expression: "{cron_expr}"')
        sys.exit(1)

    from .main import run_agent

    print(f"⏰ Meridian Post Agent scheduler (human-in-the-loop mode)")
    print(f"   Schedule: {cron_expr} (UTC)\n")

    running = False
    cron = croniter(cron_expr)
    while True:
        next_run = cron.get_next(datetime)
        wait = (next_run - datetime.utcnow()).total_seconds()
        if wait > 0:
            m, s = divmod(int(wait), 60)
            h, m = divmod(m, 60)
            print(f"⏳ Next run: {next_run.strftime('%Y-%m-%d %H:%M UTC')} (in {h:02d}:{m:02d}:{s:02d})")
            time.sleep(wait)
        if running:
            print(f"[{datetime.utcnow().isoformat()}] Skipping — previous run still in progress")
            continue
        running = True
        print(f"\n[{datetime.utcnow().isoformat()}] Scheduled run triggered")
        try:
            run_agent()
        except Exception as err:
            print(f"Scheduled run failed: {err}")
        finally:
            running = False

# ── registry-remove <post_id> — remove from pending JSONL without API call ────
# Used by the on-post-decision workflow after the blog-service has already
# handled the approve/reject; this only syncs the local pending registry.
elif cmd == "registry-remove":
    if len(sys.argv) < 3:
        print("Usage: python3 -m meridian_agents.post_agent registry-remove <post_id>")
        sys.exit(1)
    from .main import _remove_pending
    post_id = int(sys.argv[2])
    _remove_pending(post_id)
    print(f"✅ Post #{post_id} removed from pending registry.")

# ── generate (default) ────────────────────────────────────────────────────────
else:
    from .main import run_agent
    try:
        run_agent()
    except Exception as e:
        print(f"\n❌ Agent failed: {e}", file=sys.stderr)
        sys.exit(1)
