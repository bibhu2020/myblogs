#!/bin/sh
# Polls the SonarQube analysis task started by `npm run sonar`, waits for
# server-side processing to finish, then applies a CUSTOM security-severity
# gate instead of SonarQube's built-in Quality Gate:
#
#   FAIL if any open vulnerability has Security impact severity BLOCKER (critical)
#   FAIL if more than 3 open vulnerabilities have Security impact severity HIGH
#   otherwise PASS
#
# SonarQube's built-in gate has no native condition for "count of vulnerabilities
# at a given severity" (only ratings A-E or unfiltered totals), so this script
# queries the Issues API directly and makes its own pass/fail decision. The
# built-in gate status is still printed below for visibility, but it is
# informational only — it does not affect this script's exit code.
#
# Requires SONAR_HOST_URL, SONAR_TOKEN, SONAR_PROJECT_KEY in the environment
# and .scannerwork/report-task.txt from the preceding scan.
set -e

TASK_ID=$(grep "^ceTaskId=" .scannerwork/report-task.txt | cut -d= -f2)
STATUS=""
for i in $(seq 1 30); do
  RESPONSE=$(curl -sf -u "$SONAR_TOKEN:" "$SONAR_HOST_URL/api/ce/task?id=$TASK_ID")
  STATUS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['task']['status'])")
  if [ "$STATUS" = "SUCCESS" ] || [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "CANCELED" ]; then break; fi
  sleep 10
done

if [ "$STATUS" != "SUCCESS" ]; then
  echo "Analysis task did not succeed (status: $STATUS)"
  exit 1
fi

GATE_RESPONSE=$(curl -sf -u "$SONAR_TOKEN:" \
  "$SONAR_HOST_URL/api/qualitygates/project_status?projectKey=$SONAR_PROJECT_KEY")
QG=$(echo "$GATE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['projectStatus']['status'])")
echo "SonarQube built-in Quality Gate status (informational only): $QG"

python3 <<'PYEOF'
import json, os, sys, base64, urllib.request

host = os.environ["SONAR_HOST_URL"]
token = os.environ["SONAR_TOKEN"]
project = os.environ["SONAR_PROJECT_KEY"]
auth = base64.b64encode(f"{token}:".encode()).decode()

def get(path):
    # A custom User-Agent is required: the server's edge (Cloudflare) blocks
    # Python's default "Python-urllib/x.y" signature with a 403 (error 1010),
    # while curl's UA is allowlisted — mimic it here.
    req = urllib.request.Request(
        f"{host}{path}",
        headers={"Authorization": f"Basic {auth}", "User-Agent": "curl/8.5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

# Legacy severity fallback for issues predating the Impact model.
LEGACY_MAP = {"BLOCKER": "BLOCKER", "CRITICAL": "HIGH"}

blockers, highs = [], []
page = 1
while True:
    data = get(
        f"/api/issues/search?componentKeys={project}&types=VULNERABILITY"
        f"&resolved=false&ps=500&p={page}"
    )
    for issue in data["issues"]:
        sec_severity = next(
            (imp["severity"] for imp in issue.get("impacts", [])
             if imp.get("softwareQuality") == "SECURITY"),
            None,
        )
        if sec_severity is None:
            sec_severity = LEGACY_MAP.get(issue.get("severity"))
        entry = (
            f"  {sec_severity}: {issue['component'].split(':', 1)[-1]}"
            f":{issue.get('line', '?')} — {issue['message']}"
        )
        if sec_severity == "BLOCKER":
            blockers.append(entry)
        elif sec_severity == "HIGH":
            highs.append(entry)
    total = data["paging"]["total"]
    if page * 500 >= total:
        break
    page += 1

print(f"Open vulnerabilities (Security impact): {len(blockers)} critical, {len(highs)} high")

failed = False
if blockers:
    failed = True
    print(f"FAILED: {len(blockers)} critical vulnerability(ies) found (must be 0):")
    for b in blockers:
        print(b)
if len(highs) > 3:
    failed = True
    print(f"FAILED: {len(highs)} high-severity vulnerabilities found (must be <= 3):")
    for h in highs:
        print(h)

if failed:
    print(f"See: {host}/project/issues?id={project}&types=VULNERABILITY&resolved=false")
    sys.exit(1)

print("Security gate: OK (0 critical, <= 3 high)")
PYEOF
