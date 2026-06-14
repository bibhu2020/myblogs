"""Maintenance agent — sequential 3-phase pipeline.

Phase 1: Dependabot PRs  — fetch all open Dependabot PRs, analyze, fix code if
          needed, merge to main, close the PR.
Phase 2: Sitemap + 404   — generate/update sitemap.xml, check every URL, fix 404s.
Phase 3: SEO & ADA       — scan frontend source + post content, fix issues found.

All code fixes use the branch → commit → push → PR → merge → close workflow.
"""
import os
import re

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

from . import tools

MODEL = os.getenv("MAINTENANCE_MODEL") or "gpt-4o"

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


async def _run_agent(agent: AssistantAgent, task: str, max_turns: int = 80) -> str:
    """Run a single agent on a task and return its final text response."""
    team = RoundRobinGroupChat([agent], termination_condition=MaxMessageTermination(max_turns))
    last_content = ""
    async for message in team.run_stream(task=task):
        if isinstance(message, TaskResult):
            break
        content = getattr(message, "content", None)
        source = getattr(message, "source", "")
        if isinstance(content, str) and content.strip():
            print(f"[{source}] {content[:400]}{'...' if len(content) > 400 else ''}")
            last_content = content
    return last_content


# ── Shared tool groups ─────────────────────────────────────────────────────────

_BRANCH_PR_TOOLS = [
    tools.get_github_repo,
    tools.get_current_branch,
    tools.git_checkout_branch,
    tools.git_pull_main,
    tools.git_stage_and_commit,
    tools.git_push_current_branch,
    tools.create_github_pr,
    tools.merge_github_pr,
    tools.close_github_pr,
    tools.delete_github_branch,
    tools.git_status_short,
    tools.git_diff_changes,
]

_CODE_TOOLS = [
    tools.read_source_file,
    tools.apply_file_patch,
    tools.revert_file,
]

_BUILD_TOOL = [tools.run_frontend_build]

# ── Branch/PR workflow block injected into every fix agent system message ──────

_BRANCH_PR_INSTRUCTIONS = """
BRANCH / PR WORKFLOW (mandatory for all code fixes):
  1. Call get_github_repo() to obtain owner and repo values.
  2. Call git_checkout_branch(branch_name, create_from_main=True) — syncs main + creates branch.
  3. Apply fixes using apply_file_patch (call read_source_file first to get exact content).
  4. For frontend Vue/CSS/HTML fixes: call run_frontend_build() to validate.
       If BUILD FAILED → call revert_file, re-patch, re-validate.
  5. Call git_stage_and_commit("fix: <concise description>").
  6. Call git_push_current_branch().
  7. Call create_github_pr(owner, repo, title, body, head_branch, "main").
  8. Call merge_github_pr(owner, repo, pr_number, "squash").
  9. Call delete_github_branch(owner, repo, branch_name) to clean up the remote branch.
 10. Call git_pull_main() so local main is in sync before the next fix cycle.

If GITHUB_REPO is not set, skip steps 1–2 and 6–10 (apply fixes directly on main, no PR needed).
"""


