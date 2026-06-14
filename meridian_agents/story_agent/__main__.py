"""Entry point: python -m meridian_agents.story_agent [approve|reject|pending|schedule] [args]"""
import sys
import time

cmd = sys.argv[1] if len(sys.argv) >= 2 else "generate"

if cmd == "approve":
    if len(sys.argv) < 3:
        print("Usage: python3 -m meridian_agents.story_agent approve <story_id>")
        sys.exit(1)
    from .main import approve_story
    try:
        approve_story(int(sys.argv[2]))
    except Exception as e:
        print(f"❌ Approve failed: {e}", file=sys.stderr)
        sys.exit(1)

elif cmd == "reject":
    if len(sys.argv) < 3:
        print("Usage: python3 -m meridian_agents.story_agent reject <story_id>")
        sys.exit(1)
    from .main import reject_story
    try:
        reject_story(int(sys.argv[2]))
    except Exception as e:
        print(f"❌ Reject failed: {e}", file=sys.stderr)
        sys.exit(1)

elif cmd == "pending":
    from .main import list_pending
    list_pending()

elif cmd == "schedule":
    cron_expr = sys.argv[2] if len(sys.argv) >= 3 else ""
    if not cron_expr:
        print("Usage: python3 -m meridian_agents.story_agent schedule '0 6 * * 1'")
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

    print(f"⏰ Meridian Story Agent scheduler")
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

else:
    from .main import run_agent
    try:
        run_agent()
    except Exception as e:
        print(f"\n❌ Story agent failed: {e}", file=sys.stderr)
        sys.exit(1)
