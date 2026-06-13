"""Tool functions for the maintenance agent specialists."""
import json
import os
import re
import subprocess
from pathlib import Path

import requests

SERVER_BASE = os.getenv("SERVER_BASE", "https://mishrabP-myblogs.hf.space")
REPO_ROOT = str(Path(__file__).parent.parent)

# ---------------------------------------------------------------------------
# SecurityScanner tools
# ---------------------------------------------------------------------------


def run_npm_audit(service: str) -> str:
    """Run npm audit in the specified service directory and return JSON findings.

    Args:
        service: One of api-gateway, auth-service, blog-service, media-service, frontend.
    """
    allowed = {"api-gateway", "auth-service", "blog-service", "media-service", "frontend"}
    if service not in allowed:
        return json.dumps({"error": f"Unknown service '{service}'. Valid: {sorted(allowed)}"})
    service_dir = os.path.join(REPO_ROOT, service)
    if not os.path.isdir(service_dir):
        return json.dumps({"error": f"Directory not found: {service_dir}"})
    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            cwd=service_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        raw = result.stdout.strip()
        if not raw:
            return json.dumps({"service": service, "error": "npm audit produced no output", "stderr": result.stderr[:500]})
        data = json.loads(raw)
        # Summarise for the agent
        meta = data.get("metadata", {})
        vulns = data.get("vulnerabilities", {})
        summary = {
            "service": service,
            "vulnerabilityCount": meta.get("vulnerabilities", {}),
            "auditReportVersion": data.get("auditReportVersion"),
            "topVulnerabilities": [
                {
                    "name": name,
                    "severity": info.get("severity"),
                    "isDirect": info.get("isDirect"),
                    "fixAvailable": info.get("fixAvailable"),
                    "via": [v if isinstance(v, str) else v.get("title", "") for v in info.get("via", [])[:3]],
                }
                for name, info in list(vulns.items())[:20]
            ],
        }
        return json.dumps(summary)
    except subprocess.TimeoutExpired:
        return json.dumps({"service": service, "error": "npm audit timed out after 120s"})
    except json.JSONDecodeError as exc:
        return json.dumps({"service": service, "error": f"Could not parse npm audit output: {exc}", "raw": raw[:300]})
    except Exception as exc:
        return json.dumps({"service": service, "error": str(exc)})


