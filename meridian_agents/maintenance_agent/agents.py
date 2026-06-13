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
Coordinate the team through 4 phases in strict order.

PHASE 1 — AUDIT (SEO + ADA + Security scan):
1. Ask SecurityScanner to audit all 5 npm services for vulnerabilities and outdated packages.
2. Ask SEOAnalyzer to run check_frontend_static() then check all posts for per-post SEO issues.
3. Ask ADAAnalyzer to check each published post's HTML content for WCAG AA violations.
Wait for all three to finish before Phase 2.

PHASE 2 — DEPENDABOT (merge or close open Dependabot PRs):
Ask DependabotHandler to:
  a. Call list_github_prs to find ALL open PRs (split GITHUB_REPO into owner/repo).
  b. For each PR where isDependabot == true, call get_pr_details to check semverBump and riskLevel.
  c. For patch and minor semver PRs (riskLevel low or medium): call merge_github_pr to merge them.
  d. For major semver PRs (riskLevel high): call close_github_pr with a reason explaining that
     major version bumps require human review.
  e. Skip any PRs where isDependabot == false (leave those for human review).
  f. Report a summary: how many merged, how many closed, how many skipped.
If GITHUB_REPO is not set, skip Phase 2 entirely.

PHASE 3 — FIX & SELF-REFLECT (apply safe static fixes from Phase 1 and verify the build):
Identify low-risk static fixes from the SEO/ADA findings in Phase 1
(e.g. missing meta tags, aria-labels, heading levels, focus styles — NOT logic or backend changes).
Tell CodePatcher exactly which fix to apply and in which file. Give one fix at a time.
After CodePatcher confirms a batch of fixes, tell BuildValidator to run the frontend build.
If BuildValidator reports BUILD FAILED:
  - Tell CodePatcher to revert the file that caused the error (using revert_file).
  - Have CodePatcher apply a corrected version of the patch.
  - Ask BuildValidator to re-run the build.
  - Repeat until BuildValidator confirms BUILD PASSED.
If no static fixes are needed or all checks already pass, proceed directly to Phase 4.

PHASE 4 — PUBLISH (commit and push validated SEO/ADA fixes):
Tell GitPublisher to:
  1. First call git_pull_rebase to sync with any Dependabot merges that updated the remote.
  2. Then commit and push all staged changes with a descriptive 'maint:' commit message.
If the working tree is clean (no changes from Phase 3), skip the commit step but still pull.

After all phases complete, write a concise paragraph summarising:
Phase 1 findings per category, Phase 2 Dependabot actions, Phase 3 fixes applied,
build validation status, and Phase 4 publish status.
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
        tools=[
            tools.list_github_prs,
            tools.get_pr_details,
            tools.merge_github_pr,
            tools.close_github_pr,
        ],
        system_message="""You are the Dependabot Handler for Meridian. You list, assess, and ACT on open PRs.

GITHUB_REPO env var format: owner/repo  (e.g. bibhu2020/myblogs).
Split it on '/' to get owner and repo for each tool call.
If GITHUB_REPO is not set, report that and stop.

Steps (execute ALL of them):
1. Call list_github_prs(owner, repo) to get all open PRs.
2. For each PR where isDependabot == true:
   a. Call get_pr_details(owner, repo, pr_number) to check semverBump and riskLevel.
   b. If semverBump is 'patch' or 'minor' (riskLevel low or medium):
      → Call merge_github_pr(owner, repo, pr_number, 'squash') to merge it.
      → Report: "Merged PR #N: <title>"
   c. If semverBump is 'major' (riskLevel high):
      → Call close_github_pr(owner, repo, pr_number,
          "Major version bump requires manual review before merging.") to close it.
      → Report: "Closed PR #N: <title> (major bump — needs human review)"
   d. If semverBump is 'unknown' (version format not parseable):
      → Treat as high risk. Call close_github_pr with reason
          "Could not determine semver bump type — closing for manual review.".
      → Report: "Closed PR #N: <title> (unknown bump — needs human review)"
3. Skip any PRs where isDependabot == false (do not touch human PRs).
4. Report final counts: merged N, closed N, skipped N.

Format your final report as a JSON findings list where each item has:
area="dependabot", severity ("low"/"medium"/"high"), message, detail (include PR number and action taken).""",
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
        tools=[tools.git_commit_and_push, tools.git_status_short, tools.git_pull_rebase],
        system_message="""You are the GitPublisher for Meridian. You sync with remote, then commit and push validated changes.

IMPORTANT: Only act when the Orchestrator explicitly asks you to publish.

Steps (always in this order):
1. Call git_pull_rebase() to sync the local branch with the remote.
   This is required because DependabotHandler may have merged PRs that added commits to remote main.
   If pull fails, report the error — do not proceed to commit.
2. Call git_status_short() to see which local files were modified by CodePatcher.
3. If there are local changes: call git_commit_and_push(message) with a 'maint:' prefix message
   summarising what was fixed, e.g.:
   'maint: fix aria-labels, viewport meta, OG tags, heading levels (monthly maintenance)'
4. If the working tree is clean after the pull: report "No local changes to commit — pull complete."

Report the result clearly — success/failure, commit hash, and any push errors.
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
GitHub repo: {github_repo if github_repo else "(GITHUB_REPO env var not set — skip Phase 2)"}

Run all 4 phases in strict order:

PHASE 1 — AUDIT: Run SecurityScanner, SEOAnalyzer, and ADAAnalyzer in sequence.

PHASE 2 — DEPENDABOT:
  DependabotHandler lists all open PRs, merges safe Dependabot patch/minor PRs,
  and closes risky major-version PRs.
  {'Skip Phase 2 — GITHUB_REPO is not set.' if not github_repo else ''}

PHASE 3 — FIX & SELF-REFLECT:
  CodePatcher applies safe static SEO/ADA fixes found in Phase 1 (one file at a time).
  BuildValidator runs the Vite frontend build after each batch of fixes.
  If build fails → CodePatcher reverts and re-patches; BuildValidator re-runs until BUILD PASSED.

PHASE 4 — PUBLISH:
  GitPublisher first calls git_pull_rebase to sync with any Dependabot merges,
  then commits and pushes the Phase 3 SEO/ADA fixes.
  If no local changes, just pull and report.

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
