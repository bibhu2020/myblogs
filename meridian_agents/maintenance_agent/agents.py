"""AutoGen 0.4 multi-agent team for Meridian maintenance."""
import json
import os
import re

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

from . import tools

MODEL = os.getenv("MAINTENANCE_MODEL") or "gpt-4o"

# AutoGen's client registry only knows standard OpenAI model IDs. For any other
# name (e.g. a future "gpt-5" or a fine-tuned model), we must supply model_info
# manually so AutoGen knows its capabilities.
_AUTOGEN_KNOWN_MODELS = {
    "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4",
    "gpt-3.5-turbo", "o1", "o1-mini", "o1-preview", "o3", "o3-mini",
}


def _make_client() -> OpenAIChatCompletionClient:
    if MODEL in _AUTOGEN_KNOWN_MODELS:
        return OpenAIChatCompletionClient(model=MODEL)
    from autogen_core.models import ModelInfo
    info: ModelInfo = {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": "gpt-4o",
    }
    return OpenAIChatCompletionClient(model=MODEL, model_info=info)


async def run_team(repo_root: str, server_base: str) -> tuple[str, list]:
    """Run the maintenance multi-agent team and return (summary, findings_list)."""
    model_client = _make_client()

    # ── Phase orchestration ────────────────────────────────────────────────────
    orchestrator = AssistantAgent(
        name="Orchestrator",
        model_client=model_client,
        system_message="""You are the Maintenance Orchestrator for the Meridian blogging platform.
Coordinate the team through 3 phases in strict order.

PHASE 1 — AUDIT (collect findings from all 4 specialists):
1. Ask SecurityScanner to audit all 5 npm services for vulnerabilities and outdated packages.
2. Ask SEOAnalyzer to run check_frontend_static() then check all posts for per-post SEO issues.
3. Ask ADAAnalyzer to check each published post's HTML content for WCAG AA violations.
4. Ask DependabotHandler to list open GitHub PRs and assess their risk.
Wait for each specialist to finish before moving to the next.

PHASE 2 — FIX & SELF-REFLECT (apply safe static fixes and verify the build):
After all audit reports are in, identify low-risk static fixes from the SEO/ADA findings
(e.g. missing meta tags, aria-labels, heading levels, focus styles — NOT logic or backend changes).
Tell CodePatcher exactly which fix to apply and in which file. Give one fix at a time.
After CodePatcher confirms a batch of fixes, tell BuildValidator to run the frontend build.
If BuildValidator reports BUILD FAILED:
  - Tell CodePatcher to revert the file that caused the error (using revert_file).
  - Have CodePatcher apply a corrected version of the patch.
  - Ask BuildValidator to re-run the build.
  - Repeat until BuildValidator confirms BUILD PASSED.
If no static fixes are needed or all checks already pass, proceed directly to Phase 3.

PHASE 3 — PUBLISH (commit and push validated changes):
Once BuildValidator has confirmed BUILD PASSED (or if no changes were made), tell GitPublisher
to commit and push all staged changes to GitHub with a descriptive 'maint:' commit message
summarising what was fixed.
If the working tree is clean (no changes), skip this step.

After all phases complete, write a concise paragraph summarising:
findings per category, fixes applied, build validation status, and GitHub publish status.
End with exactly: MAINTENANCE_COMPLETE""",
    )

    # ── Phase 1: Audit agents ──────────────────────────────────────────────────
    security_scanner = AssistantAgent(
        name="SecurityScanner",
        model_client=model_client,
        tools=[tools.run_npm_audit, tools.list_outdated_packages, tools.read_source_file],
        system_message="""You are the Security Scanner for Meridian.
Run npm audit for each of these 5 services: api-gateway, auth-service, blog-service, media-service, frontend.
Also run list_outdated_packages for each service to find outdated dependencies.
Report all vulnerabilities with severity (critical/high/medium/low) and recommended action.
Format your final report as a JSON findings list where each item has: area, severity, message, detail.""",
    )

    seo_agent = AssistantAgent(
        name="SEOAnalyzer",
        model_client=model_client,
        tools=[tools.fetch_all_posts, tools.analyze_post_seo, tools.check_frontend_static],
        system_message="""You are the SEO Analyzer for Meridian.

Step 1 — Static frontend audit: call check_frontend_static() with no arguments.
Report every "failed" item from the result.

Step 2 — Per-post SEO: call fetch_all_posts(), then call analyze_post_seo() for each post
(pass title, excerpt, slug, and wordCount). Report every post with SEO issues.

Format your final report as a JSON findings list where each item has:
area ("seo" or "ada"), severity, message, detail.""",
    )

    ada_agent = AssistantAgent(
        name="ADAAnalyzer",
        model_client=model_client,
        tools=[tools.fetch_all_posts, tools.fetch_post_html, tools.analyze_html_fragment],
        system_message="""You are the post-content ADA Analyzer for Meridian.
(Static frontend checks are handled by SEOAnalyzer — focus only on post HTML content here.)

Call fetch_all_posts() to get all published posts.
For each post, call fetch_post_html(slug) to get its rendered HTML content,
then call analyze_html_fragment(html, slug) to check for WCAG AA violations
(missing alt attributes, empty buttons/links, heading level skips, tables without headers).

Format your final report as a JSON findings list: area="ada", severity, message, detail.""",
    )

    dependabot_agent = AssistantAgent(
        name="DependabotHandler",
        model_client=model_client,
        tools=[tools.list_github_prs, tools.get_pr_details],
        system_message="""You are the Dependabot Handler for Meridian.
Check the GitHub repository for open pull requests using the GITHUB_REPO environment variable
(format: owner/repo, e.g. bibhu2020/myblogs). If GITHUB_REPO is not set, report that and skip.
For each open PR, call get_pr_details to assess its risk level.
Report: PR number, title, author, age in days, semver bump type, risk level, merge recommendation.
Format your final report as JSON findings list: area="dependabot", severity, message, detail.""",
    )

    # ── Phase 2: Fix agent ────────────────────────────────────────────────────
    code_patcher = AssistantAgent(
        name="CodePatcher",
        model_client=model_client,
        tools=[
            tools.apply_file_patch,
            tools.read_source_file,
            tools.revert_file,
            tools.git_diff_changes,
        ],
        system_message="""You are the CodePatcher for Meridian. You apply safe, surgical fixes to frontend source files.

RULES:
- Only apply the specific fix the Orchestrator asks for — nothing else.
- Always call read_source_file first to see the exact current content before patching.
- Use apply_file_patch with the exact old_string as it appears in the file — character-for-character.
- If apply_file_patch returns "old_string not found", read the file again to find the correct text.
- Apply ONE fix at a time and confirm success before moving on to the next.
- If asked to revert a file, call revert_file with the exact relative path (e.g. 'frontend/index.html').
- After all requested fixes are applied, call git_diff_changes() and report what changed.
- Do NOT touch NestJS backend files, package.json, or lock files — only frontend source and static assets.
- Do NOT make unrequested changes.""",
    )

    # ── Phase 2: Self-reflection agent ────────────────────────────────────────
    build_validator = AssistantAgent(
        name="BuildValidator",
        model_client=model_client,
        tools=[tools.run_frontend_build, tools.git_diff_changes],
        system_message="""You are the BuildValidator — the self-reflection agent for Meridian.
Your role is to verify that code changes are safe before they can be published to GitHub.

When asked to validate:
1. Call git_diff_changes() to confirm which files were modified.
2. Call run_frontend_build() to compile the frontend with Vite.
3. Analyse the result:
   - returnCode == 0  →  announce "BUILD PASSED — changes are safe to publish."
   - returnCode != 0  →  announce "BUILD FAILED" with the exact error lines from stdout/stderr.
     Identify which file and line caused the failure so CodePatcher can fix or revert it.
     Do NOT allow publishing until a subsequent build returns returnCode 0.

Note: chunk-size warnings ('Some chunks are larger than 500 kB') are NOT failures.
Only returnCode != 0 is a true build failure.

After a revert+re-patch cycle, run the build again to re-validate.
Keep re-validating until you can announce BUILD PASSED.""",
    )

    # ── Phase 3: Publish agent ────────────────────────────────────────────────
    git_publisher = AssistantAgent(
        name="GitPublisher",
        model_client=model_client,
        tools=[tools.git_commit_and_push, tools.git_status_short],
        system_message="""You are the GitPublisher for Meridian. You commit and push validated changes to GitHub.

IMPORTANT: Only act when ALL of these are true:
  1. The Orchestrator explicitly asks you to publish.
  2. BuildValidator has announced BUILD PASSED in this session (or no code changes were made).

Steps:
1. Call git_status_short() to see which files were modified.
2. Call git_commit_and_push(message) with a descriptive commit message using the 'maint:' prefix,
   e.g. 'maint: fix aria-labels, heading levels, and OG meta tags (monthly maintenance)'.
3. Report the result clearly — success/failure, commit hash, and any push errors.

If push fails because of GitHub Actions workflow file permissions,
note it separately and treat the rest of the commit as a success.
Do NOT call git_commit_and_push more than once per session.""",
    )

    # ── Team assembly ─────────────────────────────────────────────────────────
    termination = TextMentionTermination("MAINTENANCE_COMPLETE") | MaxMessageTermination(120)

    team = SelectorGroupChat(
        [
            orchestrator,
            security_scanner,
            seo_agent,
            ada_agent,
            dependabot_agent,
            code_patcher,
            build_validator,
            git_publisher,
        ],
        model_client=model_client,
        termination_condition=termination,
    )

    github_repo = os.getenv("GITHUB_REPO", "")
    task = f"""Perform a full monthly maintenance cycle for the Meridian blogging platform.
Repo root: {repo_root}
API base URL: {server_base}
GitHub repo: {github_repo if github_repo else "(GITHUB_REPO env var not set — skip dependabot check)"}

Run all 3 phases in order:

PHASE 1 — AUDIT: Run SecurityScanner, SEOAnalyzer, ADAAnalyzer, and DependabotHandler in sequence.

PHASE 2 — FIX & SELF-REFLECT:
  CodePatcher applies safe static fixes found in Phase 1 (one file at a time).
  BuildValidator (self-reflection agent) runs the Vite frontend build after each batch of fixes.
  If build fails → CodePatcher reverts the breaking change and applies a corrected patch.
  BuildValidator re-runs until it confirms BUILD PASSED.

PHASE 3 — PUBLISH:
  GitPublisher commits all validated changes and pushes to GitHub.
  If no changes were made, skip this step.

Orchestrator synthesises findings and concludes with MAINTENANCE_COMPLETE."""

    # ── Stream processing ─────────────────────────────────────────────────────
    audit_agents = {"SecurityScanner", "SEOAnalyzer", "ADAAnalyzer", "DependabotHandler"}
    findings: list = []
    summary_parts: list = []
    last_content: str = ""

    async for message in team.run_stream(task=task):
        if isinstance(message, TaskResult):
            break
        content = getattr(message, "content", None)
        source = getattr(message, "source", "")
        if not isinstance(content, str) or not content.strip():
            continue
        print(f"[{source}] {content[:200]}{'...' if len(content) > 200 else ''}")
        last_content = content
        # Collect JSON findings only from audit-phase agents
        if source in audit_agents:
            for block in re.findall(r"\[[\s\S]*?\]", content):
                try:
                    items = json.loads(block)
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and "message" in item:
                                findings.append({
                                    "area": item.get("area", source.lower()),
                                    "severity": item.get("severity", "info"),
                                    "message": item.get("message", ""),
                                    "detail": item.get("detail", ""),
                                })
                except (json.JSONDecodeError, ValueError):
                    pass
        if source == "Orchestrator" and "MAINTENANCE_COMPLETE" not in content:
            summary_parts.append(content)

    summary = " ".join(summary_parts).strip() or last_content[:1000]

    # Deduplicate findings by (area, message)
    seen: set = set()
    unique_findings: list = []
    for f in findings:
        key = (f.get("area"), f.get("message"))
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    return summary, unique_findings