def list_outdated_packages(service: str) -> str:
    """List outdated npm packages for the specified service.

    Args:
        service: One of api-gateway, auth-service, blog-service, media-service, frontend.
    """
    allowed = {"api-gateway", "auth-service", "blog-service", "media-service", "frontend"}
    if service not in allowed:
        return json.dumps({"error": f"Unknown service '{service}'. Valid: {sorted(allowed)}"})
    service_dir = os.path.join(REPO_ROOT, service)
    if not os.path.isdir(service_dir):
        return json.dumps({"error": f"Directory not found: {service_dir}"})
    try:
        result = subprocess.run(
            ["npm", "outdated", "--json"],
            cwd=service_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        raw = result.stdout.strip()
        if not raw:
            return json.dumps({"service": service, "outdated": {}, "message": "No outdated packages found"})
        data = json.loads(raw)
        # Annotate with semver bump type
        def bump_type(current: str, latest: str) -> str:
            try:
                c = [int(x) for x in current.lstrip("^~").split(".")[:3]]
                l = [int(x) for x in latest.lstrip("^~").split(".")[:3]]
                if l[0] > c[0]:
                    return "major"
                if l[1] > c[1]:
                    return "minor"
                return "patch"
            except Exception:
                return "unknown"

        annotated = {
            pkg: {**info, "bumpType": bump_type(info.get("current", "0.0.0"), info.get("latest", "0.0.0"))}
            for pkg, info in data.items()
        }
        return json.dumps({"service": service, "outdated": annotated})
    except subprocess.TimeoutExpired:
        return json.dumps({"service": service, "error": "npm outdated timed out after 120s"})
    except json.JSONDecodeError:
        return json.dumps({"service": service, "message": "No outdated packages (or all up to date)", "raw": raw[:200]})
    except Exception as exc:
        return json.dumps({"service": service, "error": str(exc)})


def read_source_file(relative_path: str) -> str:
    """Read a source file from the myblogs project.

    Args:
        relative_path: File path relative to /home/azure/myblogs/, e.g. 'api-gateway/src/app.controller.ts'.
    """
    full_path = os.path.join(REPO_ROOT, relative_path.lstrip("/"))
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"ERROR: File not found: {full_path}"
    except Exception as exc:
        return f"ERROR: {exc}"


# ---------------------------------------------------------------------------
# SEOAnalyzer tools
# ---------------------------------------------------------------------------


def fetch_all_posts() -> str:
    """Fetch all published blog posts from the Meridian API. Returns a JSON summary."""
    try:
        resp = requests.get(f"{SERVER_BASE}/api/posts?limit=200", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        posts = data.get("posts", data) if isinstance(data, dict) else data
        summarised = [
            {
                "id": p.get("id"),
                "title": p.get("title", ""),
                "excerpt": p.get("excerpt", ""),
                "slug": p.get("slug", ""),
                "wordCount": p.get("wordCount", 0),
                "status": p.get("status", ""),
                "category": p.get("category", {}).get("name") if p.get("category") else None,
            }
            for p in (posts if isinstance(posts, list) else [])
        ]
        return json.dumps({"total": len(summarised), "posts": summarised})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def analyze_post_seo(title: str, excerpt: str, slug: str, word_count: int) -> str:
    """Analyze a single post's SEO quality and return a JSON report with score and issues.

    Args:
        title: The post title.
        excerpt: The post excerpt/description.
        slug: The URL slug.
        word_count: Estimated word count of the post body.
    """
    issues = []
    score = 100

    title_len = len(title)
    if title_len < 30:
        issues.append({"field": "title", "severity": "high", "message": f"Title too short ({title_len} chars, min 30)"})
        score -= 20
    elif title_len < 50:
        issues.append({"field": "title", "severity": "medium", "message": f"Title slightly short ({title_len} chars, ideal 50-60)"})
        score -= 10
    elif title_len > 70:
        issues.append({"field": "title", "severity": "medium", "message": f"Title too long ({title_len} chars, max 60-70)"})
        score -= 10

    excerpt_len = len(excerpt)
    if excerpt_len == 0:
        issues.append({"field": "excerpt", "severity": "critical", "message": "Missing meta description/excerpt"})
        score -= 30
    elif excerpt_len < 80:
        issues.append({"field": "excerpt", "severity": "high", "message": f"Excerpt too short ({excerpt_len} chars, ideal 120-160)"})
        score -= 20
    elif excerpt_len > 170:
        issues.append({"field": "excerpt", "severity": "low", "message": f"Excerpt may be truncated in SERPs ({excerpt_len} chars, max 160)"})
        score -= 5

    if "_" in slug:
        issues.append({"field": "slug", "severity": "medium", "message": "Slug contains underscores — use hyphens for SEO"})
        score -= 10
    if re.search(r"[A-Z]", slug):
        issues.append({"field": "slug", "severity": "medium", "message": "Slug contains uppercase letters — should be lowercase"})
        score -= 10
    if len(slug) > 75:
        issues.append({"field": "slug", "severity": "low", "message": f"Slug is long ({len(slug)} chars) — consider shortening"})
        score -= 5

    if word_count < 300:
        issues.append({"field": "content", "severity": "high", "message": f"Content very short ({word_count} words) — aim for 800+"})
        score -= 25
    elif word_count < 600:
        issues.append({"field": "content", "severity": "medium", "message": f"Content below recommended length ({word_count} words, aim for 800+)"})
        score -= 10

    read_time = max(1, round(word_count / 200))
    return json.dumps({"score": max(0, score), "issues": issues, "readTimeMinutes": read_time})


# ---------------------------------------------------------------------------
# ADAAnalyzer tools
# ---------------------------------------------------------------------------


def analyze_html_fragment(html: str, context: str) -> str:
    """Analyze an HTML fragment for ADA/WCAG AA compliance issues.

    Args:
        html: Raw HTML string to analyze.
        context: Human-readable context (e.g. post slug or section name) for the report.
    """
    findings = []

    # Images without alt
    img_tags = re.findall(r"<img[^>]*>", html, re.IGNORECASE)
    for tag in img_tags:
        if 'alt=' not in tag.lower():
            src = re.search(r'src=["\']([^"\']+)["\']', tag)
            src_val = src.group(1)[:60] if src else "(unknown)"
            findings.append({
                "wcag": "1.1.1",
                "severity": "critical",
                "element": "img",
                "message": f"Image missing alt attribute: {src_val}",
            })
        elif re.search(r'alt=["\']["\']', tag):
            findings.append({
                "wcag": "1.1.1",
                "severity": "medium",
                "element": "img",
                "message": "Image has empty alt attribute — ensure this is intentional (decorative only)",
            })

    # Buttons without text or aria-label
    button_tags = re.findall(r"<button[^>]*>.*?</button>", html, re.IGNORECASE | re.DOTALL)
    for tag in button_tags:
        inner = re.sub(r"<[^>]+>", "", tag).strip()
        has_aria = "aria-label=" in tag.lower() or "aria-labelledby=" in tag.lower()
        if not inner and not has_aria:
            findings.append({
                "wcag": "4.1.2",
                "severity": "critical",
                "element": "button",
                "message": "Button has no accessible label (no text content or aria-label)",
            })

    # Links without discernible text
    link_tags = re.findall(r"<a[^>]*>.*?</a>", html, re.IGNORECASE | re.DOTALL)
    for tag in link_tags:
        inner = re.sub(r"<[^>]+>", "", tag).strip()
        has_aria = "aria-label=" in tag.lower() or "aria-labelledby=" in tag.lower()
        href = re.search(r'href=["\']([^"\']+)["\']', tag)
        if not inner and not has_aria and href:
            findings.append({
                "wcag": "2.4.4",
                "severity": "high",
                "element": "a",
                "message": f"Link missing discernible text: {href.group(1)[:60]}",
            })

    # Heading hierarchy — check for skipped levels
    headings = re.findall(r"<(h[1-6])[^>]*>", html, re.IGNORECASE)
    levels = [int(h[1]) for h in headings]
    for i in range(1, len(levels)):
        if levels[i] - levels[i - 1] > 1:
            findings.append({
                "wcag": "1.3.1",
                "severity": "medium",
                "element": f"h{levels[i]}",
                "message": f"Heading level skipped from h{levels[i-1]} to h{levels[i]}",
            })

    # Tables without headers
    tables = re.findall(r"<table[^>]*>.*?</table>", html, re.IGNORECASE | re.DOTALL)
    for table in tables:
        if "<th" not in table.lower() and "scope=" not in table.lower():
            findings.append({
                "wcag": "1.3.1",
                "severity": "medium",
                "element": "table",
                "message": "Table has no <th> elements — add header cells with scope attribute",
            })

    return json.dumps({"context": context, "issueCount": len(findings), "findings": findings})


def fetch_post_html(slug: str) -> str:
    """Fetch the raw HTML content field of a blog post by slug.

    Args:
        slug: The URL slug of the blog post.
    """
    try:
        resp = requests.get(f"{SERVER_BASE}/api/posts/{slug}", timeout=30)
        resp.raise_for_status()
        post = resp.json()
        content = post.get("content", "")
        return json.dumps({"slug": slug, "title": post.get("title", ""), "html": content})
    except Exception as exc:
        return json.dumps({"error": str(exc), "slug": slug})


# ---------------------------------------------------------------------------
# DependabotHandler tools
# ---------------------------------------------------------------------------


def list_github_prs(owner: str, repo: str) -> str:
    """List open pull requests on a GitHub repository.

    Uses the GITHUB_TOKEN environment variable for authentication.

    Args:
        owner: GitHub repository owner/org, e.g. 'bibhu2020'.
        repo: Repository name, e.g. 'myblogs'.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            params={"state": "open", "per_page": 100},
            headers=headers,
            timeout=30,
        )
        if resp.status_code == 404:
            return json.dumps({"error": f"Repository {owner}/{repo} not found or not accessible"})
        resp.raise_for_status()
        prs = resp.json()
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        summarised = []
        for pr in prs:
            created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
            age_days = (now - created).days
            summarised.append({
                "number": pr["number"],
                "title": pr["title"],
                "author": pr["user"]["login"],
                "ageDays": age_days,
                "createdAt": pr["created_at"],
                "url": pr["html_url"],
                "isDependabot": pr["user"]["login"].startswith("dependabot"),
                "labels": [lb["name"] for lb in pr.get("labels", [])],
            })
        return json.dumps({"total": len(summarised), "pulls": summarised})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def get_pr_details(owner: str, repo: str, pr_number: int) -> str:
    """Get details of a specific GitHub PR including files changed.

    Uses the GITHUB_TOKEN environment variable for authentication.

    Args:
        owner: GitHub repository owner/org.
        repo: Repository name.
        pr_number: Pull request number.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        pr_resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
            headers=headers,
            timeout=30,
        )
        if pr_resp.status_code == 404:
            return json.dumps({"error": f"PR #{pr_number} not found in {owner}/{repo}"})
        pr_resp.raise_for_status()
        pr = pr_resp.json()

        files_resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files",
            headers=headers,
            timeout=30,
        )
        files = files_resp.json() if files_resp.ok else []

        # Determine semver bump from title (Dependabot titles contain "from X.Y.Z to A.B.C")
        bump = "unknown"
        m = re.search(r"from (\d+)\.(\d+)\.(\d+) to (\d+)\.(\d+)\.(\d+)", pr.get("title", ""))
        if m:
            old = [int(m.group(i)) for i in (1, 2, 3)]
            new = [int(m.group(i)) for i in (4, 5, 6)]
            if new[0] > old[0]:
                bump = "major"
            elif new[1] > old[1]:
                bump = "minor"
            else:
                bump = "patch"

        risk = {"major": "high", "minor": "medium", "patch": "low"}.get(bump, "unknown")

        return json.dumps({
            "number": pr["number"],
            "title": pr["title"],
            "author": pr["user"]["login"],
            "state": pr["state"],
            "body": (pr.get("body") or "")[:500],
            "filesChanged": len(files),
            "changedFiles": [f["filename"] for f in files[:20]],
            "semverBump": bump,
            "riskLevel": risk,
            "mergeable": pr.get("mergeable"),
            "url": pr["html_url"],
        })
    except Exception as exc:
        return json.dumps({"error": str(exc)})
