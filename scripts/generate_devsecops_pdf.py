"""
Meridian — DevSecOps doc generator.
Produces _docs/devsecops.pdf: a user guide to this repo's automated security
scanning, organized by category — SAST (SonarQube, CodeQL) and SCA
(Dependabot, Dependency Review) — covering what each tool is, how it's
configured on GitHub and in code, and exactly how it's wired up here.
"""
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, ListFlowable, ListItem,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

DARK = colors.HexColor('#0d0d1a')
SLATE = colors.HexColor('#334155')
GRAY = colors.HexColor('#64748b')
BORDER = colors.HexColor('#e2e8f0')
CODE_BG = colors.HexColor('#f4f4f5')
NOTE_BG = colors.HexColor('#f8fafc')
TABLE_HEAD = colors.HexColor('#1e293b')

styles = getSampleStyleSheet()

title_style = ParagraphStyle('TitleX', parent=styles['Title'], fontName='Helvetica-Bold',
                              fontSize=22, alignment=TA_CENTER, spaceAfter=4, textColor=DARK)
subtitle_style = ParagraphStyle('SubtitleX', parent=styles['Normal'], fontName='Helvetica-Oblique',
                                 fontSize=10.5, alignment=TA_CENTER, textColor=GRAY, spaceAfter=18)
h1_style = ParagraphStyle('H1X', parent=styles['Heading1'], fontName='Helvetica-Bold',
                           fontSize=15, spaceBefore=16, spaceAfter=8, textColor=DARK)
h2_style = ParagraphStyle('H2X', parent=styles['Heading2'], fontName='Helvetica-Bold',
                           fontSize=11.5, spaceBefore=10, spaceAfter=5, textColor=SLATE)
body_style = ParagraphStyle('BodyX', parent=styles['Normal'], fontName='Helvetica',
                             fontSize=10, leading=14.5, spaceAfter=8, alignment=TA_LEFT)
bullet_style = ParagraphStyle('BulletX', parent=body_style, spaceAfter=4)
note_style = ParagraphStyle('NoteX', parent=styles['Normal'], fontName='Helvetica-Oblique',
                             fontSize=8.7, leading=12.5, textColor=GRAY, leftIndent=10)
code_style = ParagraphStyle('CodeX', parent=styles['Normal'], fontName='Courier',
                             fontSize=8.3, leading=11.5, textColor=DARK)
table_head_style = ParagraphStyle('TableHeadX', parent=styles['Normal'], fontName='Helvetica-Bold',
                                   fontSize=8.7, textColor=colors.white, leading=11)
table_body_style = ParagraphStyle('TableBodyX', parent=styles['Normal'], fontName='Helvetica',
                                   fontSize=8.7, leading=11.5)
table_body_mono_style = ParagraphStyle('TableBodyMonoX', parent=table_body_style, fontName='Courier', fontSize=8)


def code_block(text: str):
    p = Paragraph(text.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)
    t = Table([[p]], colWidths=[168 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


def note(text: str):
    p = Paragraph(text, note_style)
    t = Table([[p]], colWidths=[168 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NOTE_BG),
        ('LINEBEFORE', (0, 0), (0, -1), 2, BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(t, bullet_style), leftIndent=0) for t in items],
        bulletType='bullet', start='•', leftIndent=14, bulletFontSize=8, spaceBefore=2, spaceAfter=8,
    )


def metrics_table(rows, col_widths):
    header = [Paragraph(h, table_head_style) for h in rows[0]]
    data = [header]
    for r in rows[1:]:
        data.append([Paragraph(c, table_body_style) for c in r])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEAD),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]
    for i in range(2, len(data), 2):
        style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fafafa')))
    t.setStyle(TableStyle(style))
    return t


