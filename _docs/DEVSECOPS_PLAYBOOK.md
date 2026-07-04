# DevSecOps Pipeline Setup Playbook

A portable runbook for replicating this repo's automated security scanning
pipeline (SAST + SCA + DAST, all as GitHub Actions PR checks) in another
project. This is the **how-to / copy-paste** version — for the full
narrative explanation of *why* each piece exists and exactly how it's wired
up here, see [`devsecops.pdf`](./devsecops.pdf) in this same folder. That
doc is Meridian-specific; this one is meant to travel.

Placeholders are written as `<LIKE_THIS>` — replace them for your project.
Everything else is a working template lifted directly from this repo.

---

## What you end up with

One GitHub Actions workflow (`pr-check.yml`) that runs on every pull
request and covers three categories, each gated independently:

| Category | Tools | What it checks |
|---|---|---|
| **SAST** | SonarQube + CodeQL | Your own source code, without running it |
| **SCA** | Dependabot + Dependency Review Action | Third-party dependencies, for known CVEs |
| **DAST** | OWASP ZAP (baseline scan) | The app while actually running, from the outside |

Two design decisions carry through everything below, worth internalizing
before copying files:

1. **Custom gates over native ones, where the tool has no built-in one.**
   SonarQube has a real Quality Gate API to poll. CodeQL and Dependabot
   alerts don't — `codeql-action/analyze` and Dependabot always "succeed"
   regardless of findings. Where there's no native gate, this playbook adds
   a small script that queries results directly and decides pass/fail
   itself (see `scripts/*.sh` below).
2. **One workflow file, not one per tool.** A gate job that needs to know
   "has the scan job finished yet" can only declare a native `needs:`
   dependency on a job *in the same workflow file* — not across separate
   workflow runs. Keeping SAST/SCA/DAST jobs in one file lets gate jobs use
   `needs:` instead of polling the Checks API to work around a file
   boundary.

---

## Prerequisites

- [ ] GitHub repository. **Public repos get CodeQL, Dependabot, and
      Dependency Review for free.** Private repos need a GitHub Advanced
      Security license for CodeQL and Dependency Review (Dependabot alerts
      are free either way).
- [ ] Admin access to the repo's **Settings** tab (several steps below are
      Settings toggles, not files).
- [ ] (Only if using SonarQube) A running SonarQube server — self-hosted or
      SonarCloud — and an account with permission to create a project token.
- [ ] A single, unified way to install dependencies and run tests for your
      project (a root `package.json`/`pyproject.toml`/equivalent). If your
      repo currently has multiple independent manifests, consolidate first
      — several steps below assume one root-level dependency tree.

---

## Step 1 — Enable GitHub-native features (Settings, no files)

**Settings → Code security and analysis.** Turn on:

- [ ] **Dependency graph** — required by Dependency Review (Step 5). Not
      always on by default even for public repos on some org configs —
      check it explicitly. If you skip this, Step 5's job fails with
      *"Dependency review is not supported on this repository."*
- [ ] **Dependabot alerts** — the actual SCA lookup. Notifies on
      already-known-vulnerable dependencies, independent of any PR.
- [ ] **Dependabot security updates** — auto-opens a PR to patch a
      dependency the moment an alert fires on it, independent of any
      schedule. (This is a *different* feature from the version-update
      config in Step 2, easy to conflate — see `devsecops.pdf` Section 2.2
      if you want the full distinction.)

None of these three need a workflow file or a line of code — they're pure
repo settings.

---

## Step 2 — Dependabot version updates (`.github/dependabot.yml`)

```yaml
version: 2

updates:
  - package-ecosystem: <npm | pip | maven | gomod | ...>
    directory: /
    schedule:
      interval: weekly
      day: monday
      time: "06:00"
    open-pull-requests-limit: 10

  # Repeat one block per ecosystem your repo actually uses.
  # - package-ecosystem: pip
  #   directory: /
  #   schedule: {interval: weekly, day: monday, time: "06:00"}
  #   open-pull-requests-limit: 5
```

- `directory: /` assumes one root manifest per ecosystem. If your repo
  still has multiple independent manifests (e.g. a monorepo with
  per-service `package.json`), add one entry per directory — but consider
  consolidating first (see Prerequisites); a single root entry keeps this
  whole pipeline simpler everywhere, not just here.
- Deliberately no `groups:` key — each bump stays its own individual PR.
  If you have automation that parses PR titles (a merge bot, a bump-review
  script), a batched multi-package PR breaks that; leave grouping off
  unless you specifically want fewer, bigger PRs.

