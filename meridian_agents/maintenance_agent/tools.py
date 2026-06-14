"""Tool functions for the maintenance agent specialists."""
import json
import os
import re
import subprocess
from pathlib import Path

import requests

SERVER_BASE = os.getenv("SERVER_BASE", "https://mishrabP-myblogs.hf.space")
REPO_ROOT = str(Path(__file__).parent.parent.parent)


# ---------------------------------------------------------------------------
# Static frontend audit tool  (SEO + ADA)
# ---------------------------------------------------------------------------

def check_frontend_static(root: str = "") -> str:
    """Audit the frontend source for SEO and ADA/WCAG AA requirements.

    Checks index.html, robots.txt, router, App.vue, Home.vue, Footer.vue,
    Navbar.vue, and BlogPost.vue against a known checklist.
    Returns a JSON report with passed/failed items.

    Args:
        root: Repo root path. Defaults to the myblogs project root.
    """
    base = Path(root or REPO_ROOT)
    passed: list[dict] = []
    failed: list[dict] = []

    def _read(rel: str) -> str:
        p = base / rel
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def ok(area: str, msg: str) -> None:
        passed.append({"area": area, "message": msg})

    def fail(area: str, severity: str, msg: str, detail: str = "") -> None:
        failed.append({"area": area, "severity": severity, "message": msg, "detail": detail})

    # ── index.html ───────────────────────────────────────────────────────────
    html = _read("frontend/index.html")
    if not html:
        fail("seo", "critical", "frontend/index.html not found")
    else:
        if re.search(r'<html[^>]+lang=["\']en["\']', html):
            ok("seo", "<html lang='en'> present")
        else:
            fail("seo", "high", "index.html missing lang='en' on <html>",
                 "Add lang=\"en\" to the <html> tag.")
        if re.search(r'<meta\s+name=["\']description["\']', html, re.I):
            ok("seo", "<meta name='description'> present")
        else:
            fail("seo", "high", "index.html missing <meta name='description'>",
                 "Add a concise site description meta tag.")
        for tag in ("og:title", "og:description", "og:type", "og:url"):
            if tag in html:
                ok("seo", f"Open Graph tag {tag} present")
            else:
                fail("seo", "medium", f"index.html missing Open Graph tag {tag}")
        for tag in ("twitter:card", "twitter:title"):
            if tag in html:
                ok("seo", f"Twitter Card tag {tag} present")
            else:
                fail("seo", "medium", f"index.html missing Twitter Card tag {tag}")
        if re.search(r'<meta\s+name=["\']viewport["\']', html, re.I):
            ok("seo", "<meta name='viewport'> present")
        else:
            fail("seo", "high", "index.html missing viewport meta tag")
        if re.search(r'<link\s+rel=["\']canonical["\']', html, re.I):
            ok("seo", "<link rel='canonical'> present")
        else:
            fail("seo", "medium", "index.html missing canonical link tag")

    # ── robots.txt ───────────────────────────────────────────────────────────
    robots = _read("frontend/public/robots.txt")
    if robots:
        if re.search(r"User-agent:\s*\*", robots) and "Allow:" in robots:
            ok("seo", "robots.txt present and allows crawling")
        else:
            fail("seo", "medium", "robots.txt may be blocking crawlers",
                 "Ensure 'User-agent: *' and 'Allow: /' are present.")
    else:
        fail("seo", "high", "frontend/public/robots.txt is missing",
             "Create robots.txt with 'User-agent: *\\nAllow: /'.")

    # ── router document.title ────────────────────────────────────────────────
    router = _read("frontend/src/router/index.js")
    if "afterEach" in router and "document.title" in router:
        ok("seo", "Router afterEach sets document.title per route")
    else:
        fail("seo", "high", "Router does not set document.title per route",
             "Add a router.afterEach hook that sets document.title from route.meta.title.")

    # ── App.vue skip link ────────────────────────────────────────────────────
    app = _read("frontend/src/App.vue")
    if "skip" in app.lower() and "#main-content" in app:
        ok("ada", "Skip-to-content link present in App.vue")
    else:
        fail("ada", "high", "App.vue missing skip-to-content link",
             "Add <a href='#main-content' class='sr-only focus:not-sr-only ...'>Skip to content</a>.")

    # ── Home.vue id=main-content ─────────────────────────────────────────────
    home = _read("frontend/src/views/Home.vue")
    main_ids = re.findall(r'id=["\']main-content["\']', home)
    if len(main_ids) >= 2:
        ok("ada", "id='main-content' present in both Home.vue layouts")
    elif len(main_ids) == 1:
        fail("ada", "medium", "id='main-content' only found once in Home.vue",
             "Both Layout A and Layout B sections need id='main-content'.")
    else:
        fail("ada", "high", "id='main-content' missing from Home.vue",
             "Add id='main-content' to the main content landmark in both layouts.")

    # ── Home.vue newsletter aria-labels ─────────────────────────────────────
    newsletter_labels = re.findall(r'aria-label=["\']Email address for newsletter["\']', home)
    if len(newsletter_labels) >= 2:
        ok("ada", "Newsletter inputs have aria-label in both Home.vue layouts")
    else:
        fail("ada", "medium", f"Newsletter email input missing aria-label (found {len(newsletter_labels)}/2)",
             "Both Layout A and Layout B newsletter inputs need aria-label='Email address for newsletter'.")

    # ── Navbar.vue mobile toggle ──────────────────────────────────────────────
    nav = _read("frontend/src/components/Navbar.vue")
    if "aria-label" in nav and "Toggle navigation" in nav:
        ok("ada", "Mobile nav toggle has aria-label")
    else:
        fail("ada", "high", "Navbar mobile toggle button missing aria-label",
             "Add aria-label='Toggle navigation' to the hamburger button.")
    if "aria-expanded" in nav:
        ok("ada", "Nav toggle has aria-expanded")
    else:
        fail("ada", "medium", "Navbar toggle missing :aria-expanded binding")

    # ── Footer.vue social links & heading levels ─────────────────────────────
    footer = _read("frontend/src/components/Footer.vue")
    for label in ("Follow Meridian on Twitter", "Follow Meridian on LinkedIn", "Follow Meridian on Instagram"):
        if label in footer:
            ok("ada", f"Footer social link has descriptive aria-label: {label}")
        else:
            fail("ada", "medium", f"Footer social link missing descriptive aria-label",
                 f"Expected aria-label like '{label}'.")
    if "<h3" in footer and "<h4" not in footer:
        ok("ada", "Footer section headings use h3 (not h4)")
    elif "<h4" in footer:
        fail("ada", "medium", "Footer uses h4 for section headings — should be h3",
             "Change <h4> to <h3> for Topics and Quick Links in Footer.vue.")

    # ── BlogPost.vue heading hierarchy ───────────────────────────────────────
    post = _read("frontend/src/views/BlogPost.vue")
    if re.search(r'<h2[^>]*>Photo Gallery', post):
        ok("ada", "BlogPost Photo Gallery uses h2 (not h3)")
    elif re.search(r'<h3[^>]*>Photo Gallery', post):
        fail("ada", "medium", "BlogPost Photo Gallery uses h3 — risks skipping h2 if post content has no headings",
             "Change to <h2> for guaranteed valid heading hierarchy.")

    # ── style.css focus-visible ──────────────────────────────────────────────
    css = _read("frontend/src/style.css")
    if ":focus-visible" in css:
        ok("ada", ":focus-visible outline rule present in style.css")
    else:
        fail("ada", "high", "style.css missing :focus-visible outline rule",
             "Add ':focus-visible { outline: 2px solid ...; outline-offset: 2px; }'.")

    # ── Maintenance agent workflow ───────────────────────────────────────────
    maint_wf = _read(".github/workflows/run-maintenance-agent.yml")
    if maint_wf and "FORCE_MAINTENANCE" in maint_wf:
        ok("dependabot", "Maintenance agent workflow present (handles Dependabot PRs)")
    else:
        fail("dependabot", "medium", ".github/workflows/run-maintenance-agent.yml missing or incomplete",
             "The maintenance agent workflow must exist and include FORCE_MAINTENANCE support.")

    return json.dumps({
        "checkedAt": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "passedCount": len(passed),
        "failedCount": len(failed),
        "passed": passed,
        "failed": failed,
    })

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
# Internal-link auditor
# ---------------------------------------------------------------------------


