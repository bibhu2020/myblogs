"""
Meridian — SonarQube Integration doc generator.
Produces _docs/codescan.pdf: what SonarQube is, how this repo wires it up
(scan + gate, locally and in CI), and how code coverage feeds into it.
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
    out_path = os.path.join(os.path.dirname(__file__), '..', '_docs', 'codescan.pdf')
    doc = SimpleDocTemplate(out_path, pagesize=A4,
                             topMargin=20 * mm, bottomMargin=18 * mm,
                             leftMargin=20 * mm, rightMargin=20 * mm)
    story = []

    story.append(Paragraph('SonarQube Integration', title_style))
    story.append(Paragraph('Static code analysis setup for the Meridian (myblogs) project', subtitle_style))

    # ── 1. What is SonarQube? ────────────────────────────────────────────────
    story.append(Paragraph('1. What is SonarQube?', h1_style))
    story.append(Paragraph(
        'SonarQube is a self-hosted static analysis platform that scans source code and reports on code '
        'quality and security. It does not run the application or execute tests itself — it parses source '
        '(and ingests test coverage reports you provide) and evaluates the result against a configurable '
        'set of rules and thresholds called a <b>Quality Gate</b>.', body_style))
    story.append(Paragraph('It checks four categories of issues:', body_style))
    story.append(bullets([
        '<b>Bugs</b> — code likely to behave incorrectly or crash (Reliability).',
        '<b>Vulnerabilities</b> — exploitable security flaws such as injection, XSS, hardcoded secrets, '
        'insecure crypto (Security). Found via static dataflow/taint analysis, not just pattern matching.',
        '<b>Code Smells</b> — maintainability issues: dead code, high complexity, poor structure.',
        '<b>Security Hotspots</b> — security-sensitive code (crypto, cookies, regex, deserialization) that '
        'needs a human to confirm whether it’s actually exploitable in context, rather than being '
        'flagged outright as a vulnerability.',
    ]))
    story.append(Paragraph(
        'Alongside issues, it also computes non-issue metrics that factor into the gate: <b>test coverage</b> '
        '(from lcov/Cobertura reports you feed in) and <b>duplicated code density</b>.', body_style))
    story.append(note(
        'Note: SonarQube Community Edition (what this project uses) does not scan third-party dependencies '
        'for known CVEs (no Software Composition Analysis) — it only analyzes your own source code.'))

    # ── 2. How This Repo Integrates SonarQube ────────────────────────────────
    story.append(Paragraph('2. How This Repo Integrates SonarQube', h1_style))
    story.append(Paragraph(
        'The goal of this setup was to have exactly <b>one</b> way of invoking a scan and one way of '
        'checking the gate, used identically by a developer’s machine, the IDE, and CI — rather than '
        'CI running different logic than what a developer can reproduce locally.', body_style))

    story.append(Paragraph('2.1 Project-level scan configuration — sonar-project.properties', h2_style))
    story.append(Paragraph('Lives at the repo root and defines what gets scanned, independent of secrets:', body_style))
    story.append(bullets([
        '<font face="Courier">sonar.sources</font> — scan root (<font face="Courier">.</font>)',
        '<font face="Courier">sonar.exclusions</font> — keeps node_modules/, dist/, *.db, uploads/, '
        'coverage/, .github/ out of analysis',
        '<font face="Courier">sonar.javascript.file.suffixes</font> / '
        '<font face="Courier">sonar.typescript.file.suffixes</font> — includes .vue files as JS/TS-analyzable',
        '<font face="Courier">sonar.javascript.lcov.reportPaths</font> — points at each service’s '
        '<font face="Courier">coverage/lcov.info</font> so test coverage feeds into the gate',
        '<font face="Courier">sonar.python.coverage.reportPaths</font> — points at '
        '<font face="Courier">coverage-python.xml</font> so the meridian_agents test suite’s coverage '
        'feeds into the gate too (see Section 6)',
    ]))
    story.append(note(
        'Note: sonar.projectKey=${SONAR_PROJECT_KEY} in this file is a literal placeholder — SonarScanner '
        'only substitutes environment variables written as ${env.VAR_NAME}. The real project key is supplied '
        'explicitly on the command line instead (see 2.3), so this placeholder has no functional effect.'))

    story.append(Paragraph('2.2 Secrets — .env (local) / GitHub Secrets (CI)', h2_style))
    story.append(Paragraph('Three values are kept out of the properties file and out of git:', body_style))
    story.append(code_block(
        'SONAR_HOST_URL=https://sonarqube.kube8t.com\n'
        'SONAR_TOKEN=sqp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n'
        'SONAR_PROJECT_KEY=base-kiwi-sauce'))
    story.append(Paragraph(
        'Locally these live in <font face="Courier">.env</font> (gitignored) and are loaded by '
        '<font face="Courier">dotenv-cli</font>, the same tool already used by the project’s '
        '<font face="Courier">start</font> / <font face="Courier">start:backend</font> scripts. In CI they '
        'come from GitHub Actions repository secrets instead — dotenv-cli silently no-ops when no .env file '
        'is present, so the same npm command works unchanged in both places.', body_style))

    story.append(Paragraph('2.3 npm scripts — package.json', h2_style))
    story.append(Paragraph(
        'The scanner itself is the <font face="Courier">@sonar/scan</font> npm package (installed as a root '
        'devDependency), exposing a <font face="Courier">sonar-scanner</font> binary — no separate Java '
        'install or Docker image required.', body_style))
    story.append(code_block(
        '"scripts": {\n'
        '&nbsp;&nbsp;"sonar":&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"dotenv -e .env -- sh -c \'sonar-scanner \\\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;-Dsonar.projectKey="$SONAR_PROJECT_KEY" \\\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;-Dsonar.scanner.socketTimeout=300 \\\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;-Dsonar.scanner.responseTimeout=300\'",\n'
        '&nbsp;&nbsp;"sonar:gate":&nbsp;&nbsp;"dotenv -e .env -- sh scripts/sonar-quality-gate.sh",\n'
        '&nbsp;&nbsp;"sonar:check":&nbsp;&nbsp;"npm run sonar && npm run sonar:gate"\n'
        '}'))
    story.append(Paragraph(
        'The scan command is wrapped in an inner <font face="Courier">sh -c \'...\'</font> deliberately: if '
        '<font face="Courier">$SONAR_PROJECT_KEY</font> were expanded directly in the script string, npm’s '
        'own shell would expand it before dotenv-cli has injected the variable from .env, resulting in an '
        'empty value. The inner shell defers expansion until after the environment is populated.', body_style))

    story.append(Paragraph('2.4 Quality Gate check script — scripts/sonar-quality-gate.sh', h2_style))
    story.append(Paragraph(
        'A standalone shell script (not inlined in package.json or the workflow file) so both local runs '
        'and CI call the exact same logic. See Section 5 for what it does.', body_style))

    story.append(Paragraph('2.5 IDE feedback — SonarQube for IDE (SonarLint)', h2_style))
    story.append(Paragraph(
        'As a complementary, faster feedback loop, the VS Code extension <b>SonarQube for IDE</b> can be '
        'connected to the same server (Connected Mode) so a developer sees issues inline while typing, using '
        'the same quality profile as the server. This is local-only analysis, though — it does not upload '
        'results or evaluate the Quality Gate. It is a supplement to the scan-and-gate flow, not a replacement '
        'for it.', body_style))

    # ── 3. Triggering a Scan Locally ─────────────────────────────────────────
    story.append(Paragraph('3. Triggering a Scan Locally', h1_style))
    story.append(Paragraph('From the repo root, with .env populated with real SONAR_* values:', body_style))
    story.append(code_block(
        'npm run sonar&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# run the scan only, uploads results to the server\n'
        'npm run sonar:gate&nbsp;&nbsp;&nbsp;# check the gate result of the most recent scan\n'
        'npm run sonar:check&nbsp;&nbsp;# run both in sequence; exits non-zero if the gate fails'))
    story.append(Paragraph(
        'Test coverage should be generated before scanning if the coverage condition matters — either per '
        'service (<font face="Courier">npm run test:cov --prefix &lt;service&gt;</font>, plus '
        '<font face="Courier">npm run coverage:python</font> for meridian_agents) or all at once via '
        '<font face="Courier">npm run coverage:all</font> — since the properties file only picks up coverage '
        'that already exists on disk at scan time. <font face="Courier">npm run sonar:full</font> chains '
        '<font face="Courier">coverage:all</font> and <font face="Courier">sonar:check</font> into a single '
        'command that reproduces the full CI pipeline locally.', body_style))

    # ── 4. Triggering from the CI Pipeline ───────────────────────────────────
    story.append(Paragraph('4. Triggering from the CI Pipeline', h1_style))
    story.append(Paragraph(
        'Defined in <font face="Courier">.github/workflows/sonarqube.yml</font>, as a job alongside the '
        'existing build-check job that runs on every pull request into main. As of this document, the job '
        'is present but <b>commented out</b> — it does not currently run or gate PRs.', body_style))
    story.append(code_block(
        'sonarqube:\n'
        '&nbsp;&nbsp;steps:\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- actions/checkout@v4&nbsp;&nbsp;(fetch-depth: 0)\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- actions/setup-node@v4\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- run: npm ci --ignore-scripts\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- run: npm run coverage:all&nbsp;&nbsp;&nbsp;# 5 services + Python\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- name: SonarQube Scan\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;env: {SONAR_TOKEN, SONAR_HOST_URL, SONAR_PROJECT_KEY}&nbsp;&nbsp;# from GitHub Secrets\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: npm run sonar\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;- name: SonarQube Quality Gate check\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;env: {SONAR_TOKEN, SONAR_HOST_URL, SONAR_PROJECT_KEY}\n'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;run: npm run sonar:gate'))
    story.append(Paragraph(
        'The pipeline calls the identical npm scripts used locally — nothing CI-specific is duplicated. To '
        'enable it: uncomment the job, and add SONAR_TOKEN, SONAR_HOST_URL, and SONAR_PROJECT_KEY as '
        'repository secrets in GitHub. Once enabled, this becomes the mechanism that can actually block a PR '
        'merge on a failed gate (via a required status check), which running from a developer’s machine '
        'or the IDE alone cannot enforce.', body_style))

    # ── 5. How the Quality Gate Check Works ──────────────────────────────────
    story.append(Paragraph('5. How the Quality Gate Check Works', h1_style))
    story.append(Paragraph('Analysis and gate evaluation are asynchronous and happen in two stages:', body_style))
    story.append(bullets([
        '<b>Scan (client-side):</b> sonar-scanner analyzes the source locally and writes an intermediate '
        'report (protobuf files) under <font face="Courier">.scannerwork/</font>. This is zipped and '
        'uploaded to the server via <font face="Courier">POST /api/ce/submit</font>. The server responds '
        'with a task receipt, written locally to <font face="Courier">.scannerwork/report-task.txt</font> '
        '(contains ceTaskId, dashboardUrl).',
        '<b>Processing (server-side):</b> the upload is queued as a Compute Engine (CE) background task. It '
        'ingests the report, computes final measures, matches issues against the active quality profile, and '
        'evaluates the Quality Gate conditions — all before the task reports as SUCCESS.',
    ]))
    story.append(Paragraph('scripts/sonar-quality-gate.sh then does the following:', body_style))
    story.append(bullets([
        'Reads <font face="Courier">ceTaskId</font> from report-task.txt.',
        'Polls <font face="Courier">GET /api/ce/task?id=...</font> every 10 seconds (up to 30 attempts) '
        'until the task reaches SUCCESS, FAILED, or CANCELED.',
        'If the task did not reach SUCCESS, fails immediately — the gate result would otherwise reflect a '
        'stale prior analysis, not this run.',
        'Queries <font face="Courier">GET /api/qualitygates/project_status?projectKey=...</font>, which '
        'returns the gate result already computed during processing (this call reads a result, it does not '
        'trigger new evaluation).',
        'Prints the overall status (OK or ERROR — SonarQube’s API uses ERROR for a failed gate, not '
        'FAIL) and, on failure, the specific failing conditions with their actual value and threshold.',
        'Exits non-zero on anything other than OK, which is what allows CI to fail the build / block the PR '
        'on this step.',
    ]))

    story.append(Paragraph('Example: a real gate failure observed on this project', h2_style))
    story.append(Paragraph(
        'Default gate conditions evaluate only <i>new</i> code (i.e. lines changed since the gate’s '
        'baseline — the “leak period”, currently the previous version tag), not the whole codebase. '
        'This example is from a scan run after a large batch of test files was added in a single session, '
        'so “new code” spans everything changed since that baseline, not just the most recent commit:',
        body_style))
    story.append(metrics_table(
        [['Metric', 'Actual', 'Required', 'Meaning'],
         ['new_coverage', '19.0%', '≥ 100%', 'Coverage on lines changed since baseline'],
         ['new_duplicated_lines_density', '5.27%', '≤ 3%', 'Too much duplicated new code'],
         ['new_security_hotspots_reviewed', '0.0%', '= 100%', 'Hotspot(s) not yet manually reviewed'],
         ['new_violations', '73', '= 0', 'New bugs / vulnerabilities / code smells introduced']],
        col_widths=[45 * mm, 20 * mm, 22 * mm, 81 * mm]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        'A failing gate does not mean the scan itself failed — the scan always succeeds if it can reach the '
        'server and upload results. “Passing” or “failing” is purely the gate’s '
        'evaluation of those results against its configured thresholds.', body_style))
    story.append(note(
        'Note: the new_coverage threshold shown here (≥100%) is unusually strict compared to SonarQube’s '
        'default “Sonar way” gate (typically ≥80%). It reflects this project’s currently '
        'configured gate, which is worth reviewing in the SonarQube UI if the intent was the standard '
        'threshold. The other three conditions (violations, duplication, hotspot review) are independent of '
        'test coverage entirely — see Section 6 for coverage specifically.'))

    # ── 6. Code Coverage ──────────────────────────────────────────────────────
    story.append(Paragraph('6. Code Coverage', h1_style))

    story.append(Paragraph('6.1 What is code coverage?', h2_style))
    story.append(Paragraph(
        'Code coverage is a runtime metric, not a static-analysis one: as the test suite executes, a '
        'coverage tool instruments the code and records which lines (and optionally branches/functions) '
        'actually ran. The result is a percentage — e.g. “83% line coverage” means 83% of '
        'executable statements in the measured files were hit by at least one test.', body_style))
    story.append(Paragraph(
        'It measures only whether a line <i>executed</i>, not whether the test that executed it asserted '
        'anything meaningful. A test that calls a function and checks nothing about its result still counts '
        'as “covering” that function. High coverage is necessary but not sufficient for a '
        'trustworthy test suite; low coverage, on the other hand, is a reliable signal that some code paths '
        'are completely unverified.', body_style))

    story.append(Paragraph('6.2 Why it matters here', h2_style))
    story.append(bullets([
        'Untested paths are exactly where regressions hide silently — a suite that passes 100% of its own '
        'tests can still miss a broken function nobody wrote a test for.',
        'The Quality Gate’s coverage condition is scoped to new/changed code specifically so it acts as '
        'a forcing function at the cheapest possible point: while the author still has full context on what '
        'the code is supposed to do, not months later during a bug report.',
        'It is a lagging indicator to monitor, not a target to game — this project’s approach was to add '
        'real behavioral tests (including several that caught genuine production bugs along the way, e.g. a '
        'dependency version mismatch in api-gateway and a broken clipboard reference in BlogPost.vue) rather '
        'than shallow tests written purely to move the coverage number.',
    ]))

    story.append(Paragraph('6.3 How coverage feeds into SonarQube', h2_style))
    story.append(Paragraph(
        'SonarQube does not execute tests or instrument code itself — it is purely a consumer of coverage '
        'reports produced by whatever test runner the project already uses. The report format is '
        'language-specific and declared in sonar-project.properties (Section 2.1):', body_style))
    story.append(bullets([
        'JS / TS / Vue → <font face="Courier">sonar.javascript.lcov.reportPaths</font> — one '
        '<font face="Courier">lcov.info</font> file per service, comma-separated (LCOV format).',
        'Python → <font face="Courier">sonar.python.coverage.reportPaths</font> — a single '
        '<font face="Courier">coverage-python.xml</font> (Cobertura XML format).',
    ]))
    story.append(Paragraph(
        'Both formats are, at their core, a list of covered/uncovered line numbers per source file — a '
        'standard interchange format that most coverage tools across ecosystems know how to both emit and '
        'consume. During analysis, the scanner cross-references each report’s line numbers against the '
        'files it just parsed, and derives per-file, per-directory, whole-project, and git-diff-scoped '
        '(<font face="Courier">new_coverage</font>) percentages — the last of which is what the Quality Gate '
        'actually evaluates.', body_style))
    story.append(note(
        'Coverage reports must already exist on disk before npm run sonar runs — the scan is a point-in-time '
        'read of whatever coverage/lcov.info and coverage-python.xml happen to contain at that moment. Stale '
        'or missing reports silently produce 0% or a previous run’s numbers, not an error.'))

    story.append(Paragraph('6.4 How it’s configured in this repo', h2_style))
    story.append(Paragraph(
        'Coverage is generated per codebase using each ecosystem’s native tooling, then every report '
        'path is declared centrally in sonar-project.properties so the scanner picks all of them up in one '
        'pass:', body_style))
    story.append(metrics_table(
        [['Codebase', 'Runner', 'Command', 'Report'],
         ['auth-service, blog-service,\nmedia-service, api-gateway',
          'Jest (ts-jest)',
          'npm run test:cov\n(jest --coverage)',
          'coverage/lcov.info'],
         ['frontend', 'Vitest (v8 provider)', 'npm run test:cov\n(vitest run --coverage)', 'coverage/lcov.info'],
         ['meridian_agents (Python)', 'pytest + pytest-cov', 'npm run coverage:python\n(--cov-report=xml)',
          'coverage-python.xml']],
        col_widths=[42 * mm, 30 * mm, 50 * mm, 46 * mm]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        'Each Jest config sets <font face="Courier">collectCoverageFrom</font> to include all .ts/.js source '
        'while excluding <font face="Courier">main.ts</font> and <font face="Courier">app.module.ts</font> '
        '(framework bootstrap files with no meaningful logic to test). Vitest’s config similarly '
        'excludes <font face="Courier">main.js</font>, <font face="Courier">router/**</font>, '
        '<font face="Courier">sw.js</font>, and the placeholder <font face="Courier">HelloWorld.vue</font> '
        'component. On the Python side, <font face="Courier">pyproject.toml</font>’s '
        '<font face="Courier">[tool.coverage.run]</font> scopes collection to '
        '<font face="Courier">source = ["meridian_agents"]</font> and omits '
        '<font face="Courier">meridian_agents/tests/*</font> itself from being counted as coverable code.',
        body_style))
    story.append(Paragraph(
        '<font face="Courier">npm run coverage:all</font> chains all six coverage commands (five services + '
        'Python) in sequence, so a single command regenerates every report SonarQube needs before a scan. '
        '<font face="Courier">npm run sonar:full</font> then runs '
        '<font face="Courier">coverage:all</font>, the scan, and the gate check in order — the one command '
        'that reproduces the full CI pipeline end-to-end from a clean checkout.', body_style))

    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceBefore=14, spaceAfter=8))
    story.append(Paragraph(
        '<i>Generated for the Meridian (myblogs) project.</i>',
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=GRAY, alignment=TA_CENTER)))

    doc.build(story)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    build()