---

## Step 3 — SonarQube (SAST #1)

Skip this whole step if you don't have/want a SonarQube server — CodeQL
(Step 4) alone still gives you real SAST coverage, just narrower (see
`devsecops.pdf` Section 1.4 for the trade-off in both directions).

### 3.1 — Secrets
Add three **repository secrets** (Settings → Secrets and variables →
Actions): `SONAR_TOKEN`, `SONAR_HOST_URL`, `SONAR_PROJECT_KEY`.

### 3.2 — `sonar-project.properties` (repo root)
```properties
sonar.projectKey=${SONAR_PROJECT_KEY}
sonar.projectName=<Your Project Name>

sonar.sources=.
sonar.exclusions=\
  **/node_modules/**,\
  **/dist/**,\
  **/*.db,\
  **/uploads/**,\
  **/coverage/**,\
  **/.github/**

# Add per-language file suffix / coverage report lines as needed, e.g.:
sonar.javascript.file.suffixes=.js,.mjs,.cjs
sonar.typescript.file.suffixes=.ts,.tsx
sonar.javascript.lcov.reportPaths=coverage/lcov.info
sonar.python.coverage.reportPaths=coverage-python.xml

sonar.sourceEncoding=UTF-8
```
`${SONAR_PROJECT_KEY}` here only works if your scanner substitutes
`${env.VAR}`-style references — otherwise pass `-Dsonar.projectKey=...`
explicitly on the command line instead (below), which is what this repo
actually does.

### 3.3 — Install the scanner + add scripts
```bash
npm install --save-dev @sonar/scan   # or the sonar-scanner CLI for your ecosystem
```
```json
{
  "scripts": {
    "sonar": "sh -c 'sonar-scanner -Dsonar.projectKey=\"$SONAR_PROJECT_KEY\" -Dsonar.scanner.socketTimeout=300 -Dsonar.scanner.responseTimeout=300'",
    "sonar:gate": "sh scripts/sonar-quality-gate.sh",
    "sonar:check": "npm run sonar && npm run sonar:gate"
  }
}
```
The scan command is wrapped in `sh -c '...'` deliberately — if your CI
shell expands `$SONAR_PROJECT_KEY` before the secret is injected into the
environment, you get an empty value. The inner shell defers expansion.

### 3.4 — Custom Quality Gate script (`scripts/sonar-quality-gate.sh`)
SonarQube's built-in gate can only threshold on ratings/percentages, not
"count of vulnerabilities at a given severity." If that's the policy you
want (e.g. "0 critical, ≤3 high"), you need a custom script:

```sh
#!/bin/sh
set -e

TASK_ID=$(grep "^ceTaskId=" .scannerwork/report-task.txt | cut -d= -f2)
for i in $(seq 1 30); do
  RESPONSE=$(curl -sf -u "$SONAR_TOKEN:" "$SONAR_HOST_URL/api/ce/task?id=$TASK_ID")
  STATUS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['task']['status'])")
  [ "$STATUS" = "SUCCESS" ] || [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "CANCELED" ] && break
  sleep 10
done
[ "$STATUS" = "SUCCESS" ] || { echo "Analysis task did not succeed ($STATUS)"; exit 1; }

python3 <<'PYEOF'
import json, os, sys, base64, urllib.request

host, token, project = os.environ["SONAR_HOST_URL"], os.environ["SONAR_TOKEN"], os.environ["SONAR_PROJECT_KEY"]
auth = base64.b64encode(f"{token}:".encode()).decode()

def get(path):
    req = urllib.request.Request(f"{host}{path}", headers={"Authorization": f"Basic {auth}", "User-Agent": "curl/8.5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

CRITICAL_MAX, HIGH_MAX = 0, 3   # <-- tune your own thresholds here
blockers, highs, page = [], [], 1
while True:
    data = get(f"/api/issues/search?componentKeys={project}&types=VULNERABILITY&resolved=false&ps=500&p={page}")
    for issue in data["issues"]:
        sev = next((i["severity"] for i in issue.get("impacts", []) if i.get("softwareQuality") == "SECURITY"), issue.get("severity"))
        (blockers if sev in ("BLOCKER",) else highs if sev == "HIGH" else []).append(issue)
    if page * 500 >= data["paging"]["total"]:
        break
    page += 1

failed = len(blockers) > CRITICAL_MAX or len(highs) > HIGH_MAX
print(f"{len(blockers)} critical, {len(highs)} high (limits: {CRITICAL_MAX}/{HIGH_MAX})")
sys.exit(1 if failed else 0)
PYEOF
```
> Note: a custom `User-Agent` header is required against some SonarQube
> deployments — a default Python UA can get blocked (HTTP 403) by an
> edge/CDN in front of the server even though `curl`'s isn't.

