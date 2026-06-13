import json
import os
import re

import httpx

from ..state import AgentState

MCP_URL = os.getenv("MCP_URL", "https://mishrabp-myblogs.hf.space/api/mcp")
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


def pick_taxonomy_node(state: AgentState) -> dict:
    raw_cats = mcp_call("list_categories", {})
    raw_tags = mcp_call("list_tags", {})

    categories = _parse_mcp_items(raw_cats)
    tags = _parse_mcp_items(raw_tags)

    category_id = None
    if categories:
        kws = [k.lower() for k in state["post_category_keywords"]]
        match = next(
            (c for c in categories
             if any(k in c["name"].lower() or k in c["slug"].lower() for k in kws)),
            None,
        )
        category_id = (match or categories[0])["id"]

    tag_ids: list[int] = []
    if tags:
        kws = [k.lower() for k in state["post_tag_keywords"]]
        matched = [t for t in tags
                   if any(k in t["name"].lower() or k in t["slug"].lower() for k in kws)]
        tag_ids = [t["id"] for t in matched[:6]]
        if len(tag_ids) < 3:
            extras = [t["id"] for t in tags if t["id"] not in tag_ids][: 3 - len(tag_ids)]
            tag_ids.extend(extras)

    print(f"🏷️  Category ID: {category_id} | Tag IDs: {tag_ids}")
    return {"category_id": category_id, "tag_ids": tag_ids}


def publish_post_node(state: AgentState) -> dict:
    print("\n📡 Publishing post via MCP...")
    args: dict = {
        "title": state["post_title"],
        "content": state["final_content"],
        "excerpt": state["post_excerpt"],
        "status": "published",
        "author_name": state["author_name"],
    }
    if state.get("category_id") is not None:
        args["category_id"] = state["category_id"]
    if state.get("tag_ids"):
        args["tag_ids"] = state["tag_ids"]
    if state.get("featured_image_url"):
        args["featured_image"] = state["featured_image_url"]

    raw = mcp_call("create_blog", args)
    slug, post_id = None, None
    if isinstance(raw, dict):
        slug = raw.get("slug")
        post_id = raw.get("id")
    else:
        text = str(raw)
        m_slug = re.search(r"Slug:\s*(\S+)", text)
        m_id = re.search(r"ID:\s*(\d+)", text)
        slug = m_slug.group(1) if m_slug else None
        post_id = int(m_id.group(1)) if m_id else None

    return {"published_slug": slug, "published_id": post_id}