def check_internal_links(root: str = "") -> str:
    """Scan all Vue/JS frontend source files for internal navigation links whose
    paths don't match any route defined in frontend/src/router/index.js.

    Catches broken RouterLink to="..." and <a href="..."> destinations.
    Returns JSON: routesFound, filesScanned, brokenLinks, broken[{file, line, path}].

    Args:
        root: Repo root path. Defaults to the myblogs project root.
    """
    base = Path(root or REPO_ROOT)

    # ── 1. Parse router: collect valid absolute paths + parent→child mapping ──
    router_file = base / "frontend/src/router/index.js"
    router_text = router_file.read_text(encoding="utf-8") if router_file.exists() else ""

    valid_paths: set[str] = set()

    # Collect absolute paths (direct valid routes), excluding catch-all patterns
    abs_paths = [
        p for p in re.findall(r"\bpath:\s*['\"](/[^'\"]+)['\"]", router_text)
        if not re.search(r"[*().]", p)  # skip catch-all like /:pathMatch(.*)*
    ]
    valid_paths.update(abs_paths)

    # Resolve children: for each "children: [...]" block, find its nearest
    # preceding absolute-path parent and combine.
    segments = re.split(r"(children\s*:\s*\[)", router_text)
    accumulated = segments[0]
    for i in range(1, len(segments), 2):
        children_marker = segments[i]
        rest = segments[i + 1] if i + 1 < len(segments) else ""

        # Most-recent absolute path before this children block = parent
        parent_candidates = re.findall(r"\bpath:\s*['\"](/[^'\"]+)['\"]", accumulated)
        parent = parent_candidates[-1] if parent_candidates else None

        if parent:
            # Read content inside [ ... ] respecting bracket nesting
            depth = 1
            child_text: list[str] = []
            for ch in rest:
                if ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        break
                child_text.append(ch)

            child_block = "".join(child_text)
            for child in re.findall(r"\bpath:\s*['\"]([^'\"]+)['\"]", child_block):
                if child and not child.startswith("/") and not re.search(r"[*().]", child):
                    valid_paths.add(f"{parent.rstrip('/')}/{child}")

        accumulated += children_marker + rest

    def _route_to_regex(path: str) -> re.Pattern:
        parts = path.split("/")
        pats = ["[^/]+" if part.startswith(":") else re.escape(part) for part in parts]
        return re.compile("^" + "/".join(pats) + "$")

    route_regexes = [_route_to_regex(p) for p in valid_paths]

    def _is_valid(path: str) -> bool:
        path = path.split("?")[0].split("#")[0].rstrip("/") or "/"
        return any(rx.match(path) for rx in route_regexes)

    _IGNORE_PREFIXES = ("/api/", "/uploads/", "//")
    _SKIP = {"", "/", "#"}
    # Static assets are not SPA routes — ignore paths with file extensions
    _STATIC_EXTS = {".svg", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".ico",
                    ".css", ".js", ".json", ".txt", ".woff", ".woff2", ".ttf", ".xml"}

    # ── 2. Patterns to extract internal link paths from templates ─────────────
    #   to="/path"      — static RouterLink (unbound)
    #   to='/path'      — same, single-quoted
    #   :to="'/path'"   — bound but literal string value
    #   href="/path"    — anchor tag (non-external)
    _link_patterns = [
        re.compile(r'''\bto="(/[^"<>{}`\s]+)"'''),
        re.compile(r"""\bto='(/[^'<>{}`\s]+)'"""),
        re.compile(r""":to="'(/[^']+)'"''"""),
        re.compile(r'''\bhref="(/[^"<>\s]+)"'''),
        re.compile(r"""\bhref='(/[^'<>\s]+)'"""),
    ]

    # ── 3. Walk frontend/src Vue/JS files ─────────────────────────────────────
    src_dir = base / "frontend/src"
    vue_files = sorted(
        f for f in src_dir.rglob("*")
        if f.suffix in {".vue", ".js"} and "node_modules" not in f.parts
    )

    broken: list[dict] = []
    for vf in vue_files:
        try:
            lines = vf.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for lineno, line in enumerate(lines, 1):
            for pat in _link_patterns:
                for m in pat.finditer(line):
                    path = m.group(1)
                    if path in _SKIP:
                        continue
                    if any(path.startswith(pfx) for pfx in _IGNORE_PREFIXES):
                        continue
                    # Ignore static assets (have a file extension in the path)
                    bare = path.split("#")[0].split("?")[0]
                    if any(bare.lower().endswith(ext) for ext in _STATIC_EXTS):
                        continue
                    if not _is_valid(path):
                        broken.append({
                            "file": str(vf.relative_to(base)),
                            "line": lineno,
                            "path": path,
                        })

    return json.dumps({
        "routesFound": len(valid_paths),
        "filesScanned": len(vue_files),
        "brokenLinks": len(broken),
        "broken": broken,
    }, indent=2)


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

    Uses the SECRET_TOKEN_GITHUB environment variable for authentication.

    Args:
        owner: GitHub repository owner/org, e.g. 'bibhu2020'.
        repo: Repository name, e.g. 'myblogs'.
    """
    token = os.getenv("SECRET_TOKEN_GITHUB", "")
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


def merge_github_pr(owner: str, repo: str, pr_number: int, merge_method: str = "squash") -> str:
    """Merge a GitHub pull request via the GitHub API.

    Use this for Dependabot patch/minor PRs that are low-risk and mergeable.
    Requires SECRET_TOKEN_GITHUB with contents:write and pull-requests:write permissions.

    Args:
        owner: GitHub repository owner/org.
        repo: Repository name.
        pr_number: Pull request number to merge.
        merge_method: 'merge', 'squash', or 'rebase'. Defaults to 'squash'.
    """
    token = os.getenv("SECRET_TOKEN_GITHUB", "")
    if not token:
        return json.dumps({"success": False, "error": "SECRET_TOKEN_GITHUB not set — cannot merge PR"})
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        resp = requests.put(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/merge",
            headers=headers,
            json={
                "merge_method": merge_method,
                "commit_title": f"chore(deps): merge Dependabot PR #{pr_number} [{merge_method}]",
            },
            timeout=30,
        )
        data = resp.json() if resp.content else {}
        if resp.status_code == 200:
            return json.dumps({"success": True, "sha": data.get("sha"), "message": data.get("message", "Merged")})
        return json.dumps({
            "success": False,
            "status": resp.status_code,
            "error": data.get("message", resp.text[:300]),
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def close_github_pr(owner: str, repo: str, pr_number: int, reason: str = "") -> str:
    """Close a GitHub pull request without merging, optionally posting a reason comment.

    Use this for Dependabot major-version PRs that require human review before merging.

    Args:
        owner: GitHub repository owner/org.
        repo: Repository name.
        pr_number: Pull request number to close.
        reason: Optional explanation to post as a comment before closing.
    """
    token = os.getenv("SECRET_TOKEN_GITHUB", "")
    if not token:
        return json.dumps({"success": False, "error": "SECRET_TOKEN_GITHUB not set — cannot close PR"})
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        comment_body = f"🤖 Maintenance agent: {reason}" if reason else "🤖 Maintenance agent: closing this PR."
        # Always post the comment first (issues:write is usually available)
        comment_resp = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments",
            headers=headers,
            json={"body": comment_body},
            timeout=30,
        )
        commented = comment_resp.status_code == 201

        # Attempt to close the PR (requires pull-requests:write scope)
        resp = requests.patch(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
            headers=headers,
            json={"state": "closed"},
            timeout=30,
        )
        data = resp.json() if resp.content else {}
        if resp.status_code == 200:
            return json.dumps({"success": True, "message": f"PR #{pr_number} closed"})
        if resp.status_code == 403:
            # Token lacks pull-requests:write — comment was posted as a warning instead
            return json.dumps({
                "success": False,
                "partial": True,
                "commented": commented,
                "error": (
                    "Token lacks pull-requests:write — PR left open. "
                    f"Comment {'posted' if commented else 'failed'}: {comment_body}"
                ),
            })
        return json.dumps({
            "success": False,
            "status": resp.status_code,
            "error": data.get("message", resp.text[:300]),
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def get_pr_details(owner: str, repo: str, pr_number: int) -> str:
    """Get details of a specific GitHub PR including files changed.

    Uses the SECRET_TOKEN_GITHUB environment variable for authentication.

    Args:
        owner: GitHub repository owner/org.
        repo: Repository name.
        pr_number: Pull request number.
    """
    token = os.getenv("SECRET_TOKEN_GITHUB", "")
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

        # Determine semver bump from title.
        # Handles both npm format ("from 10.2.0 to 11.0.2")
        # and Python format ("from >=21.0 to >=26" or "from >=0.4 to >=0.5.1")
        bump = "unknown"
        # (?:>=?)? makes the ">=" prefix optional so both npm ("from 4.0 to 5.0")
        # and Python requirements ("from >=4.0 to >=5.0") are handled.
        m = re.search(
            r"from\s+(?:>=?)?(\d+)\.(\d+)(?:\.(\d+))?\s+to\s+(?:>=?)?(\d+)\.(\d+)(?:\.(\d+))?",
            pr.get("title", ""),
        )
        if m:
            old_maj, old_min = int(m.group(1)), int(m.group(2))
            new_maj, new_min = int(m.group(4)), int(m.group(5))
            if new_maj > old_maj:
                bump = "major"
            elif new_min > old_min:
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


# ---------------------------------------------------------------------------
# CodePatcher tools
# ---------------------------------------------------------------------------


def apply_file_patch(file_path: str, old_string: str, new_string: str) -> str:
    """Apply a surgical text replacement to a source file in the myblogs project.

    The old_string must appear exactly once in the file. Changes are written in-place.
    Always call read_source_file first to see the exact current content before patching.

    Args:
        file_path: File path relative to /home/azure/myblogs/ (e.g. 'frontend/index.html').
        old_string: Exact text to replace — must appear exactly once in the file.
        new_string: Replacement text. Can be empty string to delete the old_string.
    """
    full_path = (Path(REPO_ROOT) / file_path.lstrip("/")).resolve()
    repo_path = Path(REPO_ROOT).resolve()
    if not str(full_path).startswith(str(repo_path) + "/"):
        return json.dumps({"success": False, "error": "Path traversal rejected — must be within repo root"})
    if not full_path.exists():
        return json.dumps({"success": False, "error": f"File not found: {file_path}"})
    try:
        content = full_path.read_text(encoding="utf-8")
        count = content.count(old_string)
        if count == 0:
            return json.dumps({
                "success": False,
                "error": f"old_string not found in {file_path}. Use read_source_file to verify exact content.",
            })
        if count > 1:
            return json.dumps({
                "success": False,
                "error": (
                    f"old_string found {count} times in {file_path} — must be unique. "
                    "Add more surrounding context to make it unambiguous."
                ),
            })
        full_path.write_text(content.replace(old_string, new_string, 1), encoding="utf-8")
        return json.dumps({"success": True, "file": file_path, "message": f"Replaced 1 occurrence in {file_path}"})
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def revert_file(file_path: str) -> str:
    """Revert a specific file to its last committed state (git checkout HEAD -- <file>).

    Use this to undo a patch that caused a build failure before retrying with a corrected patch.

    Args:
        file_path: File path relative to /home/azure/myblogs/ (e.g. 'frontend/index.html').
    """
    full_path = (Path(REPO_ROOT) / file_path.lstrip("/")).resolve()
    if not str(full_path).startswith(str(Path(REPO_ROOT).resolve()) + "/"):
        return json.dumps({"success": False, "error": "Path traversal rejected"})
    try:
        result = subprocess.run(
            ["git", "checkout", "HEAD", "--", file_path],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return json.dumps({"success": True, "message": f"Reverted {file_path} to HEAD"})
        return json.dumps({"success": False, "error": result.stderr or result.stdout})
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


# ---------------------------------------------------------------------------
# BuildValidator tools
# ---------------------------------------------------------------------------


def build_nodejs_service(service: str) -> str:
    """Run 'npm ci' then 'npm run build' for a specific Node.js / NestJS service.

    Uses 'npm ci' (same as the production Dockerfile) so peer-dependency
    conflicts that would break the Hugging Face build are caught here first.
    If 'npm ci' fails due to a missing or out-of-sync lock file the tool falls
    back to 'npm install' and regenerates the lock file automatically.

    Args:
        service: One of 'frontend', 'api-gateway', 'auth-service',
                 'blog-service', 'media-service'.
    """
    import shutil, time

    allowed = {"frontend", "api-gateway", "auth-service", "blog-service", "media-service"}
    if service not in allowed:
        return json.dumps({"error": f"Unknown service '{service}'. Valid: {sorted(allowed)}"})
    if not shutil.which("npm"):
        return json.dumps({"service": service, "verdict": "BUILD SKIPPED",
                           "message": "npm not available in this environment"})
    service_dir = os.path.join(REPO_ROOT, service)
    if not os.path.isdir(service_dir):
        return json.dumps({"service": service, "verdict": "BUILD SKIPPED",
                           "message": f"Directory not found: {service_dir}"})
    try:
        t0 = time.time()
        # Use npm ci (strict, matches Dockerfile) to catch peer-dep conflicts.
        # Fall back to npm install only when package-lock.json is absent/stale.
        lock_file = os.path.join(service_dir, "package-lock.json")
        if os.path.exists(lock_file):
            install = subprocess.run(
                ["npm", "ci"],
                cwd=service_dir, capture_output=True, text=True, timeout=300,
            )
        else:
            install = subprocess.run(
                ["npm", "install"],
                cwd=service_dir, capture_output=True, text=True, timeout=300,
            )
        if install.returncode != 0:
            return json.dumps({
                "service": service, "success": False, "verdict": "BUILD FAILED",
                "error": f"npm ci failed (peer-dep conflict or lock mismatch):\n{install.stderr[-2000:]}",
            })
        # Build
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=service_dir, capture_output=True, text=True, timeout=300,
        )
        elapsed = round(time.time() - t0, 1)
        success = result.returncode == 0
        return json.dumps({
            "service": service,
            "success": success,
            "returnCode": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
            "durationSeconds": elapsed,
            "verdict": "BUILD PASSED" if success else "BUILD FAILED",
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"service": service, "success": False,
                           "verdict": "BUILD FAILED", "error": "Timed out after 300s"})
    except Exception as exc:
        return json.dumps({"service": service, "success": False,
                           "verdict": "BUILD FAILED", "error": str(exc)})


def check_python_syntax() -> str:
    """Check Python syntax for every .py file under meridian_agents/.

    Uses py_compile (no imports executed) to detect syntax errors without
    running the modules.  Returns a JSON report listing any bad files.
    """
    import py_compile

    agents_dir = os.path.join(REPO_ROOT, "meridian_agents")
    errors: list[dict] = []
    checked = 0

    for root, dirs, files in os.walk(agents_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".venv", "node_modules")]
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, REPO_ROOT)
            checked += 1
            try:
                py_compile.compile(fpath, doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append({"file": rel, "error": str(exc)})

    return json.dumps({
        "checked": checked,
        "errorCount": len(errors),
        "errors": errors,
        "verdict": "SYNTAX OK" if not errors else "SYNTAX ERRORS FOUND",
    })


def install_frontend_deps() -> str:
    """Run npm install in the frontend directory to sync dependencies after package.json changes.

    Call this before run_frontend_build() whenever package.json or package-lock.json may
    have been updated (e.g. after Dependabot PRs were merged).
    Returns JSON with success (bool) and output/error strings.
    """
    import shutil
    if not shutil.which("npm"):
        return json.dumps({"success": False, "verdict": "SKIPPED",
                           "message": "npm not available — dependency install skipped"})
    frontend_dir = os.path.join(REPO_ROOT, "frontend")
    try:
        result = subprocess.run(
            ["npm", "install", "--prefer-offline"],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return json.dumps({
            "success": result.returncode == 0,
            "returnCode": result.returncode,
            "output": result.stdout[-2000:] if result.stdout else "",
            "error": result.stderr[-1000:] if result.returncode != 0 else "",
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"success": False, "error": "npm install timed out after 300s"})
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def run_frontend_build() -> str:
    """Run the Vite frontend build (npm run build) to verify the frontend compiles without errors.

    Returns JSON with: success (bool), returnCode, stdout (last 3000 chars),
    stderr (last 2000 chars), durationSeconds, and verdict:
      'BUILD PASSED'  — returnCode 0 (chunk-size warnings are NOT failures)
      'BUILD FAILED'  — returnCode != 0
      'BUILD SKIPPED' — npm not available in this environment
    """
    import shutil, time
    if not shutil.which("npm"):
        return json.dumps({"success": False, "verdict": "BUILD SKIPPED",
                           "message": "npm not available in this environment — build check skipped"})
    frontend_dir = os.path.join(REPO_ROOT, "frontend")
    try:
        t0 = time.time()
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        elapsed = round(time.time() - t0, 1)
        success = result.returncode == 0
        return json.dumps({
            "success": success,
            "returnCode": result.returncode,
            "stdout": result.stdout[-3000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
            "durationSeconds": elapsed,
            "verdict": "BUILD PASSED" if success else "BUILD FAILED",
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"success": False, "error": "Build timed out after 300s", "verdict": "BUILD FAILED"})
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc), "verdict": "BUILD FAILED"})


def git_diff_changes() -> str:
    """Show all changes (staged and unstaged) relative to HEAD in the myblogs repository.

    Returns a unified diff so the team can review exactly what code has been modified.
    Output is truncated at 15000 characters if the diff is very large.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        diff = result.stdout
        if not diff.strip():
            return json.dumps({"diff": "", "message": "No changes compared to HEAD — working tree is clean"})
        if len(diff) > 15000:
            diff = diff[:15000] + "\n... (truncated at 15000 chars)"
        return json.dumps({"diff": diff, "charCount": len(result.stdout)})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# GitPublisher tools
