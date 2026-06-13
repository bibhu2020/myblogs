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

MODEL = os.getenv("MAINTENANCE_MODEL", "gpt-5")


async def run_team(repo_root: str, server_base: str) -> tuple[str, list]:
    """Run the maintenance multi-agent team and return (summary, findings_list)."""
    model_client = OpenAIChatCompletionClient(model=MODEL)

    orchestrator = AssistantAgent(
        name="Orchestrator",
        model_client=model_client,
        system_message="""You are the Maintenance Orchestrator for the Meridian blogging platform.
Your job is to coordinate a team of specialist agents to perform a comprehensive monthly maintenance check.
Direct each specialist to run their checks in order:
1. Ask SecurityScanner to audit all 5 npm services for vulnerabilities and outdated packages.
2. Ask SEOAnalyzer to check all published posts for SEO issues.
3. Ask ADAAnalyzer to check post HTML content for accessibility violations.
4. Ask DependabotHandler to list all open GitHub PRs and assess their risk.

After all specialists have reported, synthesize their findings into a concise summary paragraph.
Then say exactly: MAINTENANCE_COMPLETE""",
    )

    security_scanner = AssistantAgent(
        name="SecurityScanner",
        model_client=model_client,
        tools=[tools.run_npm_audit, tools.list_outdated_packages, tools.read_source_file],
        system_message="""You are the Security Scanner for Meridian.
Run npm audit for each of these 5 services: api-gateway, auth-service, blog-service, media-service, frontend.
Also run list_outdated_packages for each service to find outdated dependencies.
Report all vulnerabilities found with severity (critical/high/medium/low) and recommended action.
Format your final report as JSON findings list where each item has: area, severity, message, detail.""",
    )

    seo_agent = AssistantAgent(
        name="SEOAnalyzer",
        model_client=model_client,
        tools=[tools.fetch_all_posts, tools.analyze_post_seo, tools.check_frontend_static],
        system_message="""You are the SEO and ADA Analyzer for Meridian.

Step 1 — Static frontend audit: call check_frontend_static() with no arguments. This verifies
index.html (lang, meta description, OG/Twitter tags, viewport, canonical), robots.txt,
router document.title hooks, skip-to-content link, newsletter aria-labels, social link
aria-labels, footer heading levels, focus-visible styles, and the Dependabot workflow file.
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
(Static frontend checks are handled by SEOAnalyzer — focus only on post HTML content.)

Call fetch_all_posts() to get all published posts.
For each post, call fetch_post_html(slug) to get its rendered HTML content,
then call analyze_html_fragment(html, slug) to check for WCAG AA violations
(missing alt attributes, empty buttons/links, heading level skips, tables without headers).

Report each violation with the post slug, element, and remediation guidance.
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
Report: PR number, title, author, age in days, semver bump type, risk level, and merge recommendation.
Dependabot patch-level PRs with no breaking changes are generally safe to merge.
Format your final report as JSON findings list where each item has: area="dependabot", severity, message, detail.""",
    )

    termination = TextMentionTermination("MAINTENANCE_COMPLETE") | MaxMessageTermination(80)

    team = SelectorGroupChat(
        [orchestrator, security_scanner, seo_agent, ada_agent, dependabot_agent],
        model_client=model_client,
        termination_condition=termination,
    )

    github_repo = os.getenv("GITHUB_REPO", "")
    task = f"""Perform a full monthly maintenance check for the Meridian blogging platform.
Repo root: {repo_root}
API base URL: {server_base}
GitHub repo: {github_repo if github_repo else "(GITHUB_REPO env var not set — skip dependabot check)"}

Run all checks:
1. SecurityScanner: audit all 5 npm services (api-gateway, auth-service, blog-service, media-service, frontend) for vulnerabilities and outdated packages
2. SEOAnalyzer: run check_frontend_static() for the static SEO/ADA audit (index.html, robots.txt, heading hierarchy, aria-labels, focus styles, Dependabot workflow), then check all posts for per-post SEO issues
3. ADAAnalyzer: check each published post's HTML content for WCAG AA violations
4. DependabotHandler: list all open GitHub PRs and assess their safety

After all specialists report, the Orchestrator should synthesize findings and say MAINTENANCE_COMPLETE."""

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
        # Collect specialist JSON findings blocks
        if source in ("SecurityScanner", "SEOAnalyzer", "ADAAnalyzer", "DependabotHandler"):
            # Try to extract JSON arrays from the message
            json_blocks = re.findall(r"\[[\s\S]*?\]", content)
            for block in json_blocks:
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

    # Use final orchestrator message as summary if available
    summary = " ".join(summary_parts).strip() or last_content[:1000]

    # Deduplicate findings
    seen = set()
    unique_findings = []
    for f in findings:
        key = (f.get("area"), f.get("message"))
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    return summary, unique_findings
