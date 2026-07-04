#!/bin/sh
# Applies a CUSTOM severity gate against the repo's open Code Scanning alerts.
# GitHub Code Scanning has no native "fail the build on severity count" gate —
# the codeql-action/analyze step always succeeds regardless of findings — so
# this mirrors scripts/sonar-quality-gate.sh's approach instead of relying on
# one:
#
#   FAIL if any open alert has security severity CRITICAL
#   FAIL if more than 2 open alerts have security severity HIGH
#   otherwise PASS
#
# Must run as a job with `needs: codeql` in the same workflow, so the analyze
# matrix has already finished by the time this runs. SARIF results still take
# a few seconds to finish processing into alerts after upload, hence the
# short retry loop below.
#
# Requires GITHUB_TOKEN, GITHUB_REPOSITORY in the environment (both set
# automatically inside GitHub Actions).
set -e

python3 <<'PYEOF'
import json, os, sys, time, urllib.request

repo = os.environ["GITHUB_REPOSITORY"]
token = os.environ["GITHUB_TOKEN"]
api = f"https://api.github.com/repos/{repo}"
headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

def get(path):
    req = urllib.request.Request(f"{api}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

def fetch_all_open_alerts():
    alerts = []
    page = 1
    while True:
        batch = get(f"/code-scanning/alerts?state=open&per_page=100&page={page}")
        if not batch:
            break
        alerts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return alerts

# SARIF processing lags slightly behind the analyze step finishing (an empty
# result here is ambiguous — genuinely zero alerts, or not processed yet — so
# a fixed pause is more honest than retrying-until-nonempty).
time.sleep(30)
alerts = fetch_all_open_alerts()

criticals, highs = [], []
for alert in alerts:
    level = (alert.get("rule") or {}).get("security_severity_level")
    loc = (alert.get("most_recent_instance") or {}).get("location", {})
    entry = f"  {level}: {loc.get('path', '?')}:{loc.get('start_line', '?')} — {alert['rule']['description']}"
    if level == "critical":
        criticals.append(entry)
    elif level == "high":
        highs.append(entry)

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
