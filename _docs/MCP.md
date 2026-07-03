# Meridian MCP Server

Meridian exposes a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) endpoint that lets external AI agents interact with the blogging platform — discovering content, publishing posts, and managing contributor accounts.

## Transport

**Streamable HTTP** (MCP spec 2024-11-05) — stateless, JSON-RPC 2.0 over a single POST endpoint.

| Environment | MCP Endpoint URL |
|---|---|
| Local dev | `http://localhost:3000/api/mcp` |
| Docker (local) | `http://localhost:7860/api/mcp` |
| HuggingFace Spaces | `https://mishrabp-myblogs.hf.space/api/mcp` |

## Authentication

All requests require an `Authorization` header carrying the `MCP_API_KEY` configured in the server's `.env`:

```
Authorization: Bearer <MCP_API_KEY>
```

Set `MCP_API_KEY` in `.env` (see `.env.example`). If `MCP_API_KEY` is unset the server accepts all requests — suitable only for local development.

## Protocol Handshake

Before calling tools, clients must complete the initialize handshake:

```jsonc
// 1. Client → Server: initialize
POST /api/mcp
Content-Type: application/json
Authorization: Bearer <MCP_API_KEY>

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": { "name": "my-agent", "version": "1.0" }
  }
}

// 2. Server → Client: capabilities
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": { "tools": {} },
    "serverInfo": { "name": "meridian-mcp", "version": "1.0.0" }
  }
}

// 3. Client → Server: initialized notification (no response expected)
{ "jsonrpc": "2.0", "method": "notifications/initialized" }
```

## Available Tools

### 1. `manage_guest_user`
Create, update, or delete guest contributor accounts.

> **The `admin@myblogs.com` account is permanently protected and cannot be touched by this tool.**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `action` | `"create" \| "update" \| "delete"` | ✅ | Operation to perform |
| `email` | string | ✅ | User's email address |
| `name` | string | for create | Full display name |
| `password` | string | for create | Login password (min 8 chars) |
| `bio` | string | — | Short author bio |
| `is_active` | boolean | — | `false` suspends without deleting |

```jsonc
// Create a guest writer
{
  "jsonrpc": "2.0", "id": 2,
  "method": "tools/call",
  "params": {
    "name": "manage_guest_user",
    "arguments": {
      "action": "create",
      "email": "alice@example.com",
      "name": "Alice Smith",
      "password": "securePass123",
      "bio": "Tech writer and open-source enthusiast."
    }
  }
}
```

---

### 2. `list_blogs`
Retrieve published posts with optional filtering.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `filter` | `"latest" \| "featured" \| "recent"` | `"latest"` | `latest` = newest-first paginated; `featured` = top 5 by views; `recent` = last 6 published |
| `category` | string | — | Filter by category slug (use `list_categories`) |
| `tag` | string | — | Filter by tag slug (use `list_tags`) |
| `page` | integer | 1 | Page number (latest only) |
| `limit` | integer | 10 | Results per page, max 50 (latest only) |

```jsonc
// Get the 5 most popular posts
{
  "jsonrpc": "2.0", "id": 3,
  "method": "tools/call",
  "params": { "name": "list_blogs", "arguments": { "filter": "featured" } }
}

// Latest 10 posts in the "technology" category
{
  "jsonrpc": "2.0", "id": 4,
  "method": "tools/call",
  "params": { "name": "list_blogs", "arguments": { "category": "technology", "limit": 10 } }
}
```

---

### 3. `get_blog`
Fetch the full content of a post by its URL slug.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `slug` | string | ✅ | URL slug (e.g. `"understanding-react-hooks"`) |
| `summarize` | boolean | — | Generate a 2-3 sentence AI summary (requires `OPENAI_API_KEY`) |

```jsonc
{
  "jsonrpc": "2.0", "id": 5,
  "method": "tools/call",
  "params": {
    "name": "get_blog",
    "arguments": { "slug": "understanding-react-hooks", "summarize": true }
  }
}
```

---

### 4. `search_blogs`
Full-text keyword search across titles, excerpts, and body content (case-insensitive SQL ILIKE).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | string | ✅ required | Search term (e.g. `"machine learning"`) |
| `limit` | integer | 10 | Max results, max 50 |
| `include_content` | boolean | false | Append a 500-char body snippet to each result |

```jsonc
{
  "jsonrpc": "2.0", "id": 6,
  "method": "tools/call",
  "params": {
    "name": "search_blogs",
    "arguments": { "query": "docker kubernetes", "limit": 5 }
  }
}
```

---

### 5. `create_blog`
Publish a new blog post with rich HTML content.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `title` | string | ✅ | Post title (50-70 chars ideal) |
| `content` | string | ✅ | Full HTML body — see supported tags below |
| `excerpt` | string | ✅ | ~120-160 char summary for listing cards |
| `category_id` | integer | — | From `list_categories` |
| `tag_ids` | integer[] | — | From `list_tags` (3-6 tags recommended) |
| `featured_image` | string | — | Image URL (1200×630 px, Unsplash etc.) |
| `status` | `"draft" \| "published"` | `"draft"` | Visibility |
| `author_name` | string | `"MCP Agent"` | Display name shown on the post |

**Supported HTML tags in `content`:**
```
<h2>, <h3>, <h4>          — Section headings
<p>                        — Paragraphs
<strong>, <em>             — Bold, italic
<a href="...">             — Links
<ul>, <ol>, <li>           — Lists
<blockquote>               — Pull quotes
<img src="..." alt="...">  — Inline images
<pre><code class="language-js">...</code></pre>  — Syntax-highlighted code
```

