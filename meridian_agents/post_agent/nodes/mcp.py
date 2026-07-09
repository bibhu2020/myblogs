import json
import os
import re

import httpx

from ...auth import make_agent_jwt
from ..state import AgentState

MCP_URL = os.getenv("MCP_URL", "https://mishrabp-meridian.hf.space/api/mcp")
MCP_KEY = os.getenv("MCP_API_KEY", "")

_req_id = 0


def _mcp_request(method: str, params: dict | None = None) -> dict:
    global _req_id
    _req_id += 1
    body: dict = {"jsonrpc": "2.0", "id": _req_id, "method": method}
    if params:
        body["params"] = params
    headers = {"Content-Type": "application/json"}
    if MCP_KEY:
        headers["Authorization"] = f"Bearer {MCP_KEY}"
    with httpx.Client(timeout=30.0) as client:
        res = client.post(MCP_URL, json=body, headers=headers)
        res.raise_for_status()
        data = res.json()
    if "error" in data:
        raise RuntimeError(f"MCP error [{data['error']['code']}]: {data['error']['message']}")
    return data["result"]


def mcp_call(tool_name: str, args: dict):
    result = _mcp_request("tools/call", {"name": tool_name, "arguments": args})
    if result.get("isError"):
        msg = (result.get("content") or [{}])[0].get("text", "Unknown tool error")
        raise RuntimeError(f'Tool "{tool_name}" failed: {msg}')
    text = (result.get("content") or [{}])[0].get("text")
    if text is None:
        raise RuntimeError(f'Tool "{tool_name}" returned no content')
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _parse_mcp_items(data) -> list[dict]:
    if isinstance(data, list):
        return data
    results = []
    for line in str(data).split("\n"):
        m = re.match(r"\s*ID:\s*(\d+)\s*\|\s*Name:\s*([^|]+?)\s*\|\s*Slug:\s*(\S+)", line)
        if m:
            results.append({"id": int(m.group(1)), "name": m.group(2).strip(), "slug": m.group(3).strip()})
    return results


# ── LangGraph nodes ──────────────────────────────────────────────────────────

def init_mcp_node(state: AgentState) -> dict:
    print(f"🔌 Connecting to MCP: {MCP_URL}")
    _mcp_request("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "meridian-ai-agent", "version": "2.0.0"},
    })
    print("✅ MCP ready\n")
    return {}


def ensure_author_node(state: AgentState) -> dict:
    name = state["author_name"]
    print(f'👤 Ensuring guest author "{name}"...')
    try:
        mcp_call("manage_guest_user", {
            "action": "create",
            "email": state["author_email"],
            "name": name,
            "password": state["author_password"],
            "bio": (
                "AI-powered research journalist covering the latest breakthroughs in artificial "
                "intelligence, machine learning, and emerging technologies. Each post is grounded "
                "in live web research and expert analysis."
            ),
        })
        print(f"✅ Guest author created: {name}")
    except Exception as err:
        msg = str(err).lower()
        if any(k in msg for k in ("already", "duplicate", "exists", "conflict")):
            print(f"✅ Guest author already exists: {name}")
        else:
            print(f"⚠️  Could not create guest author ({err}) — using name as display")
    return {}


def _create_category(server_base: str, name: str) -> dict | None:
    """Create a missing fixed category (Technology/Educational/History) via a direct
    REST call, self-signing an admin JWT — no MCP tool exists for category creation."""
    try:
        jwt = make_agent_jwt()
        with httpx.Client(timeout=15.0) as client:
            res = client.post(
                f"{server_base}/api/categories",
                json={"name": name},
                headers={"Authorization": f"Bearer {jwt}"},
            )
            res.raise_for_status()
            cat = res.json()
            print(f"🆕 Created missing category: {name} (ID: {cat.get('id')})")
            return cat
    except Exception as exc:
        print(f"⚠️  Could not create category '{name}': {exc}")
        return None


def pick_taxonomy_node(state: AgentState) -> dict:
    raw_cats = mcp_call("list_categories", {})
    raw_tags = mcp_call("list_tags", {})

    categories = _parse_mcp_items(raw_cats)
    tags = _parse_mcp_items(raw_tags)

    # ── Category matching ─────────────────────────────────────────────────────
    # category_name is one of the 3 fixed categories (Technology/Educational/History) —
    # match it exactly first, creating it if it doesn't exist yet, rather
    # than fuzzy-matching keywords against whatever happens to be in the DB.
    category_id = None
    matched_cat = None
    category_name = state.get("category_name", "")

    if category_name:
        matched_cat = next(
            (c for c in categories if c["name"].lower() == category_name.lower()),
            None,
        )
        if not matched_cat:
            created = _create_category(state.get("server_base", ""), category_name)
            if created:
                matched_cat = created
                categories.append(created)

    if not matched_cat and categories:
        kws = [k.lower() for k in state["post_category_keywords"]]
        cat_name_kw = category_name.lower()
        all_kws = list({cat_name_kw} | set(kws)) if cat_name_kw else kws
        matched_cat = next(
            (c for c in categories
             if any(k in c["name"].lower() or k in c["slug"].lower() for k in all_kws)),
            None,
        )

    if matched_cat:
        category_id = matched_cat["id"]
    elif categories:
        category_id = categories[0]["id"]

    # ── Tag matching ──────────────────────────────────────────────────────────
    tag_ids: list[int] = []
    if tags:
        # Normalise: lowercase, replace hyphens/underscores with spaces,
        # then also expand each multi-word keyword into individual words so
        # "software-development" matches "Software Engineering" via "software".
        raw_kws = [k.lower().replace("-", " ").replace("_", " ")
                   for k in state["post_tag_keywords"]]
        expanded: list[str] = []
        for kw in raw_kws:
            expanded.append(kw)
            expanded.extend(w for w in kw.split() if len(w) > 3)  # skip short stop-words
        kws = list(dict.fromkeys(expanded))  # deduplicate, preserve order

        def _tag_matches(t: dict) -> bool:
            name = t["name"].lower()
            slug = t.get("slug", "").lower()
            return any(k in name or k in slug for k in kws)

        matched = [t for t in tags if _tag_matches(t)]
        tag_ids = [t["id"] for t in matched[:6]]

        # Pad to 3 only with tags that relate to the category — never with random low-ID tags
        if len(tag_ids) < 3 and matched_cat:
            cat_words = matched_cat["name"].lower().split()
            cat_pool = [
                t for t in tags
                if t["id"] not in tag_ids
                and any(w in t["name"].lower() or w in t["slug"].lower() for w in cat_words)
            ]
            extras = [t["id"] for t in cat_pool][: 3 - len(tag_ids)]
            tag_ids.extend(extras)

    cat_kws = state.get("post_category_keywords", [])
    tag_kws = state.get("post_tag_keywords", [])
    print(f"🏷️  Writer cat-kws={cat_kws} | tag-kws={tag_kws[:5]}")
    print(f"🏷️  Category ID: {category_id} | Tag IDs: {tag_ids}")
    return {"category_id": category_id, "tag_ids": tag_ids}