async def run_team(repo_root: str, server_base: str) -> tuple[str, list]:
    """Run the 3-phase maintenance pipeline and return (summary, findings)."""
    client = _make_client()
    github_repo = os.getenv("GITHUB_REPO", "")
    owner, repo = github_repo.split("/", 1) if "/" in github_repo else ("", "")

    summaries: list[str] = []
    findings: list[dict] = []

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 1 — Dependabot PRs
    # ══════════════════════════════════════════════════════════════════════════
    print("\n╔══════════════════════════════════════╗")
    print("║  Phase 1: Dependabot PRs             ║")
    print("╚══════════════════════════════════════╝\n")

    if not github_repo:
        print("[Phase 1] SKIPPED — GITHUB_REPO env var not set")
        summaries.append("Phase 1 (Dependabot): Skipped — GITHUB_REPO not configured.")
    else:
        dep_agent = AssistantAgent(
            name="DependabotAgent",
            model_client=client,
            tools=[
                tools.list_github_prs,
                tools.get_pr_details,
                tools.merge_github_pr,
                tools.close_github_pr,
                *_BRANCH_PR_TOOLS,
                *_CODE_TOOLS,
                *_BUILD_TOOL,
            ],
            system_message=f"""You handle ALL open Dependabot pull requests for the Meridian blogging platform.
GitHub repo: {github_repo}  (owner="{owner}", repo="{repo}")

STEPS:
1. Call list_github_prs("{owner}", "{repo}") to get all open PRs.
2. For each PR where isDependabot == true:
   a. Call get_pr_details("{owner}", "{repo}", pr_number) to read semverBump, riskLevel, changedFiles.
   b. Act based on riskLevel:

      LOW or MEDIUM (patch or minor semver bump):
        → Call merge_github_pr("{owner}", "{repo}", pr_number, "squash").
        → The PR auto-closes on merge. Report: "Merged PR #N: <title>".

      HIGH (major semver bump):
        → Inspect changedFiles: call read_source_file for each relevant source file.
        → Use your knowledge of the package (inferred from the PR title) to determine
          whether application code must be updated for the new major version API.
        → If code changes ARE needed:
{_BRANCH_PR_INSTRUCTIONS}
            Use branch name "fix/dep-pr-{{pr_number}}".
            Commit: "fix: update code for major dep bump (PR #{{pr_number}})".
            After fix PR is merged, call git_pull_main().
        → Merge the Dependabot PR:
            Call merge_github_pr("{owner}", "{repo}", pr_number, "squash").
        → Report: "Merged PR #N (code fix applied)" or "Merged PR #N (no code change needed)".

      UNKNOWN semver bump:
        → Treat as HIGH risk. Apply the same major-bump process above.

3. Skip all PRs where isDependabot == false (never touch human-authored PRs).
4. End with: "Merged: N | Skipped (non-Dependabot): N".
""",
        )
        dep_task = (
            f"Process all open Dependabot PRs for {github_repo}. "
            "List all open PRs, handle each Dependabot PR per your instructions, "
            "and report final counts."
        )
        result = await _run_agent(dep_agent, dep_task, max_turns=100)
        summaries.append(f"Phase 1 (Dependabot): {result[:800]}")
        findings.extend(_extract_findings(result, "dependabot"))

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 2 — Sitemap + 404 Validation
    # ══════════════════════════════════════════════════════════════════════════
    print("\n╔══════════════════════════════════════╗")
    print("║  Phase 2: Sitemap + 404 Validation   ║")
    print("╚══════════════════════════════════════╝\n")

    sitemap_agent = AssistantAgent(
        name="SitemapAgent",
        model_client=client,
        tools=[
            tools.get_sitemap_urls,
            tools.generate_sitemap,
            tools.check_url_status,
            *_BRANCH_PR_TOOLS,
            *_CODE_TOOLS,
        ],
        system_message=f"""You manage sitemap.xml and 404 health for the Meridian blogging platform.
Live site: {server_base}
GitHub repo: {github_repo}

STEP 1 — Sitemap check / generation:
  Call get_sitemap_urls().
  • If exists=false or count==0: call generate_sitemap() to create it.
  • If exists=true: use the current URLs.

STEP 2 — 404 scan:
  For EACH URL in the sitemap call check_url_status(url).
  Collect all URLs where is404==true.
  (Note: for /post/<slug> and /story/<id> the tool automatically checks the backing API endpoint.)

STEP 3 — Fix 404s:
  For each 404 URL, determine the fix:
  • /post/<slug> or /story/<id>  → the content no longer exists; remove it from sitemap.xml.
  • Static route                 → inspect router with read_source_file("frontend/src/router/index.js");
                                   if the route is genuinely missing, add it or remove from sitemap.
  Make changes using the branch/PR workflow:
{_BRANCH_PR_INSTRUCTIONS}
  Branch name: "fix/sitemap-404s".
  Include the updated sitemap.xml in the same commit.

STEP 4 — Regenerate sitemap if content changed:
  If URLs were removed or fixed, call generate_sitemap() to rebuild sitemap.xml.
  If the sitemap itself was modified outside of step 3, commit it in its own branch/PR:
    Branch name: "fix/sitemap-update".

STEP 5 — Report:
  "Checked N URLs | 404s: N | Fixed: N | Sitemap updated: yes/no"

If no 404s are found: report "Sitemap healthy — N URLs checked, 0 dead links" and stop.
""",
    )
    sitemap_task = (
        f"Validate the Meridian sitemap and fix 404s. Server: {server_base}. "
        "Check/generate sitemap, scan every URL, fix dead links via branch/PR, report results."
    )
    result = await _run_agent(sitemap_agent, sitemap_task, max_turns=80)
    summaries.append(f"Phase 2 (Sitemap/404): {result[:800]}")
    findings.extend(_extract_findings(result, "sitemap"))

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 3 — SEO & ADA Fixes
    # ══════════════════════════════════════════════════════════════════════════
    print("\n╔══════════════════════════════════════╗")
    print("║  Phase 3: SEO & ADA Fixes            ║")
    print("╚══════════════════════════════════════╝\n")

    seo_ada_agent = AssistantAgent(
        name="SEOADAAgent",
        model_client=client,
        tools=[
            tools.check_frontend_static,
            tools.fetch_all_posts,
            tools.analyze_post_seo,
            tools.fetch_post_html,
            tools.analyze_html_fragment,
            *_BRANCH_PR_TOOLS,
            *_CODE_TOOLS,
            *_BUILD_TOOL,
        ],
        system_message=f"""You audit and fix SEO and ADA/WCAG AA issues in the Meridian blogging platform.
GitHub repo: {github_repo}

AUDIT:

STEP 1 — Static frontend source audit:
  Call check_frontend_static() — checks index.html, robots.txt, router, App.vue, Home.vue,
  Navbar.vue, Footer.vue, BlogPost.vue, and style.css.
  Collect every item in the "failed" array.

STEP 2 — Per-post SEO:
  Call fetch_all_posts(). For each post call analyze_post_seo(title, excerpt, slug, wordCount).
  Collect posts with score < 80 or any "high"/"critical" issues.

STEP 3 — Per-post ADA:
  For each post from fetch_all_posts() call fetch_post_html(slug), then
  analyze_html_fragment(html, slug). Collect posts with WCAG violations.

FIX:

STEP 4 — Apply fixes (one branch/PR per logical fix group):
  Only touch static source files — NEVER modify NestJS backend files, package.json, or lock files.
  Fixable items: missing/wrong meta tags, aria-labels, heading levels, alt attributes,
  focus-visible rules, robots.txt entries, canonical link, lang attribute.

  Group related fixes by file. For each group:
{_BRANCH_PR_INSTRUCTIONS}
  Branch name: "fix/seo-ada-<short-description>" (e.g. "fix/seo-ada-meta-tags").
  Run run_frontend_build() after patching and before pushing.

STEP 5 — Report:
  "SEO issues: N | ADA issues: N | Fixes applied: N | Build: PASSED/FAILED"

If there are no fixable issues: report that clearly and stop.
""",
    )
    seo_ada_task = (
        f"Audit and fix SEO/ADA issues for the Meridian frontend. Server: {server_base}. "
        "Run all 3 audit steps, then apply fixes via branch/PR workflow. Report findings and actions."
    )
    result = await _run_agent(seo_ada_agent, seo_ada_task, max_turns=100)
    summaries.append(f"Phase 3 (SEO/ADA): {result[:800]}")
    findings.extend(_extract_findings(result, "seo_ada"))

    # ── Ensure local main is clean after all phases ────────────────────────────
    tools.git_pull_main()

    summary = "\n\n".join(summaries)
    return summary, findings


def _extract_findings(text: str, area: str) -> list[dict]:
    """Extract a brief finding entry from an agent's summary text."""
    for m in re.finditer(r"(\d+)\s+(issue|violation|404|error|finding|problem)", text, re.I):
        count = int(m.group(1))
        kind = m.group(2).lower()
        if count > 0:
            return [{
                "area": area,
                "severity": "info",
                "message": f"{count} {kind}(s) found in {area} phase",
                "detail": text[:300],
            }]
    return []