### 3.5 — Coverage (optional but recommended)
If you want the gate to also consider test coverage, generate a report in
whatever format your test runner supports (LCOV for JS/TS, Cobertura XML
for Python, etc.) **before** running `npm run sonar` — the scan only reads
whatever's already on disk, it doesn't run your tests itself. Point
`sonar.javascript.lcov.reportPaths` / `sonar.python.coverage.reportPaths`
(Step 3.2) at those files.

### 3.6 — CI job
```yaml
sonarqube:
  runs-on: ubuntu-latest
  permissions: { pull-requests: read }
  steps:
    - uses: actions/checkout@v4
      with: { fetch-depth: 0 }
    - uses: actions/setup-node@v4          # + setup-python, etc. as needed
    - run: npm ci --ignore-scripts
    - run: <your test/coverage command>
      continue-on-error: true              # don't let a flaky coverage step block the scan itself
    - name: SonarQube Scan
      env: { SONAR_TOKEN: "${{ secrets.SONAR_TOKEN }}", SONAR_HOST_URL: "${{ secrets.SONAR_HOST_URL }}", SONAR_PROJECT_KEY: "${{ secrets.SONAR_PROJECT_KEY }}" }
      run: npm run sonar
    - name: SonarQube Quality Gate check
      env: { SONAR_TOKEN: "${{ secrets.SONAR_TOKEN }}", SONAR_HOST_URL: "${{ secrets.SONAR_HOST_URL }}", SONAR_PROJECT_KEY: "${{ secrets.SONAR_PROJECT_KEY }}" }
      run: npm run sonar:gate
```

---

## Step 4 — CodeQL (SAST #2)

### 4.1 — `.github/codeql/codeql-config.yml`
```yaml
name: "CodeQL config"

queries:
  - uses: security-extended

paths-ignore:
  - "**/node_modules/**"
  - "**/dist/**"
  - "**/coverage/**"
  - "**/*.db"
```
Mirror whatever you put in `sonar.exclusions` (Step 3.2) so both tools
scan the same real source.

### 4.2 — CI jobs
```yaml
codeql:
  permissions: { security-events: write, actions: read, contents: read }
  strategy:
    fail-fast: false
    matrix:
      language: [<javascript-typescript, python, java, go, ...>]   # pick what your repo actually contains
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4          # only if a matrix leg needs it to resolve imports
      if: matrix.language == 'javascript-typescript'
    - run: npm ci --ignore-scripts
      if: matrix.language == 'javascript-typescript'
    - uses: github/codeql-action/init@v3
      with:
        languages: ${{ matrix.language }}
        config-file: ./.github/codeql/codeql-config.yml
    - uses: github/codeql-action/autobuild@v3
    - uses: github/codeql-action/analyze@v3
      with: { category: "/language:${{ matrix.language }}" }

codeql-gate:
  needs: codeql       # only works because this job is in the SAME workflow file
  permissions: { security-events: read, contents: read }
  steps:
    - uses: actions/checkout@v4
    - env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
      run: sh scripts/codeql-quality-gate.sh
```
For **compiled** languages, `autobuild` needs your project to actually be
buildable in this job (add real build steps before it, or replace
`autobuild` with your own build command). For interpreted languages
(Python, Ruby, JS/TS), it's a no-op.

### 4.3 — Custom severity gate (`scripts/codeql-quality-gate.sh`)
`codeql-action/analyze` always exits 0 regardless of findings — there's no
native "fail on severity count" gate.
```sh
#!/bin/sh
set -e
python3 <<'PYEOF'
import json, os, sys, time, urllib.request

repo, token = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
api = f"https://api.github.com/repos/{repo}"
headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

def get(path):
    req = urllib.request.Request(f"{api}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

# A finished `analyze` step means the SARIF upload was accepted, not that
# GitHub has finished turning it into queryable alerts yet — a short pause
# is more honest than retrying-until-nonempty (which can't distinguish
# "zero alerts" from "not processed yet").
time.sleep(30)

alerts, page = [], 1
while True:
    batch = get(f"/code-scanning/alerts?state=open&per_page=100&page={page}")
    if not batch:
        break
    alerts += batch
    if len(batch) < 100:
        break
    page += 1

CRITICAL_MAX, HIGH_MAX = 0, 2   # <-- tune your own thresholds here
criticals = [a for a in alerts if (a.get("rule") or {}).get("security_severity_level") == "critical"]
highs     = [a for a in alerts if (a.get("rule") or {}).get("security_severity_level") == "high"]
print(f"{len(criticals)} critical, {len(highs)} high (limits: {CRITICAL_MAX}/{HIGH_MAX})")
sys.exit(1 if (len(criticals) > CRITICAL_MAX or len(highs) > HIGH_MAX) else 0)
PYEOF
```