def _extract_slug_id(raw) -> tuple[str | None, int | None]:
    if isinstance(raw, dict):
        return raw.get("slug"), raw.get("id")
    text = str(raw)
    m_slug = re.search(r"Slug:\s*(\S+)", text)
    m_id = re.search(r"ID:\s*(\d+)", text)
    return (m_slug.group(1) if m_slug else None,
            int(m_id.group(1)) if m_id else None)


def save_pending_node(state: AgentState) -> dict:
    """Save the generated post to the blog with status='pending'.

    The post will not be visible to readers until an admin approves it
    via the admin panel at /admin/posts (Pending Approval tab).
    """
    print("\n⏸️  Saving post as PENDING (awaiting admin approval)...")
    args: dict = {
        "title": state["post_title"],
        "content": state["final_content"],
        "excerpt": state["post_excerpt"],
        "status": "pending",
        "author_name": state["author_name"],
    }
    if state.get("category_id") is not None:
        args["category_id"] = state["category_id"]
    if state.get("tag_ids"):
        args["tag_ids"] = state["tag_ids"]
    if state.get("featured_image_url"):
        args["featured_image"] = state["featured_image_url"]
    # audio_url is intentionally NOT set here — narration is generated and attached by
    # generate_audio_node/attach_audio_node *after* this save, since the mp3 filename is
    # named deterministically from the post id this call returns (post_<id>.mp3).
    # resolve_curriculum_node stashes series_key/series_index on EVERY run (it doesn't yet
    # know which category the weighted pick will land on) — only persist them onto the post
    # when this run's post actually is Educational, so Technology/History posts never get a
    # stray series tag.
    if state.get("category_name") == "Educational" and state.get("series_key") is not None:
        args["series_key"] = state["series_key"]
        args["series_index"] = state["series_index"]

    raw = mcp_call("create_blog", args)
    slug, post_id = _extract_slug_id(raw)

    print(f"✅ Pending post saved — ID: {post_id}, slug: {slug}")
    return {"pending_post_id": post_id, "pending_post_slug": slug,
            "approved": None, "published_slug": None, "published_id": None}


def attach_audio_node(state: AgentState) -> dict:
    """Attach the narration mp3 (generated after save_pending_node, once the post id is
    known — see nodes/audio.py) to the just-created post via a direct PUT, mirroring
    _create_category's precedent of bypassing MCP for deterministic, non-LLM-driven
    steps. No-op if audio generation failed or was skipped."""
    audio_url = state.get("audio_url")
    post_id = state.get("pending_post_id")
    if not audio_url or not post_id:
        return {}

    server_base = state.get("server_base", "")
    try:
        jwt = make_agent_jwt()
        with httpx.Client(timeout=15.0) as client:
            res = client.put(
                f"{server_base}/api/posts/{post_id}",
                json={"audioUrl": audio_url},
                headers={"Authorization": f"Bearer {jwt}"},
            )
            res.raise_for_status()
        print(f"✅ Narration attached to post #{post_id}")
    except Exception as exc:
        print(f"⚠️  Could not attach narration to post #{post_id}: {exc}")
    return {}


def publish_approved_node(state: AgentState) -> dict:
    """Publish an already-saved pending post after admin approval.

    Called by the resume flow: reads pending_post_id from state and
    updates the post status to 'published' via the blog API.
    """
    import httpx
    post_id = state.get("pending_post_id")
    if not post_id:
        print("⚠️  No pending_post_id in state — nothing to publish.")
        return {}

    server_base = state.get("server_base", "")
    token = os.getenv("AGENT_JWT_TOKEN", "")

    print(f"\n📡 Publishing approved post #{post_id}...")
    try:
        with httpx.Client(timeout=15) as client:
            r = client.patch(
                f"{server_base}/api/posts/{post_id}/approve",
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
    except Exception as exc:
        print(f"⚠️  Could not auto-publish via API ({exc}). Admin can approve manually.")
        return {"published_slug": state.get("pending_post_slug"),
                "published_id": post_id}

    slug = state.get("pending_post_slug")
    print(f"✅ Post published — ID: {post_id}, slug: {slug}")
    return {"published_slug": slug, "published_id": post_id}
