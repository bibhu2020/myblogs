"""Entry point: python -m post_agent"""
import sys
import os
import time

# Support: python -m post_agent schedule '0 8 * * 1'
if len(sys.argv) >= 2 and sys.argv[1] == "schedule":
    cron_expr = sys.argv[2] if len(sys.argv) >= 3 else ""
    if not cron_expr:
        print("❌ 'schedule' requires a cron expression, e.g.: python -m post_agent schedule '0 8 * * 1'")
        sys.exit(1)

    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    from croniter import croniter
    from datetime import datetime

    if not croniter.is_valid(cron_expr):
        print(f'❌ Invalid cron expression: "{cron_expr}"')
        print('   Examples: "0 8 * * 1"  (Monday 8 AM UTC)')
        sys.exit(1)

    from .main import run_post_agent

    print(f"⏰ Meridian AI Agent scheduler started")
    print(f"   Schedule: {cron_expr} (UTC)")
    print(f"   Press Ctrl+C to stop\n")

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
            run_post_agent()
        except Exception as err:
            print(f"Scheduled run failed: {err}")
        finally:
            running = False
else:
    from .main import run_post_agent
    try:
        run_post_agent()
    except Exception as e:
        print(f"\n❌ Agent failed: {e}", file=sys.stderr)
        sys.exit(1)