```jsonc
{
  "jsonrpc": "2.0", "id": 7,
  "method": "tools/call",
  "params": {
    "name": "create_blog",
    "arguments": {
      "title": "Getting Started with Docker in 2026",
      "excerpt": "A practical guide to containerising your first Node.js app — from zero to running in under 30 minutes.",
      "content": "<h2>Introduction</h2><p>Docker simplifies deployment by packaging your app and its dependencies into a portable container...</p><h2>Prerequisites</h2><ul><li>Node.js 20+</li><li>Docker Desktop</li></ul><pre><code class=\"language-bash\">docker build -t myapp . && docker run -p 3000:3000 myapp</code></pre>",
      "category_id": 1,
      "tag_ids": [2, 5, 9],
      "featured_image": "https://images.unsplash.com/photo-1605745341112-85968b19335b?w=1200",
      "status": "published",
      "author_name": "Alice Smith"
    }
  }
}
```

---

### 6. `update_blog`
Edit an existing post. Only supplied fields are updated.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | integer | ✅ | Numeric post ID |
| `title` | string | — | New title (regenerates slug) |
| `content` | string | — | Replacement HTML body |
| `excerpt` | string | — | Replacement excerpt |
| `category_id` | integer \| null | — | New category, or `null` to remove |
| `tag_ids` | integer[] | — | Replaces entire tag list |
| `featured_image` | string | — | New image URL |
| `status` | `"draft" \| "published"` | — | Change visibility |

```jsonc
// Publish a draft and add a new tag
{
  "jsonrpc": "2.0", "id": 8,
  "method": "tools/call",
  "params": {
    "name": "update_blog",
    "arguments": { "id": 42, "status": "published", "tag_ids": [2, 5, 9, 11] }
  }
}
```

---

### 7. `list_categories`
Returns all categories with IDs, names, slugs, colors, and descriptions.

```jsonc
{
  "jsonrpc": "2.0", "id": 9,
  "method": "tools/call",
  "params": { "name": "list_categories", "arguments": {} }
}
```

---

### 8. `list_tags`
Returns all tags with IDs, names, and slugs.

```jsonc
{
  "jsonrpc": "2.0", "id": 10,
  "method": "tools/call",
  "params": { "name": "list_tags", "arguments": {} }
}
```

---

## Discover Tools Programmatically

```jsonc
{
  "jsonrpc": "2.0", "id": 2,
  "method": "tools/list"
}
```

Returns the full schema for all 8 tools with detailed descriptions and JSON Schema input definitions.

---

## Quick Test with curl

```bash
MCP_URL="http://localhost:3000/api/mcp"
MCP_KEY="your-mcp-api-key"

# Initialize
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MCP_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}' \
  | jq .

# List tools
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MCP_KEY" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | jq '.result.tools[].name'

# Search posts
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MCP_KEY" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_blogs","arguments":{"query":"javascript","limit":3}}}' \
  | jq '.result.content[0].text'
```

---

## Integrating with Claude Desktop

Add this to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "meridian": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:3000/api/mcp",
        "--header",
        "Authorization: Bearer YOUR_MCP_API_KEY"
      ]
    }
  }
}
```

> **Note:** `mcp-remote` is a bridge package (`npm i -g mcp-remote`) that adapts the HTTP MCP endpoint for Claude Desktop's stdio transport. Replace `localhost:3000` with your deployed URL for HF Spaces.

---

## Integrating with Claude Code / Agent SDK

```python
import anthropic

client = anthropic.Anthropic()

response = client.beta.messages.create(
    model="claude-opus-4-8",
    max_tokens=4096,
    tools=[
        {
            "type": "custom",
            "name": "meridian_mcp",
            "description": "Meridian blogging platform tools",
            # Use the MCP SDK to connect to the endpoint
        }
    ],
    messages=[{"role": "user", "content": "Find the most popular blog posts about React"}]
)
```

Or using the MCP Python SDK directly:

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def run():
    async with streamablehttp_client(
        "http://localhost:3000/api/mcp",
        headers={"Authorization": "Bearer YOUR_MCP_API_KEY"}
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print([t.name for t in tools.tools])
            
            # Search for posts
            result = await session.call_tool(
                "search_blogs",
                {"query": "javascript", "limit": 5}
            )
            print(result.content[0].text)
```

Install: `pip install mcp`

---

## Recommended Agent Workflow

For best results when an agent is creating a blog post:

1. Call `list_categories` → pick the best category ID
2. Call `list_tags` → select 3-6 relevant tag IDs
3. Call `search_blogs` with the post topic → verify content doesn't already exist
4. Call `create_blog` with `status="draft"` → review the returned slug/ID
5. Call `get_blog` with the slug → verify the rendered content
6. Call `update_blog` with `status="published"` → go live

---

## Security Notes

- `MCP_API_KEY` should be kept secret and rotated if exposed
- The `admin@myblogs.com` account has a hard-coded guard in the server — it cannot be modified even if a valid key is provided
- Write operations (create/update post, manage users) require the key; internal calls use a short-lived JWT signed with the shared service secret
- The MCP endpoint is public-facing — ensure a strong, random `MCP_API_KEY` in production (`openssl rand -hex 24`)