---

## Step 5 — Dependency Review Action (SCA #2)

Requires **Dependency graph** enabled (Step 1) — the single most common
setup failure here, with a clear error message telling you exactly that.

```yaml
dependency-review:
  permissions: { contents: read }
  steps:
    - uses: actions/checkout@v4
    - uses: actions/dependency-review-action@v4
      with:
        fail-on-severity: high   # blocks the PR if its diff introduces anything high/critical
```
This has a **native** gate (`fail-on-severity`) — no custom script needed,
unlike Steps 3/4. It only ever looks at what a PR's diff changes in
manifests/lockfiles, not the whole existing tree (that's what Dependabot
alerts, Step 1, are for).

---

## Step 6 — OWASP ZAP baseline scan (DAST)

This is the one step that genuinely depends on your project's own shape —
adapt the "start the app" step to however your project actually boots.

```yaml
dast:
  permissions: { contents: read, security-events: write }   # write only needed for the SARIF upload below
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4          # swap for whatever your stack needs
    - run: npm ci

    - name: Start the app
      run: |
        <YOUR_APP_START_COMMAND> > /tmp/app.log 2>&1 &
        for i in $(seq 1 30); do
          if curl -sf http://localhost:<YOUR_APP_PORT> >/dev/null 2>&1; then
            echo "App is up"; exit 0
          fi
          sleep 2
        done
        echo "App did not become ready in time"; cat /tmp/app.log; exit 1

    - name: ZAP Baseline Scan
      uses: zaproxy/action-baseline@v0.15.0
      with:
        target: 'http://localhost:<YOUR_APP_PORT>'
        fail_action: false        # flip to true only after seeing a real baseline run's results
        allow_issue_writing: false  # avoid needing issues: write permission
        artifact_name: 'zap-baseline-report'

    # Optional: get High-risk ZAP findings onto the Security tab. zap-baseline.py
    # doesn't expose ZAP's own SARIF report template, so this repo hand-converts
    # instead — same "own script over relying on tool internals" pattern as the
    # SonarQube/CodeQL gates in Steps 3-4. See scripts/zap-alerts-to-sarif.py.
    #
    # report_json.json is action-baseline's own default JSON report path — it
    # writes this file itself, unprompted. Don't try to redirect it via
    # cmd_options' -J flag: the action's own post-processing step expects the
    # report at exactly that filename and fails outright if zap-baseline.py
    # was told (via an extra -J) to write somewhere else instead — a real
    # mistake made (and fixed) while building this out.
    - run: python3 scripts/zap-alerts-to-sarif.py report_json.json zap-high.sarif
    - uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: zap-high.sarif
        category: zap-baseline   # keep separate from CodeQL's own SARIF categories
```
This step needs `security-events: write` added to the job's `permissions:` block
(alongside `contents: read`) — the SARIF upload is the only reason this job
needs write access to anything.

Notes that generalize regardless of stack:
- **Use the fastest boot path that serves real, crawlable HTML** — not
  necessarily your production Docker image, if that image bundles slow
  unrelated build steps (native deps, ML model downloads, etc.) DAST
  doesn't need. Point ZAP at whatever serves your actual frontend/HTML, not
  a bare JSON API with nothing for the passive spider to crawl.
- **Start with `fail_action: false`.** You don't yet know your app's normal
  finding count (missing security headers are extremely common on
  dev-mode servers and may not reflect your real production config at
  all). Run it a few times, look at the log's `WARN-NEW`/`FAIL-NEW` counts,
  *then* decide a real threshold — same "observe before you gate" pattern
  as Steps 3/4's custom scripts.
- This is a **passive-only** scan (spider + response inspection, no attack
  payloads) — safe to run against real seeded/demo data. If you want a
  full active scan instead (`zaproxy/action-full-scan`), understand first
  that it *will* submit every form it finds, including ones that
  create/delete real data.