def build():
    out_path = os.path.join(os.path.dirname(__file__), '..', '_docs', 'devsecops.pdf')
    doc = SimpleDocTemplate(out_path, pagesize=A4,
                             topMargin=20 * mm, bottomMargin=18 * mm,
                             leftMargin=20 * mm, rightMargin=20 * mm)
    story = []

    story.append(Paragraph('DevSecOps: SAST &amp; SCA Scanning', title_style))
    story.append(Paragraph('A user guide to automated security scanning for the Meridian (myblogs) project', subtitle_style))

    story.append(Paragraph(
        'Every pull request into main runs two categories of automated security scanning, defined in '
        '<font face="Courier">.github/workflows/pr-check.yml</font> ("PR Checks") alongside the ordinary '
        'build/test jobs: <b>SAST</b>, which analyzes this project’s own source code, and <b>SCA</b>, which '
        'inspects the third-party packages it depends on. Each category is covered by more than one tool — '
        'not for redundancy, but because each tool catches a different slice of the problem, as explained in '
        'its own section below. A short reference table is at the very end (Section 3) if you just want the '
        'at-a-glance version.', body_style))

    # ══════════════════════════════════════════════════════════════════════
    # 1. SAST — Static Application Security Testing
    # ══════════════════════════════════════════════════════════════════════
    story.append(Paragraph('1. SAST — Static Application Security Testing', h1_style))
    story.append(Paragraph('1.1 What is SAST?', h2_style))
    story.append(Paragraph(
        'SAST analyzes a project’s <b>own source code</b> without running it, looking for bugs and '
        'exploitable security flaws — injection, XSS, hardcoded secrets, insecure crypto — directly in the '
        'code a developer wrote. It never touches third-party packages; that’s SCA’s job (Section 2). Two '
        'SAST tools run here, covering different depths of the same first-party code:', body_style))
    story.append(bullets([
        '<b>SonarQube</b> — broad code quality + security: bugs, vulnerabilities, code smells, security '
        'hotspots, duplication, and a coverage-gated Quality Gate.',
        '<b>CodeQL</b> — narrower but deeper: real interprocedural dataflow/taint-tracking specifically for '
        'security vulnerabilities, with fewer false positives on the bug classes it targets.',
    ]))
    story.append(note(
        'Why both, not one: SonarQube’s vulnerability detection is rule/pattern-based, which is fast and '
        'broad but can miss or over-flag findings that depend on how data actually moves through the '
        'program. CodeQL’s dataflow analysis is slower and narrower in scope, but traces that movement '
        'precisely. Running both means whichever style catches a given bug catches it — neither tool alone '
        'covers what the other does.'))

    # ── 1.2 SonarQube ─────────────────────────────────────────────────────
    story.append(Paragraph('1.2 SonarQube', h2_style))

    story.append(Paragraph(
        '<b>What it is &amp; what it’s used for.</b> A self-hosted static analysis platform that parses '
        'source (and ingests test coverage reports you provide) and evaluates the result against a '
        'configurable set of rules and thresholds called a <b>Quality Gate</b>. It checks four categories: '
        '<b>Bugs</b> (Reliability), <b>Vulnerabilities</b> (Security), <b>Code Smells</b> (maintainability), '
        'and <b>Security Hotspots</b> (security-sensitive code a human must manually confirm is or isn’t '
        'exploitable in context). Alongside issues, it also tracks <b>test coverage</b> and <b>duplicated '
        'code density</b> as gate conditions.', body_style))
    story.append(note(
        'SonarQube Community Edition (what this project uses) does not scan third-party dependencies for '
        'known CVEs — no SCA capability at all. That gap is exactly what Section 2’s tools cover.'))

    story.append(Paragraph(
        '<b>Configuring on GitHub.</b> Nothing to enable in repo Settings — SonarQube is self-hosted, not a '
        'GitHub-native feature. The only GitHub-side piece is three <b>repository secrets</b> '
        '(<font face="Courier">SONAR_TOKEN</font>, <font face="Courier">SONAR_HOST_URL</font>, '
        '<font face="Courier">SONAR_PROJECT_KEY</font>) that the CI job injects as environment variables — '
        'without them the scan/gate steps in <font face="Courier">pr-check.yml</font> fail outright, since '
        'there is no server to talk to.', body_style))

    story.append(Paragraph(
        '<b>Configuring in code.</b> Three files, each with one job:', body_style))
    story.append(bullets([
        '<font face="Courier">sonar-project.properties</font> (repo root) — what gets scanned, independent '
        'of secrets: <font face="Courier">sonar.sources</font> (scan root), '
        '<font face="Courier">sonar.exclusions</font> (keeps node_modules/, dist/, *.db, uploads/, '
        'coverage/, .github/ out of analysis), <font face="Courier">sonar.javascript.file.suffixes</font> / '
        '<font face="Courier">sonar.typescript.file.suffixes</font> (includes .vue as analyzable), and the '
        'two coverage report-path settings (Section 1.2, coverage below).',
        '<font face="Courier">package.json</font> scripts — <font face="Courier">sonar</font> runs the scan '
        '(the <font face="Courier">@sonar/scan</font> npm package’s <font face="Courier">sonar-scanner</font> '
        'binary — no Java install or Docker image needed), <font face="Courier">sonar:gate</font> checks the '
        'result, <font face="Courier">sonar:check</font> chains both.',
        '<font face="Courier">scripts/sonar-quality-gate.sh</font> — the actual gate logic (below), called '
        'identically by both a developer’s machine and CI so neither ever runs different logic than the '
        'other can reproduce.',
    ]))
    story.append(note(
        'sonar.projectKey=${SONAR_PROJECT_KEY} inside sonar-project.properties is a literal placeholder — '
        'SonarScanner only substitutes ${env.VAR_NAME}-style references. The real key is supplied explicitly '
        'on the command line instead (below), so this placeholder has no functional effect.'))

    story.append(Paragraph(
        '<b>How it’s done here.</b> Locally, with <font face="Courier">.env</font> populated with real '
        '<font face="Courier">SONAR_*</font> values (loaded via <font face="Courier">dotenv-cli</font>, the '
        'same tool the project’s <font face="Courier">start</font> scripts already use):', body_style))
    story.append(code_block(
        'npm run sonar&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# run the scan only, uploads results to the server\n'
        'npm run sonar:gate&nbsp;&nbsp;&nbsp;# check the gate result of the most recent scan\n'
        'npm run sonar:check&nbsp;&nbsp;# run both in sequence; exits non-zero if the gate fails\n'
        'npm run sonar:full&nbsp;&nbsp;&nbsp;&nbsp;# coverage:all + sonar:check — the whole CI pipeline, locally'))
    story.append(Paragraph(
        'In CI, defined in <font face="Courier">.github/workflows/pr-check.yml</font> ("PR Checks") as a job '
        'alongside build-check, CodeQL, and Dependency Review (Sections 1.3, 2.3) — all in the same file, all '
        'triggered by the same <font face="Courier">on: pull_request: branches: [main]</font> block, so one '
        'PR runs every check this repo has. The secrets come from GitHub Actions repository secrets instead '
        'of .env; dotenv-cli silently no-ops when no .env file is present, so the identical npm commands run '
        'unchanged in both places:', body_style))
    story.append(code_block(
        'sonarqube:\n'
        '&nbsp;&nbsp;permissions: {pull-requests: read}\n'
        '&nbsp;&nbsp;steps:\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- actions/checkout@v4&nbsp;&nbsp;(fetch-depth: 0)\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- actions/setup-node@v4\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- actions/setup-python@v5&nbsp;&nbsp;(3.11)\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- run: pip install -e ".[all]"&nbsp;&nbsp;&nbsp;# pytest + every agent extra\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- run: npm ci --ignore-scripts\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- run: npm run coverage:all&nbsp;&nbsp;&nbsp;# 4 services + frontend + Python\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- name: SonarQube Scan\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;env: {SONAR_TOKEN, SONAR_HOST_URL, SONAR_PROJECT_KEY}&nbsp;&nbsp;# from GitHub Secrets\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: npm run sonar\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- name: SonarQube Quality Gate check\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;env: {SONAR_TOKEN, SONAR_HOST_URL, SONAR_PROJECT_KEY}\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: npm run sonar:gate'))
    story.append(Paragraph(
        'This job is what actually blocks a PR merge on a failed gate (via a required status check), which '
        'running from a developer’s machine or IDE alone cannot enforce. The Python setup step exists '
        'because <font face="Courier">coverage:all</font> shells out to pytest for the meridian_agents suite '
        '— without it, that step fails with “No module named pytest”, tolerated only because it runs with '
        '<font face="Courier">continue-on-error: true</font>.', body_style))
    story.append(Paragraph(
        'As a complementary, faster feedback loop, the VS Code extension <b>SonarQube for IDE</b> '
        '(SonarLint) can connect to the same server (Connected Mode) so issues show up inline while typing, '
        'using the server’s quality profile. It’s local-only, though — it never uploads results or '
        'evaluates the gate; a supplement to the scan-and-gate flow, not a replacement for it.', body_style))

    story.append(Paragraph('Gate mechanics — scripts/sonar-quality-gate.sh', h2_style))
    story.append(Paragraph('Analysis and gate evaluation are asynchronous, in two stages:', body_style))
    story.append(bullets([
        '<b>Scan (client-side):</b> sonar-scanner analyzes source locally, writes an intermediate report '
        'under <font face="Courier">.scannerwork/</font>, and uploads it via '
        '<font face="Courier">POST /api/ce/submit</font>. The server responds with a task receipt written to '
        '<font face="Courier">.scannerwork/report-task.txt</font> (ceTaskId, dashboardUrl).',
        '<b>Processing (server-side):</b> the upload is queued as a Compute Engine (CE) background task, '
        'which ingests the report, computes final measures, matches issues against the active quality '
        'profile, and evaluates the Quality Gate — all before the task reports SUCCESS.',
    ]))
    story.append(Paragraph('The gate script then:', body_style))
    story.append(bullets([
        'Reads <font face="Courier">ceTaskId</font> and polls <font face="Courier">GET /api/ce/task?id=...</font> '
        'every 10s (up to 30 attempts) until it reaches SUCCESS/FAILED/CANCELED — failing immediately if it '
        'never reaches SUCCESS, since the gate would otherwise reflect a stale prior analysis.',
        'Queries <font face="Courier">GET /api/qualitygates/project_status?projectKey=...</font> — this '
        'reads an already-computed result, it does not trigger new evaluation.',
        'Prints the overall status (SonarQube’s API uses <font face="Courier">ERROR</font> for a failed '
        'gate, not <font face="Courier">FAIL</font>) and, on failure, each failing condition’s actual value '
        'and threshold, then exits non-zero — what lets CI block the PR on this step.',
    ]))
    story.append(Paragraph('Example: a real gate failure observed on this project', h2_style))
    story.append(Paragraph(
        'Default gate conditions evaluate only <i>new</i> code (lines changed since the gate’s baseline — '
        'the “leak period”), not the whole codebase. This example is from a scan after a large batch of test '
        'files was added in one session, so “new code” spans everything since that baseline:', body_style))
    story.append(metrics_table(
        [['Metric', 'Actual', 'Required', 'Meaning'],
         ['new_coverage', '19.0%', '≥ 100%', 'Coverage on lines changed since baseline'],
         ['new_duplicated_lines_density', '5.27%', '≤ 3%', 'Too much duplicated new code'],
         ['new_security_hotspots_reviewed', '0.0%', '= 100%', 'Hotspot(s) not yet manually reviewed'],
         ['new_violations', '73', '= 0', 'New bugs / vulnerabilities / code smells introduced']],
        col_widths=[45 * mm, 20 * mm, 22 * mm, 81 * mm]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        'A failing gate does not mean the scan failed — the scan always succeeds if it can reach the server '
        'and upload results. Pass/fail is purely the gate’s evaluation of those results against its '
        'configured thresholds.', body_style))
    story.append(note(
        'The new_coverage threshold shown here (≥100%) is unusually strict versus SonarQube’s default '
        '“Sonar way” gate (typically ≥80%) — worth reviewing in the SonarQube UI if the standard threshold '
        'was actually intended. The other three conditions are independent of coverage entirely.'))

    story.append(Paragraph('Code coverage — how it feeds the gate', h2_style))
    story.append(Paragraph(
        'Coverage is a runtime metric, not a static-analysis one: as tests execute, a coverage tool records '
        'which lines actually ran. It measures only whether a line <i>executed</i>, not whether the test '
        'asserted anything meaningful about it — necessary but not sufficient for a trustworthy suite, while '
        'low coverage reliably signals completely unverified code. The gate’s coverage condition is scoped '
        'to new/changed code specifically so it acts as a forcing function while the author still has full '
        'context, not months later during a bug report.', body_style))
    story.append(Paragraph(
        'SonarQube doesn’t execute tests itself — it’s purely a consumer of reports the project’s own test '
        'runners produce, declared in sonar-project.properties: '
        '<font face="Courier">sonar.javascript.lcov.reportPaths</font> (one lcov.info per JS/TS/Vue codebase) '
        'and <font face="Courier">sonar.python.coverage.reportPaths</font> (one Cobertura XML for '
        'meridian_agents). During analysis the scanner cross-references each report’s line numbers against '
        'the files it parsed and derives per-file, per-directory, whole-project, and git-diff-scoped '
        '(<font face="Courier">new_coverage</font>) percentages — the last of which the gate actually '
        'evaluates.', body_style))
    story.append(metrics_table(
        [['Codebase', 'Runner', 'Command', 'Report'],
         ['auth-service, blog-service,\nmedia-service, api-gateway',
          'Jest (ts-jest)',
          'npm run test:cov:&lt;service&gt;\n(jest --coverage)',
          'coverage/lcov.info'],
         ['frontend', 'Vitest (v8 provider)', 'npm run test:cov:frontend\n(vitest run --coverage)', 'coverage/lcov.info'],
         ['meridian_agents (Python)', 'pytest + pytest-cov', 'npm run coverage:python\n(--cov-report=xml)',
          'coverage-python.xml']],
        col_widths=[42 * mm, 30 * mm, 50 * mm, 46 * mm]))
    story.append(Spacer(1, 8))
    story.append(note(
        'Coverage reports must already exist on disk before npm run sonar runs — the scan is a point-in-time '
        'read. Stale or missing reports silently produce 0% or a previous run’s numbers, not an error. '
        '<font face="Courier">npm run coverage:all</font> regenerates every report in one command; '
        '<font face="Courier">npm run sonar:full</font> chains coverage:all + the scan + the gate.'))

    # ── 1.3 CodeQL ────────────────────────────────────────────────────────
    story.append(Paragraph('1.3 CodeQL', h2_style))

    story.append(Paragraph(
        '<b>What it is &amp; what it’s used for.</b> GitHub’s own SAST engine: it treats source as a '
        'queryable relational database and performs real interprocedural <b>dataflow / taint-tracking</b> '
        'analysis — tracing how a specific piece of untrusted input actually flows into a dangerous sink (a '
        'SQL query, a shell exec, an HTML response), rather than matching syntactic patterns. This is what '
        'makes it materially stronger than pattern-based tools at finding real, exploitable injection / XSS '
        '/ SSRF / insecure-deserialization vulnerabilities with fewer false positives — at the cost of being '
        'narrower in scope than SonarQube (Section 1.2): no code smells, no duplication, no coverage gate.',
        body_style))

    story.append(Paragraph(
        '<b>Configuring on GitHub.</b> Runs as native <b>GitHub Code Scanning</b> — free for public '
        'repositories (this repo is public), with zero additional infrastructure: no server to host, no '
        'secret to manage, unlike SonarQube’s self-hosted setup. Results surface on the repo’s <b>Security '
        'tab → Code scanning alerts</b>. The workflow job needs a <font face="Courier">permissions: '
        '{security-events: write}</font> block to upload results there — everything else about enabling it '
        'lives in the workflow file itself, no repo Settings toggle required.', body_style))

    story.append(Paragraph(
        '<b>Configuring in code.</b> Two files:', body_style))
    story.append(bullets([
        '<font face="Courier">.github/codeql/codeql-config.yml</font> — enables the '
        '<font face="Courier">security-extended</font> query pack (broader than the default query set) and '
        'excludes node_modules/, dist/, coverage/, uploads/, and DB/PDF files from analysis, deliberately '
        'mirroring SonarQube’s <font face="Courier">sonar.exclusions</font> so both tools scan the same real '
        'source.',
        '<font face="Courier">.github/workflows/pr-check.yml</font> — the <font face="Courier">codeql</font> '
        'and <font face="Courier">codeql-gate</font> jobs (below).',
    ]))
    story.append(note(
        'CodeQL analysis initially lived in its own .github/workflows/codeql.yml — GitHub’s own default '
        'convention (the “Set up code scanning” button always generates a standalone file). It was folded '
        'into pr-check.yml instead for one concrete reason: the gate job needs to know when analysis has '
        'finished, and jobs can only declare a native needs: dependency on a job within the same workflow '
        'file — not across two independent workflow runs. Keeping it separate would have meant polling '
        'GitHub’s Checks API from the gate job just to work around that file boundary. A job’s permissions: '
        'block is still scoped per-job regardless of which file it lives in, so this didn’t widen any other '
        'job’s permissions — the one real trade-off is losing CodeQL’s independent trigger set (it also ran '
        'on every push to main and a weekly schedule as a standalone workflow); in one shared file, every '
        'job uses the same pull_request-only trigger.'))

    story.append(Paragraph(
        '<b>How it’s done here.</b> The single <font face="Courier">on: pull_request: branches: [main]</font> '
        'block at the top of pr-check.yml governs every job in the file — CodeQL runs whenever a PR targets '
        'main, exactly like build-check and the SonarQube scan:', body_style))
    story.append(code_block(
        'codeql:\n'
        '&nbsp;&nbsp;permissions: {security-events: write, actions: read, contents: read}\n'
        '&nbsp;&nbsp;strategy:\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;matrix:\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;language: [javascript-typescript, python]\n'
        '&nbsp;&nbsp;steps:\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- actions/checkout@v4\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- actions/setup-node@v4&nbsp;&nbsp;(js/ts leg only)\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- run: npm ci --ignore-scripts&nbsp;&nbsp;(js/ts leg only)\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- github/codeql-action/init@v3\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;with: {languages: matrix.language,\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;config-file: .github/codeql/codeql-config.yml}\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- github/codeql-action/autobuild@v3\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- github/codeql-action/analyze@v3\n\n'
        'codeql-gate:\n'
        '&nbsp;&nbsp;needs: codeql&nbsp;&nbsp;&nbsp;&nbsp;# waits for both matrix legs to finish\n'
        '&nbsp;&nbsp;permissions: {security-events: read, contents: read}\n'
        '&nbsp;&nbsp;steps:\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- actions/checkout@v4\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- run: npm run codeql:gate'))
    story.append(Paragraph(
        'The matrix runs two independent legs in parallel, one per language. The javascript-typescript leg '
        'installs dependencies first purely to help CodeQL resolve TS/JS imports more precisely; neither '
        'language actually needs a compiled build to be analyzed, so <font face="Courier">autobuild</font> '
        'is effectively a no-op for both.', body_style))

    story.append(Paragraph('Custom severity gate — scripts/codeql-quality-gate.sh', h2_style))
    story.append(Paragraph(
        '<font face="Courier">codeql-action/analyze</font> always exits successfully regardless of what it '
        'finds — GitHub Code Scanning has no built-in “fail the build on severity count” gate the way '
        'SonarQube’s Quality Gate does natively. This script closes that gap, mirroring '
        'sonar-quality-gate.sh’s approach rather than reusing SonarQube’s exact thresholds:', body_style))
    story.append(bullets([
        '<b>FAIL</b> if any open alert has security severity <b>CRITICAL</b>.',
        '<b>FAIL</b> if more than <b>2</b> open alerts have security severity <b>HIGH</b>.',
        'otherwise <b>PASS</b>.',
    ]))
    story.append(Paragraph(
        'Because <font face="Courier">codeql-gate</font> declares <font face="Courier">needs: codeql</font>, '
        'it only starts once every matrix leg has completed — no polling required to know analysis is done. '
        'The one remaining timing wrinkle: a finished analyze step means the SARIF upload was accepted, not '
        'that GitHub has finished turning it into queryable alerts yet, so the script pauses briefly before '
        'querying <font face="Courier">GET /repos/{owner}/{repo}/code-scanning/alerts?state=open</font> '
        '(paginated), filtering each alert’s <font face="Courier">rule.security_severity_level</font>.',
        body_style))
    story.append(note(
        'An empty result from that query is genuinely ambiguous — zero open alerts, or alerts not finished '
        'processing yet — so the script uses a fixed pause rather than retrying-until-nonempty, which would '
        'silently treat “not ready yet” as “clean”.'))

    # ══════════════════════════════════════════════════════════════════════
    # 2. SCA — Software Composition Analysis
    # ══════════════════════════════════════════════════════════════════════
    story.append(Paragraph('2. SCA — Software Composition Analysis', h1_style))
    story.append(Paragraph('2.1 What is SCA?', h2_style))
    story.append(Paragraph(
        'SCA inspects the <b>third-party packages</b> a project depends on — not its own source — against '
        'databases of publicly known vulnerabilities (CVEs) and license issues. Neither SonarQube Community '
        'Edition nor CodeQL do this (Section 1); a vulnerable dependency sitting in node_modules or a Python '
        'virtualenv is completely invisible to both, since both only parse first-party source. SCA closes '
        'that gap by matching exact package+version pairs already recorded in the project’s '
        '<b>dependency graph</b> (derived from lockfiles/manifests) against an advisory database — '
        'fundamentally a <i>lookup</i>, not an analysis, so it needs no understanding of how the code that '
        'uses the package actually works.', body_style))
    story.append(Paragraph('Two tools cover this here, at different scopes:', body_style))
    story.append(bullets([
        '<b>Dependabot</b> — continuous, whole-dependency-tree coverage, independent of any PR.',
        '<b>Dependency Review</b> — scoped to exactly what a single PR’s diff introduces, with an inline gate.',
    ]))

    # ── 2.2 Dependabot ────────────────────────────────────────────────────
    story.append(Paragraph('2.2 Dependabot', h2_style))
    story.append(Paragraph(
        '<b>What it is &amp; what it’s used for.</b> “Dependabot” is a brand name covering two genuinely '
        'distinct GitHub features, easy to conflate:', body_style))
    story.append(bullets([
        '<b>Dependabot version updates</b> — opens scheduled PRs bumping dependency versions, vulnerable or '
        'not. This is <i>not</i> a security tool by itself; it bumps everything on a schedule.',
        '<b>Dependabot alerts</b> — the actual SCA tool. Event-driven, not scheduled: it re-checks whenever '
        'the dependency graph changes (a manifest/lockfile push) <i>or</i> whenever a new advisory is '
        'published for a package already in use — meaning an alert can appear on a dependency nobody has '
        'touched in months, the moment a CVE for it becomes public. Results surface on the repo’s '
        '<b>Security tab → Dependabot alerts</b>, entirely independent of PR activity.',
    ]))

    story.append(Paragraph(
        '<b>Configuring on GitHub.</b> Version updates need no separate toggle — committing '
        '<font face="Courier">.github/dependabot.yml</font> is what enables them. Alerts are a repo Settings '
        'toggle instead (<b>Settings → Code security and analysis → Dependabot alerts</b>), unrelated to that '
        'file — confirmed enabled on this repo (the API’s '
        '<font face="Courier">/vulnerability-alerts</font> endpoint returns 204, and 0 alerts are currently '
        'open).', body_style))

    story.append(Paragraph(
        '<b>Configuring in code.</b> <font face="Courier">.github/dependabot.yml</font> — one entry per '
        'package ecosystem:', body_style))
    story.append(code_block(
        'updates:\n'
        '&nbsp;&nbsp;- package-ecosystem: npm\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;directory: /\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;schedule: {interval: weekly, day: monday, time: "06:00"}\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;open-pull-requests-limit: 10\n'
        '&nbsp;&nbsp;- package-ecosystem: pip\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;directory: /\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;schedule: {interval: weekly, day: monday, time: "06:00"}\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;open-pull-requests-limit: 5'))
    story.append(note(
        'Deliberately no groups: — each bump becomes its own individual PR so the maintenance agent can '
        'parse a plain “Bump X from A to B” title and decide whether to merge or close it, rather than '
        'having to unpack a batched multi-package PR.'))

    story.append(Paragraph(
        '<b>How it’s done here.</b> One npm entry and one pip entry, both rooted at <font face="Courier">'
        '/</font> — a direct consequence of this repo’s single-root-package.json consolidation (previously '
        'five separate npm entries, one per service, before that restructuring). Weekly on Mondays, capped '
        'at 10 open npm PRs / 5 open pip PRs at a time. Alerts require nothing further once the Settings '
        'toggle above is on — they just start appearing on the Security tab automatically as new advisories '
        'are published or the graph changes.', body_style))

    # ── 2.3 Dependency Review Action ──────────────────────────────────────
    story.append(Paragraph('2.3 Dependency Review Action', h2_style))
    story.append(Paragraph(
        '<b>What it is &amp; what it’s used for.</b> A GitHub Action that runs the same SCA lookup as '
        'Dependabot alerts (same underlying Advisory Database) but scoped to exactly what a single PR’s diff '
        'changes in the dependency manifests — and, unlike Dependabot alerts, with a <b>native inline gate</b>: '
        'it can fail the check itself, rather than only posting an informational alert to the Security tab. '
        'It complements Dependabot alerts rather than replacing them: Dependabot alerts cover the whole '
        'existing tree continuously; this action only ever sees what a given PR is about to add.', body_style))

    story.append(Paragraph(
        '<b>Configuring on GitHub.</b> Requires <b>Dependency graph</b> enabled (<b>Settings → Code security '
        'and analysis → Dependency graph</b>) — a real gap hit while wiring this up on this repo: the first '
        'run failed outright with “Dependency review is not supported on this repository. Please ensure that '
        'Dependency graph is enabled”, even though Dependabot alerts (2.2) were already active. Turning the '
        'toggle on and re-running the same job with no code changes fixed it. No other GitHub-side setup is '
        'needed — no secret, no additional permission beyond the job’s own '
        '<font face="Courier">contents: read</font>.', body_style))

    story.append(Paragraph(
        '<b>Configuring in code.</b> One job in <font face="Courier">.github/workflows/pr-check.yml</font>:',
        body_style))
    story.append(code_block(
        'dependency-review:\n'
        '&nbsp;&nbsp;permissions: {contents: read}\n'
        '&nbsp;&nbsp;steps:\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- actions/checkout@v4\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- actions/dependency-review-action@v4\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;with: {fail-on-severity: high}'))
    story.append(Paragraph(
        '<b>How it’s done here.</b> <font face="Courier">fail-on-severity: high</font> blocks the PR if the '
        'diff introduces anything rated high <i>or</i> critical — a plain binary cutoff, unlike the '
        '“0 critical, ≤2 high” <i>count</i>-based tolerance used for the CodeQL and SonarQube gates (Section '
        '1). That count-based tolerance exists because those gates evaluate the whole existing codebase, '
        'where some accumulated, already-triaged risk is tolerated; a single PR realistically introduces at '
        'most one or two new dependencies at a time, so there’s no equivalent “accumulated” risk to tolerate '
        'here — any new high/critical dependency is worth blocking outright. First real run on this repo '
        'passed clean (no vulnerable or license-problematic new dependencies).', body_style))

    # ══════════════════════════════════════════════════════════════════════
    # 3. Summary
    # ══════════════════════════════════════════════════════════════════════
    story.append(Paragraph('3. Summary', h1_style))
    story.append(metrics_table(
        [['Tool', 'Category', 'Scope', 'Trigger', 'Blocks merge?'],
         ['SonarQube', 'SAST', 'Whole repo\n(gate: new/changed code)', 'pull_request\n(pr-check.yml)',
          'Yes — sonar:gate'],
         ['CodeQL', 'SAST', 'Whole repo\n(JS/TS + Python matrix)', 'pull_request\n(pr-check.yml)',
          'Yes — custom codeql-gate'],
         ['Dependabot alerts', 'SCA', 'Whole dependency tree,\ncontinuous', 'Event-driven\n(new advisory / graph change)',
          'No — informational,\nSecurity tab only'],
         ['Dependabot\nversion updates', '(not security)', 'Whole dependency tree', 'Weekly schedule',
          'N/A — opens PRs,\ndoesn’t gate'],
         ['Dependency Review', 'SCA', 'This PR’s manifest\ndiff only', 'pull_request\n(pr-check.yml)',
          'Yes — fail-on-severity: high']],
        col_widths=[32 * mm, 22 * mm, 38 * mm, 38 * mm, 38 * mm]))

    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceBefore=14, spaceAfter=8))
    story.append(Paragraph(
        '<i>Generated for the Meridian (myblogs) project.</i>',
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=GRAY, alignment=TA_CENTER)))

    doc.build(story)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    build()
