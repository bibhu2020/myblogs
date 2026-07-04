#!/usr/bin/env python3
"""
Converts ZAP's native JSON report into a minimal SARIF 2.1.0 file containing
only High-risk alerts, so they (and only they) become persistent findings on
GitHub's Security tab via codeql-action/upload-sarif.

ZAP's risk scale tops out at High (riskcode "3") — there is no "Critical"
tier above it, unlike CodeQL's security_severity_level. "High or critical"
here means: everything ZAP is capable of calling severe.

Medium/Low/Informational findings (e.g. the missing-security-header
warnings a dev-mode server commonly produces) are deliberately excluded —
they still show up in the job log and the full HTML report artifact, just
not as permanent Security-tab entries.
"""
import json
import sys

HIGH_RISKCODE = "3"


def build_sarif(zap_report_path: str) -> dict:
    with open(zap_report_path) as f:
        report = json.load(f)

    rules = {}
    results = []
    for site in report.get("site", []):
        for alert in site.get("alerts", []):
            if alert.get("riskcode") != HIGH_RISKCODE:
                continue

            rule_id = f"zap-{alert.get('pluginid', alert.get('alertRef', 'unknown'))}"
            rules[rule_id] = {
                "id": rule_id,
                "name": alert.get("name", "ZAP Alert"),
                "shortDescription": {"text": alert.get("name", "ZAP Alert")},
                "fullDescription": {"text": alert.get("desc", "")},
                "help": {"text": alert.get("solution", "")},
                "properties": {"security-severity": "8.0", "tags": ["security", "zap-baseline"]},
            }

            instances = alert.get("instances") or [{}]
            for instance in instances:
                uri = instance.get("uri", site.get("@name", ""))
                results.append({
                    "ruleId": rule_id,
                    "level": "error",
                    "message": {"text": alert.get("desc", alert.get("name", ""))},
                    "locations": [{
                        "physicalLocation": {
                            "artifactLocation": {"uri": uri},
                        },
                    }],
                })

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "OWASP ZAP",
                    "informationUri": "https://www.zaproxy.org/",
                    "rules": list(rules.values()),
                },
            },
            "results": results,
        }],
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: zap-alerts-to-sarif.py <zap-report.json> <out.sarif>", file=sys.stderr)
        sys.exit(1)

    sarif = build_sarif(sys.argv[1])
    with open(sys.argv[2], "w") as f:
        json.dump(sarif, f, indent=2)

    n = len(sarif["runs"][0]["results"])
    print(f"Wrote {sys.argv[2]}: {n} High-risk finding(s) ({len(sarif['runs'][0]['tool']['driver']['rules'])} distinct rule(s))")
