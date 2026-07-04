#!/bin/sh
# Waits for CodeQL's own check runs on this commit to finish, then applies a
# CUSTOM severity gate against the repo's open Code Scanning alerts. GitHub
# Code Scanning has no native "fail the build on severity count" gate — the
# codeql-action/analyze step always succeeds regardless of findings — so this
# mirrors scripts/sonar-quality-gate.sh's approach instead of relying on one:
#
#   FAIL if any open alert has security severity CRITICAL
#   FAIL if more than 2 open alerts have security severity HIGH
#   otherwise PASS
#
# Requires GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_SHA in the environment
# (all set automatically inside GitHub Actions).
set -e

API="https://api.github.com/repos/$GITHUB_REPOSITORY"

echo "Waiting for CodeQL analysis on $GITHUB_SHA to finish..."
STATUS=""
for i in $(seq 1 40); do
  RUNS=$(curl -sf -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github+json" \
    "$API/commits/$GITHUB_SHA/check-runs?per_page=100")
  STATUS=$(echo "$RUNS" | python3 -c "
import sys, json
runs = [r for r in json.load(sys.stdin)['check_runs'] if r['name'].startswith('Analyze (')]
if not runs:
    print('missing')
elif all(r['status'] == 'completed' for r in runs):
    print('completed')
else:
    print('pending')
")
  if [ "$STATUS" = "completed" ]; then break; fi
  sleep 15
done

if [ "$STATUS" != "completed" ]; then
  echo "FAILED: CodeQL analysis did not complete in time (status: $STATUS)"
  exit 1
fi

python3 <<'PYEOF'
import json, os, sys, urllib.request

repo = os.environ["GITHUB_REPOSITORY"]
token = os.environ["GITHUB_TOKEN"]
api = f"https://api.github.com/repos/{repo}"
headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

def get(path):
    req = urllib.request.Request(f"{api}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

criticals, highs = [], []
page = 1
while True:
    alerts = get(f"/code-scanning/alerts?state=open&per_page=100&page={page}")
    if not alerts:
        break
    for alert in alerts:
        level = (alert.get("rule") or {}).get("security_severity_level")
        loc = (alert.get("most_recent_instance") or {}).get("location", {})
        entry = f"  {level}: {loc.get('path', '?')}:{loc.get('start_line', '?')} — {alert['rule']['description']}"
        if level == "critical":
            criticals.append(entry)
        elif level == "high":
            highs.append(entry)
    if len(alerts) < 100:
        break
    page += 1

print(f"Open CodeQL alerts (security severity): {len(criticals)} critical, {len(highs)} high")

failed = False
if criticals:
    failed = True
    print(f"FAILED: {len(criticals)} critical vulnerability(ies) found (must be 0):")
    for c in criticals:
        print(c)
if len(highs) > 2:
    failed = True
    print(f"FAILED: {len(highs)} high-severity vulnerabilities found (must be <= 2):")
    for h in highs:
        print(h)

if failed:
    print(f"See: https://github.com/{repo}/security/code-scanning")
    sys.exit(1)

print("CodeQL security gate: OK (0 critical, <= 2 high)")
PYEOF