- GitHub-hosted **Linux** runners execute Docker-based actions (which is
  what this is, under the hood) with host networking, so `localhost`
  inside ZAP's container reaches your app on the same runner. This does
  not necessarily hold on other runner OSes.
- **The SARIF conversion only forwards High-risk alerts.** ZAP's risk
  scale is Informational/Low/Medium/High — there's no "Critical" tier
  above High the way CodeQL has one above High, so "high or critical"
  for ZAP just means High. Everything else (commonly the missing-header
  findings a dev-mode server produces) stays out of the Security tab —
  still visible in the artifact/log, just not made permanent there. If
  your project's `zap-baseline.py`/action version ever ships native SARIF
  output directly, you can drop the custom converter script entirely; as
  of writing, `zaproxy/action-baseline` doesn't expose that template, so
  this repo hand-builds a minimal SARIF file from ZAP's own JSON report
  instead (`scripts/zap-alerts-to-sarif.py`).

---

## Step 7 — Assemble into one workflow file

```yaml
name: PR Checks

on:
  pull_request:
    branches: [<main>]

jobs:
  build-check:      # your normal build/test job(s)
    ...
  sonarqube:        # Step 3.6
    ...
  codeql:           # Step 4.2
    ...
  codeql-gate:      # Step 4.2 — needs: codeql
    ...
  dependency-review:  # Step 5
    ...
  dast:             # Step 6
    ...
```

All jobs share the single `on: pull_request` trigger. If you want CodeQL
to *also* run on a schedule or on push (catching drift outside of PR
activity, which this single-trigger-file approach gives up), that job
needs its own standalone workflow file instead — but then its gate job
can no longer use `needs:` and has to poll the Checks API across workflow
runs instead. Pick one trade-off deliberately; don't end up with both a
standalone file *and* a `needs:`-based gate expecting it to be local.

---

## Verification checklist

- [ ] Open a throwaway PR. Confirm every job in the table at the top of
      this doc appears as a check.
- [ ] `Build all services` (or your build-check job) passes on the
      unmodified branch.
- [ ] `SonarQube Scan` uploads and `SonarQube Quality Gate check` reports a
      real pass/fail (not an auth error — check the three secrets first).
- [ ] `CodeQL Analyze (<language>)` passes, and results appear under repo
      **Security → Code scanning alerts** within a few minutes.
- [ ] `CodeQL Security Gate` passes (0 critical / your threshold).
- [ ] `Dependency Review` passes. Temporarily add a known-old, known-CVE
      package version to a manifest in the test PR to confirm it actually
      fails when it should, then revert.
- [ ] `OWASP ZAP Baseline Scan` completes and uploads its artifact; check
      the job log for the `WARN-NEW`/`FAIL-NEW` summary line. If any alert
      is High risk, confirm it also lands on **Security → Code scanning
      alerts** under the `zap-baseline` category within a few minutes.
- [ ] Repo **Security → Dependabot alerts** shows 0 (or your known/
      accepted baseline) — confirms Step 1's toggles are really on.
- [ ] Wait for (or manually trigger) a Dependabot version-update PR;
      confirm it's titled like a plain "Bump X from A to B" with no
      advisory reference (a *security update* PR would reference one
      instead — see `devsecops.pdf` Section 2.2 if you need to tell them
      apart).

---

## What does *not* transfer automatically

- **Gate thresholds** (`CRITICAL_MAX`/`HIGH_MAX` in both custom scripts,
  `fail-on-severity` for Dependency Review, `fail_action` for ZAP) are a
  policy decision for your team, not a technical default — this playbook's
  numbers are what this repo settled on after seeing real results, not a
  universal recommendation.
- **`sonar.exclusions` / CodeQL `paths-ignore`** need to match your actual
  project layout (build output dirs, vendored code, generated files).
- **SonarQube findings never reach GitHub's Security tab in this setup** —
  they live only on its own server UI, SARIF or not; that's a separate
  system by design, not a gap to close.
- **ZAP's Security-tab coverage is High-risk-only, by choice, not by tool
  limitation.** Step 6 already includes the SARIF-conversion + `upload-
  sarif` step — but only High-risk alerts get converted. Medium/Low/Info
  findings stay artifact/log-only. If you want everything ZAP finds on the
  Security tab, loosen the filter in `scripts/zap-alerts-to-sarif.py`
  (`HIGH_RISKCODE` constant) — just expect header-hardening noise from a
  dev-mode server to show up there too.
