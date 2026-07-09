#!/bin/sh
# Applies a CUSTOM gate against the repo's open Code Scanning alerts that
# originated from the DAST (OWASP ZAP) tool specifically.
#
# ZAP does not identify CVEs and has no CVSS-style numeric score — unlike SCA
# (which reports real, externally-assigned CVE/CVSS ratings from the GitHub
# Advisory Database) or CodeQL (whose security_severity_level is modeled on
# CVSS methodology by GitHub's own researchers), ZAP only classifies findings
# on its own internal Risk scale: Informational / Low / Medium / High, with
# no tier above High. zap-alerts-to-sarif.py only ever uploads ZAP's
# High-risk findings, and stamps them with security-severity "8.0" purely so
# GitHub's Code Scanning UI buckets them consistently alongside CodeQL/Sonar
# alerts — that number is a chosen display value, not a computed rating.
#
#   FAIL if any open ZAP-sourced (High-risk) alert exists
#   otherwise PASS
#
# Must run as a job with `needs: dast` in the same workflow, so the baseline
# scan's SARIF has already been uploaded by the time this runs. Alerts are
# filtered to tool.name == "OWASP ZAP" so this gate only judges DAST findings
# — CodeQL's own alerts are already covered separately by codeql-quality-gate.sh.
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

# SARIF processing lags slightly behind the upload-sarif step finishing (an
# empty result here is ambiguous — genuinely zero alerts, or not processed
# yet — so a fixed pause is more honest than retrying-until-nonempty).
time.sleep(30)
alerts = [a for a in fetch_all_open_alerts()
          if (a.get("tool") or {}).get("name") == "OWASP ZAP"]

findings = []
for alert in alerts:
    loc = (alert.get("most_recent_instance") or {}).get("location", {})
    findings.append(
        f"  {loc.get('path', '?')} — {alert['rule']['description']}"
    )

print(f"Open DAST (ZAP) High-risk alerts: {len(findings)}")

if findings:
    print(f"FAILED: {len(findings)} High-risk DAST finding(s) found (must be 0):")
    for f in findings:
        print(f)
    print(f"See: https://github.com/{repo}/security/code-scanning")
    sys.exit(1)

print("DAST security gate: OK (0 High-risk findings)")
PYEOF