# ---------------------------------------------------------------------------


def git_status_short() -> str:
    """Get the short git status showing which files are modified, staged, or untracked."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.dumps({
            "output": result.stdout.strip() or "(working tree clean)",
            "returnCode": result.returncode,
        })
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def git_pull_rebase() -> str:
    """Pull and rebase the local branch on top of the remote, then report the result.

    Call this before committing SEO/ADA fixes in case Dependabot PR merges have
    added new commits to the remote main branch since the agent started.
    Safe to call even when the working tree has uncommitted changes — git will
    stash, pull, rebase, and pop automatically via git pull --rebase.
    """
    try:
        result = subprocess.run(
            ["git", "pull", "--rebase", "origin", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return json.dumps({
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip() if result.returncode != 0 else "",
            "message": "Rebased on remote HEAD" if result.returncode == 0 else "git pull --rebase failed",
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def git_commit_and_push(message: str) -> str:
    """Stage all modified tracked files (git add -u), commit with message, and push to origin.

    Only stages files already tracked by git that were modified — never adds new untracked files.
    IMPORTANT: Only call this after BuildValidator has confirmed BUILD PASSED in this session.

    Args:
        message: Commit message. Should start with 'maint: ' prefix, e.g.
                 'maint: fix aria-labels and OG meta tags (monthly maintenance)'.
    """
    try:
        # Check for changes
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
        )
        if not status.stdout.strip():
            return json.dumps({"success": False, "message": "Nothing to commit — working tree is clean"})

        # Stage only modified tracked files
        add = subprocess.run(
            ["git", "add", "-u"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
        )
        if add.returncode != 0:
            return json.dumps({"success": False, "error": f"git add -u failed: {add.stderr}"})

        # Commit
        commit = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
        )
        if commit.returncode != 0:
            return json.dumps({"success": False, "error": f"git commit failed: {commit.stderr or commit.stdout}"})

        # Push
        push = subprocess.run(
            ["git", "push", "origin", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
        )
        push_ok = push.returncode == 0
        return json.dumps({
            "success": push_ok,
            "commitOutput": commit.stdout.strip(),
            "pushOutput": push.stdout.strip() if push_ok else "",
            "pushError": push.stderr.strip() if not push_ok else "",
            "message": "Changes committed and pushed to GitHub" if push_ok
                       else f"Committed but push failed: {push.stderr[:400]}",
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


# ---------------------------------------------------------------------------
# Branch / PR workflow tools  (used by all fix agents)
# ---------------------------------------------------------------------------


def get_github_repo() -> str:
    """Return the GitHub owner and repo from the GITHUB_REPO env var (format: 'owner/repo').

    Returns JSON with 'owner', 'repo', and 'full' keys.
    """
    repo_str = os.getenv("GITHUB_REPO", "")
    if not repo_str or "/" not in repo_str:
        return json.dumps({"error": "GITHUB_REPO not set or invalid (expected 'owner/repo')",
                           "owner": "", "repo": "", "full": ""})
    owner, repo_name = repo_str.split("/", 1)
    return json.dumps({"owner": owner, "repo": repo_name, "full": repo_str})


def get_current_branch() -> str:
    """Return the name of the currently checked-out git branch."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=15,
        )
        return json.dumps({"branch": result.stdout.strip(), "success": result.returncode == 0})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def git_checkout_branch(branch_name: str, create_from_main: bool = False) -> str:
    """Check out a branch, optionally creating it fresh from the latest main.

    When create_from_main=True:
      1. Stashes any uncommitted changes.
      2. Switches to main and pulls latest from origin.
      3. Creates and checks out the new branch.

    Args:
        branch_name: Branch to switch to or create.
        create_from_main: If True, sync main first then create the branch.
    """
    try:
        if create_from_main:
            subprocess.run(["git", "stash"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
            co = subprocess.run(
                ["git", "checkout", "main"],
                cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
            )
            if co.returncode != 0:
                return json.dumps({"success": False, "error": f"git checkout main failed: {co.stderr}"})
            subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
            )
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
            )
        else:
            result = subprocess.run(
                ["git", "checkout", branch_name],
                cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
            )
        return json.dumps({
            "success": result.returncode == 0,
            "branch": branch_name,
            "output": (result.stdout or result.stderr).strip(),
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def git_pull_main() -> str:
    """Switch to main and pull latest changes from origin.

    Stashes any uncommitted changes first so the switch is safe.
    """
    try:
        subprocess.run(["git", "stash"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
        subprocess.run(["git", "checkout", "main"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
        )
        return json.dumps({
            "success": result.returncode == 0,
            "output": result.stdout.strip() or result.stderr.strip(),
            "message": "main synced with origin" if result.returncode == 0 else "git pull failed",
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def git_stage_and_commit(message: str) -> str:
    """Stage all modified and new files (git add -A) and commit on the current branch.

    Args:
        message: Commit message.
    """
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
        )
        if not status.stdout.strip():
            return json.dumps({"success": False, "message": "Nothing to commit — working tree is clean"})

        add = subprocess.run(
            ["git", "add", "-A"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
        )
        if add.returncode != 0:
            return json.dumps({"success": False, "error": f"git add failed: {add.stderr}"})

        commit = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
        )
        return json.dumps({
            "success": commit.returncode == 0,
            "output": commit.stdout.strip(),
            "error": commit.stderr.strip() if commit.returncode != 0 else "",
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def git_push_current_branch() -> str:
    """Push the currently checked-out branch to origin (sets --set-upstream automatically)."""
    try:
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=15,
        )
        branch = branch_result.stdout.strip()
        push = subprocess.run(
            ["git", "push", "--set-upstream", "origin", branch],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
        )
        return json.dumps({
            "success": push.returncode == 0,
            "branch": branch,
            "output": push.stdout.strip() if push.returncode == 0 else push.stderr.strip(),
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def create_github_pr(owner: str, repo: str, title: str, body: str,
                     head_branch: str, base_branch: str = "main") -> str:
    """Create a GitHub pull request from head_branch into base_branch.

    Requires SECRET_TOKEN_GITHUB with pull-requests:write permission.

    Args:
        owner: GitHub owner/org.
        repo: Repository name.
        title: PR title.
        body: PR description body.
        head_branch: Source branch containing the changes.
        base_branch: Target branch to merge into (default: 'main').
    """
    token = os.getenv("SECRET_TOKEN_GITHUB", "")
    if not token:
        return json.dumps({"success": False, "error": "SECRET_TOKEN_GITHUB not set"})
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        resp = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            headers=headers,
            json={"title": title, "body": body, "head": head_branch, "base": base_branch},
            timeout=30,
        )
        data = resp.json() if resp.content else {}
        if resp.status_code == 201:
            return json.dumps({
                "success": True,
                "pr_number": data["number"],
                "url": data["html_url"],
                "message": f"PR #{data['number']} created: {data['html_url']}",
            })
        return json.dumps({
            "success": False,
            "status": resp.status_code,
            "error": data.get("message", resp.text[:300]),
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def delete_github_branch(owner: str, repo: str, branch_name: str) -> str:
    """Delete a remote branch — call after a PR is merged to clean up.

    Args:
        owner: GitHub owner/org.
        repo: Repository name.
        branch_name: Branch to delete.
    """
    token = os.getenv("SECRET_TOKEN_GITHUB", "")
    if not token:
        return json.dumps({"success": False, "error": "SECRET_TOKEN_GITHUB not set"})
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        resp = requests.delete(
            f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch_name}",
            headers=headers,
            timeout=30,
        )
        return json.dumps({
            "success": resp.status_code == 204,
            "branch": branch_name,
            "message": "Branch deleted" if resp.status_code == 204 else f"HTTP {resp.status_code}",
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


# ---------------------------------------------------------------------------
# Sitemap tools
# ---------------------------------------------------------------------------


def generate_sitemap() -> str:
    """Generate/update frontend/public/sitemap.xml.

    Reads public routes from the Vue router config, then fetches published posts
    and stories from the Meridian API to build a complete sitemap.xml.
    """
    base = SERVER_BASE.rstrip("/")
    sitemap_path = Path(REPO_ROOT) / "frontend/public/sitemap.xml"

    # Known static public routes
    static_paths = ["/", "/news", "/stories"]

    # Parse Vue router for additional static (non-dynamic) public routes
    router_file = Path(REPO_ROOT) / "frontend/src/router/index.js"
    if router_file.exists():
        content = router_file.read_text(encoding="utf-8")
        for path in re.findall(r"path:\s*['\"]([^'\"*]+)['\"]", content):
            if (
                path
                and ":" not in path          # skip :slug / :id segments
                and "admin" not in path
                and "login" not in path
                and path not in static_paths
            ):
                static_paths.append(path)

    urls: list[str] = [base + p for p in static_paths]

    # Dynamic: published blog posts
    try:
        resp = requests.get(f"{base}/api/posts?limit=500", timeout=20)
        if resp.ok:
            data = resp.json()
            posts = data.get("posts", data) if isinstance(data, dict) else data
            for p in (posts if isinstance(posts, list) else []):
                if p.get("slug") and p.get("status") == "published":
                    urls.append(f"{base}/post/{p['slug']}")
    except Exception:
        pass

    # Dynamic: stories
    try:
        resp = requests.get(f"{base}/api/stories?limit=500", timeout=20)
        if resp.ok:
            stories = resp.json()
            for s in (stories if isinstance(stories, list) else []):
                if s.get("id"):
                    urls.append(f"{base}/story/{s['id']}")
    except Exception:
        pass

    # Deduplicate while preserving order
    urls = list(dict.fromkeys(urls))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in urls:
        lines.append(f"  <url><loc>{url}</loc></url>")
    lines.append("</urlset>")

    sitemap_path.parent.mkdir(parents=True, exist_ok=True)
    sitemap_path.write_text("\n".join(lines), encoding="utf-8")

    return json.dumps({
        "success": True,
        "urlCount": len(urls),
        "path": "frontend/public/sitemap.xml",
        "urls": urls,
    })


def get_sitemap_urls() -> str:
    """Read frontend/public/sitemap.xml and return all URLs listed in it."""
    sitemap_path = Path(REPO_ROOT) / "frontend/public/sitemap.xml"
    if not sitemap_path.exists():
        return json.dumps({"exists": False, "count": 0, "urls": [],
                           "message": "sitemap.xml not found at frontend/public/sitemap.xml"})
    try:
        content = sitemap_path.read_text(encoding="utf-8")
        urls = re.findall(r"<loc>([^<]+)</loc>", content)
        return json.dumps({"exists": True, "count": len(urls), "urls": urls})
    except Exception as exc:
        return json.dumps({"error": str(exc), "urls": []})


def check_url_status(url: str) -> str:
    """Check the HTTP status of a URL.

    For Vue SPA dynamic routes (/post/:slug, /story/:id) the underlying API
    endpoint is checked because the SPA shell always returns 200.

    Args:
        url: Full URL to check (e.g. 'https://example.com/post/my-slug').
    """
    api_url = url
    base = SERVER_BASE.rstrip("/")
    if "/post/" in url:
        slug = url.split("/post/", 1)[1].rstrip("/")
        api_url = f"{base}/api/posts/{slug}"
    elif "/story/" in url:
        story_id = url.split("/story/", 1)[1].rstrip("/")
        api_url = f"{base}/api/stories/{story_id}"

    try:
        resp = requests.get(api_url, timeout=15, allow_redirects=True)
        return json.dumps({
            "url": url,
            "checkedUrl": api_url,
            "status": resp.status_code,
            "ok": resp.status_code < 400,
            "is404": resp.status_code == 404,
        })
    except Exception as exc:
        return json.dumps({"url": url, "checkedUrl": api_url,
                           "error": str(exc), "ok": False, "is404": False})
