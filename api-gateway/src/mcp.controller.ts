import { Controller, Post, Body, Headers, HttpCode } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { ProxyService } from './proxy.service';

const PROTOCOL_VERSION = '2024-11-05';
// The admin account is permanently protected — MCP tools may never touch it.
const PROTECTED_ADMIN = 'admin@myblogs.com';

// ── Tool definitions ──────────────────────────────────────────────────────────
// Descriptions are deliberately verbose so LLM agents have the context they
// need to pick the right tool and supply correct arguments without guessing.

const TOOL_DEFINITIONS = [
  {
    name: 'manage_guest_user',
    description:
      'Create, update, or deactivate/delete guest contributor accounts on Meridian. ' +
      'Guest users can log in to the admin panel and create or edit blog posts. ' +
      'The protected admin account (admin@myblogs.com) can NEVER be modified or deleted ' +
      'by this tool — any attempt will be rejected. ' +
      'Use action="create" to onboard a new writer, action="update" to change their details ' +
      'or suspend them (is_active=false), and action="delete" to remove the account entirely.',
    inputSchema: {
      type: 'object',
      properties: {
        action: {
          type: 'string',
          enum: ['create', 'update', 'delete'],
          description:
            '"create" — add a new guest account. ' +
            '"update" — change name, password, bio, or active status. ' +
            '"delete" — permanently remove the account.',
        },
        email: {
          type: 'string',
          description: 'Email address that identifies the user. Required for all actions.',
        },
        name: {
          type: 'string',
          description: 'Full display name shown on blog posts. Required for create; optional for update.',
        },
        password: {
          type: 'string',
          description:
            'Login password (minimum 8 characters recommended). ' +
            'Required for create; optional for update — omit to leave unchanged.',
        },
        bio: {
          type: 'string',
          description: 'Short author bio (1-2 sentences) displayed on blog posts. Optional.',
        },
        is_active: {
          type: 'boolean',
          description:
            'Account status. true (default) = active and able to log in. ' +
            'Set false to suspend the account without deleting it.',
        },
      },
      required: ['action', 'email'],
    },
  },

  {
    name: 'list_blogs',
    description:
      'Retrieve published blog posts from Meridian with flexible filtering. ' +
      'Use filter="latest" for a paginated newest-first list (supports category/tag filters). ' +
      'Use filter="featured" for the top 5 most-viewed posts. ' +
      'Use filter="recent" for the 6 most recently published posts. ' +
      'Call list_categories and list_tags to discover valid slugs for filtering. ' +
      'Results include post ID, slug, title, category, tags, excerpt, view count, and read time — ' +
      'enough to answer questions like "what are the latest posts about React?" without fetching full content.',
    inputSchema: {
      type: 'object',
      properties: {
        filter: {
          type: 'string',
          enum: ['latest', 'featured', 'recent'],
          description:
            '"latest" (default) — paginated, newest first. ' +
            '"featured" — top 5 by all-time view count. ' +
            '"recent" — last 6 published.',
        },
        category: {
          type: 'string',
          description:
            'Filter by category slug (e.g. "technology", "lifestyle"). ' +
            'Only applies to filter="latest". Use list_categories to see available slugs.',
        },
        tag: {
          type: 'string',
          description:
            'Filter by tag slug (e.g. "javascript", "react"). ' +
            'Only applies to filter="latest". Use list_tags to see available slugs.',
        },
        page: {
          type: 'integer',
          description: 'Page number for paginated results. Only applies to filter="latest". Default: 1.',
        },
        limit: {
          type: 'integer',
          description:
            'Posts per page. Only applies to filter="latest". Default: 10, max: 50.',
        },
      },
    },
  },

  {
    name: 'get_blog',
    description:
      'Retrieve the complete content of a specific blog post by its URL slug. ' +
      'Returns full HTML content, metadata (category, tags, author, view count, read time), ' +
      'and all associated comments. ' +
      'Set summarize=true to get a concise 2-3 sentence AI-generated summary of the post ' +
      '(requires OPENAI_API_KEY to be configured on the server). ' +
      'Use this when you need to read, quote, or summarise a specific article.',
    inputSchema: {
      type: 'object',
      properties: {
        slug: {
          type: 'string',
          description:
            'URL slug of the post (e.g. "understanding-javascript-closures"). ' +
            'Visible in list_blogs and search_blogs results.',
        },
        summarize: {
          type: 'boolean',
          description:
            'If true, appends an AI-generated 2-3 sentence summary of the post body. ' +
            'Default: false.',
        },
      },
      required: ['slug'],
    },
  },

  {
    name: 'search_blogs',
    description:
      'Full-text keyword search across all published blog posts. ' +
      'Searches post titles, excerpts, and full body content (case-insensitive). ' +
      'Returns matching posts with title, slug, excerpt, category, and tags. ' +
      'Set include_content=true to also return the full HTML body of each result — ' +
      'useful when you need to quote or analyse specific passages. ' +
      'This is a SQL LIKE/ILIKE search; vector/semantic search is not yet implemented. ' +
      'Use specific keywords rather than natural-language questions for best results.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description:
            'Search keyword or phrase (e.g. "React hooks", "machine learning", "docker"). ' +
            'Case-insensitive. Prefix/suffix wildcard % is supported if needed.',
        },
        limit: {
          type: 'integer',
          description: 'Maximum number of results to return. Default: 10, max: 50.',
        },
        include_content: {
          type: 'boolean',
          description:
            'If true, includes the first 500 characters of stripped body text for each result. ' +
            'Default: false.',
        },
      },
      required: ['query'],
    },
  },

  {
    name: 'create_blog',
    description:
      'Publish a new blog post on Meridian. Supports rich HTML content: ' +
      'headings (<h2>, <h3>), paragraphs (<p>), bold/italic, links (<a href>), ' +
      'images (<img src>), ordered/unordered lists, blockquotes, and ' +
      'syntax-highlighted code blocks (<pre><code class="language-js">...</code></pre>). ' +
      'Always call list_categories and list_tags first to get valid IDs. ' +
      'Use a high-quality landscape image URL for featured_image (1200×630 px ideal). ' +
      'Write a compelling excerpt (~160 chars) — it appears on listing cards and in SEO meta. ' +
      'Set status="draft" to save privately or "published" to go live immediately.',
    inputSchema: {
      type: 'object',
      properties: {
        title: {
          type: 'string',
          description:
            'Post title. Clear, descriptive, SEO-friendly (50-70 chars ideal). ' +
            'The URL slug is derived automatically from this.',
        },
        content: {
          type: 'string',
          description:
            'Full post body as HTML. Structure with <h2>/<h3> section headings, ' +
            '<p> paragraphs, <ul>/<ol> lists, <blockquote> for pull-quotes, ' +
            'and <pre><code class="language-js">...</code></pre> for code. ' +
            'Aim for at least 500 words for quality content.',
        },
        excerpt: {
          type: 'string',
          description:
            'Post summary shown on listing cards and used as meta description. ' +
            '1-3 sentences, ~120-160 characters. Should hook the reader.',
        },
        category_id: {
          type: 'integer',
          description: 'Numeric category ID. Use list_categories to get valid IDs.',
        },
        tag_ids: {
          type: 'array',
          items: { type: 'integer' },
          description:
            'Array of numeric tag IDs. Use list_tags to get valid IDs. ' +
            '3-6 tags are recommended for discoverability.',
        },
        featured_image: {
          type: 'string',
          description:
            'Hero image URL or /uploads/ path. High-quality landscape images (1200×630 px) ' +
            'work best. Use a relevant, royalty-free image. Unsplash URLs are accepted.',
        },
        status: {
          type: 'string',
          enum: ['draft', 'published'],
          description:
            '"published" — immediately visible on the site. ' +
            '"draft" — saved privately, not visible to readers. Default: "draft".',
        },
        author_name: {
          type: 'string',
          description:
            'Display name shown as the author on the post. Defaults to "MCP Agent". ' +
            'Set this to the actual author\'s name when posting on behalf of someone.',
        },
      },
      required: ['title', 'content', 'excerpt'],
    },
  },

  {
    name: 'update_blog',
    description:
      'Edit an existing blog post. Only fields you explicitly provide are updated — ' +
      'omitted fields retain their current values. ' +
      'Fetch the current post with get_blog first to review its content before editing. ' +
      'Providing tag_ids replaces the entire tag list; provide all desired tag IDs. ' +
      'Changing the title regenerates the URL slug.',
    inputSchema: {
      type: 'object',
      properties: {
        id: {
          type: 'integer',
          description: 'Numeric post ID. Visible in list_blogs and get_blog results.',
        },
        title: { type: 'string', description: 'New post title. Regenerates the URL slug.' },
        content: { type: 'string', description: 'Replacement HTML body content.' },
        excerpt: { type: 'string', description: 'Replacement post summary/excerpt.' },
        category_id: {
          type: ['integer', 'null'],
          description: 'New category ID, or null to remove the category association.',
        },
        tag_ids: {
          type: 'array',
          items: { type: 'integer' },
          description: 'Replaces the full tag list. Provide all desired tag IDs.',
        },
        featured_image: { type: 'string', description: 'Replacement featured image URL.' },
        status: {
          type: 'string',
          enum: ['draft', 'published'],
          description: 'Change the publish status.',
        },
      },
      required: ['id'],
    },
  },

  {
    name: 'list_categories',
    description:
      'List all blog categories with their numeric IDs, names, slugs, colors, and descriptions. ' +
      'Call this before create_blog or update_blog to find valid category_id values, ' +
      'or to understand the site\'s content taxonomy. ' +
      'Categories represent broad topic areas (e.g. Technology, Lifestyle, Travel).',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },

  {
    name: 'list_tags',
    description:
      'List all available blog tags with their numeric IDs, names, and slugs. ' +
      'Call this before create_blog or update_blog to find valid tag_id values. ' +
      'Tags represent specific topics, technologies, or concepts within a post ' +
      '(e.g. javascript, docker, machine-learning). Multiple tags improve discoverability.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
];

// ── Controller ────────────────────────────────────────────────────────────────

@Controller('api/mcp')
export class McpController {
  constructor(
    private readonly proxy: ProxyService,
    private readonly jwt: JwtService,
  ) {}

  /** Short-lived JWT for internal service calls made on behalf of MCP agent. */
  private agentAuth(): string {
    const token = this.jwt.sign(
      { id: 0, email: 'mcp-agent@meridian.internal', name: 'MCP Agent', role: 'admin' },
      { expiresIn: '5m' },
    );
    return `Bearer ${token}`;
  }

  private rpcOk(id: any, result: any) {
    return { jsonrpc: '2.0', id: id ?? null, result };
  }

  private rpcErr(id: any, code: number, message: string) {
    return { jsonrpc: '2.0', id: id ?? null, error: { code, message } };
  }

  private toolResult(text: string) {
    return { content: [{ type: 'text', text }] };
  }

  private toolErr(message: string) {
    return { content: [{ type: 'text', text: `Error: ${message}` }], isError: true };
  }

  @Post()
  @HttpCode(200)
  async handle(
    @Body() body: any,
    @Headers('authorization') authHeader: string,
  ) {
    const configuredKey = process.env.MCP_API_KEY;
    if (configuredKey) {
      const provided = (authHeader ?? '').replace(/^Bearer\s+/i, '');
      if (provided !== configuredKey) {
        return this.rpcErr(body?.id ?? null, -32001, 'Unauthorized: missing or invalid MCP_API_KEY');
      }
    }

    const { method, id, params } = body ?? {};

    // JSON-RPC notifications have no id — acknowledge without body
    if (id === undefined) return {};

    try {
      switch (method) {
        case 'initialize':
          return this.rpcOk(id, {
            protocolVersion: PROTOCOL_VERSION,
            capabilities: { tools: {} },
            serverInfo: { name: 'meridian-mcp', version: '1.0.0' },
            instructions:
              'Meridian blogging platform MCP server. ' +
              'Use tools/list to discover available tools. ' +
              'All write operations (create/update posts, manage users) require MCP_API_KEY authentication. ' +
              'The admin@myblogs.com account is permanently protected.',
          });

        case 'ping':
          return this.rpcOk(id, {});

        case 'tools/list':
          return this.rpcOk(id, { tools: TOOL_DEFINITIONS });

        case 'tools/call':
          return this.rpcOk(id, await this.dispatch(params?.name, params?.arguments ?? {}));

        default:
          return this.rpcErr(id, -32601, `Method not found: ${method}`);
      }
    } catch (e) {
      return this.rpcErr(id, -32603, (e as any)?.message ?? 'Internal error');
    }
  }

  private async dispatch(toolName: string, args: Record<string, any>) {
    switch (toolName) {
      case 'manage_guest_user': return this.manageGuestUser(args);
      case 'list_blogs':        return this.listBlogs(args);
      case 'get_blog':          return this.getBlog(args);
      case 'search_blogs':      return this.searchBlogs(args);
      case 'create_blog':       return this.createBlog(args);
      case 'update_blog':       return this.updateBlog(args);
      case 'list_categories':   return this.listCategories();
      case 'list_tags':         return this.listTags();
      default:
        return this.toolErr(`Unknown tool "${toolName}". Call tools/list to see available tools.`);
    }
  }

  // ── Tool: manage_guest_user ─────────────────────────────────────────────────

  private async manageGuestUser(args: Record<string, any>) {
    const { action, email, name, password, bio, is_active } = args;

    if (!email) return this.toolErr('"email" is required.');
    if (email.toLowerCase() === PROTECTED_ADMIN.toLowerCase()) {
      return this.toolErr(
        `The admin account "${PROTECTED_ADMIN}" is permanently protected and cannot be modified or deleted by this tool.`,
      );
    }

    const auth = this.agentAuth();

    if (action === 'create') {
      if (!name || !password) return this.toolErr('"name" and "password" are required for action="create".');
      try {
        const user = await this.proxy.forward('auth', '/users', 'POST', {
          email, name, password, bio: bio ?? '', role: 'guest',
        }, { Authorization: auth });
        return this.toolResult(
          `Guest user created successfully.\n` +
          `  ID:    ${user.id}\n` +
          `  Email: ${user.email}\n` +
          `  Name:  ${user.name}\n` +
          `  Role:  ${user.role}`,
        );
      } catch (e) {
        return this.toolErr((e as any)?.message ?? 'Failed to create user.');
      }
    }

    // update / delete — locate user by email first
    let users: any[];
    try {
      users = await this.proxy.forward('auth', '/users', 'GET', null, { Authorization: auth });
    } catch (e) {
      return this.toolErr('Could not retrieve user list: ' + ((e as any)?.message ?? ''));
    }
    const target = users.find((u: any) => u.email.toLowerCase() === email.toLowerCase());
    if (!target) return this.toolErr(`No user found with email "${email}".`);

    if (action === 'update') {
      const patch: Record<string, any> = {};
      if (name !== undefined)      patch.name = name;
      if (password !== undefined)  patch.password = password;
      if (bio !== undefined)       patch.bio = bio;
      if (is_active !== undefined) patch.isActive = is_active;
      if (Object.keys(patch).length === 0) return this.toolErr('No update fields provided.');
      try {
        const u = await this.proxy.forward('auth', `/users/${target.id}`, 'PUT', patch, { Authorization: auth });
        return this.toolResult(
          `User updated.\n  ID: ${u.id} | Email: ${u.email} | Name: ${u.name} | Active: ${u.isActive}`,
        );
      } catch (e) {
        return this.toolErr((e as any)?.message ?? 'Failed to update user.');
      }
    }

    if (action === 'delete') {
      try {
        await this.proxy.forward('auth', `/users/${target.id}`, 'DELETE', null, { Authorization: auth });
        return this.toolResult(`User deleted: ${email} (ID: ${target.id})`);
      } catch (e) {
        return this.toolErr((e as any)?.message ?? 'Failed to delete user.');
      }
    }

    return this.toolErr(`Unknown action "${action}". Use "create", "update", or "delete".`);
  }

  // ── Tool: list_blogs ────────────────────────────────────────────────────────

  private async listBlogs(args: Record<string, any>) {
    const { filter = 'latest', category, tag, page = 1, limit = 10 } = args;

    try {
      if (filter === 'featured') {
        const posts: any[] = await this.proxy.forward('blog', '/posts/featured', 'GET');
        return this.toolResult(
          `Top ${posts.length} featured post(s) by view count:\n\n` +
          posts.map((p, i) => this.formatPostSummary(i + 1, p)).join('\n\n'),
        );
      }

      if (filter === 'recent') {
        const posts: any[] = await this.proxy.forward('blog', '/posts/recent', 'GET');
        return this.toolResult(
          `${posts.length} most recent post(s):\n\n` +
          posts.map((p, i) => this.formatPostSummary(i + 1, p)).join('\n\n'),
        );
      }

      // latest — paginated with optional category/tag filters
      const qs = new URLSearchParams({
        page: String(+page),
        limit: String(Math.min(+limit, 50)),
        ...(category ? { category } : {}),
        ...(tag ? { tag } : {}),
      });
      const result = await this.proxy.forward('blog', `/posts?${qs}`, 'GET');
      const { posts, total, page: pg, pages } = result;

      return this.toolResult(
        `Total: ${total} post(s) | Page ${pg} of ${pages} | Showing ${posts.length}\n\n` +
        posts.map((p: any, i: number) => this.formatPostSummary(i + 1, p)).join('\n\n'),
      );
    } catch (e) {
      return this.toolErr((e as any)?.message ?? 'Failed to fetch posts.');
    }
  }

  // ── Tool: get_blog ──────────────────────────────────────────────────────────

  private async getBlog(args: Record<string, any>) {
    const { slug, summarize = false } = args;
    if (!slug) return this.toolErr('"slug" is required.');

    try {
      const post = await this.proxy.forward('blog', `/posts/${slug}`, 'GET');
      const bodyText = this.stripHtml(post.content ?? '');

      let summaryLine = '';
      if (summarize && process.env.OPENAI_API_KEY) {
        const s = await this.aiSummarize(post.title, bodyText);
        if (s) summaryLine = `\n**AI Summary**: ${s}\n`;
      }

      const tags = post.tags?.map((t: any) => t.name).join(', ') || 'None';
      const commentCount = Array.isArray(post.comments) ? post.comments.length : 0;

      return this.toolResult(
        `**${post.title}**\n` +
        `ID: ${post.id} | Slug: ${post.slug} | Status: ${post.status}\n` +
        `Category: ${post.category?.name ?? 'None'} | Tags: ${tags}\n` +
        `Author: ${post.authorName ?? 'Unknown'} | Published: ${post.createdAt?.slice(0, 10)}\n` +
        `Views: ${post.views ?? 0} | Read time: ${post.readTime ?? '?'} min | Comments: ${commentCount}\n` +
        `\n**Excerpt**: ${post.excerpt ?? '(none)'}` +
        summaryLine +
        `\n**Featured image**: ${post.featuredImage ?? '(none)'}` +
        `\n\n**Content** (HTML):\n${post.content ?? ''}`,
      );
    } catch (e) {
      return this.toolErr((e as any)?.message ?? `Post not found: "${slug}".`);
    }
  }

  // ── Tool: search_blogs ──────────────────────────────────────────────────────

  private async searchBlogs(args: Record<string, any>) {
    const { query, limit = 10, include_content = false } = args;
    if (!query) return this.toolErr('"query" is required.');

    try {
      const qs = new URLSearchParams({ search: query, limit: String(Math.min(+limit, 50)) });
      const result = await this.proxy.forward('blog', `/posts?${qs}`, 'GET');
      const posts: any[] = result.posts ?? [];

      if (posts.length === 0) {
        return this.toolResult(`No published posts found matching "${query}".`);
      }

      const blocks = posts.map((p, i) => {
        let block = this.formatPostSummary(i + 1, p);
        if (include_content) {
          block += `\n   Body snippet: ${this.stripHtml(p.content ?? '').slice(0, 500)}…`;
        }
        return block;
      });

      return this.toolResult(
        `Found ${result.total} post(s) matching "${query}" (showing ${posts.length}):\n\n` +
        blocks.join('\n\n'),
      );
    } catch (e) {
      return this.toolErr((e as any)?.message ?? 'Search failed.');
    }
  }

  // ── Tool: create_blog ───────────────────────────────────────────────────────

  private async createBlog(args: Record<string, any>) {
    const {
      title, content, excerpt,
      category_id, tag_ids, featured_image,
      status = 'draft', author_name = 'MCP Agent',
    } = args;

    if (!title)   return this.toolErr('"title" is required.');
    if (!content) return this.toolErr('"content" is required.');
    if (!excerpt) return this.toolErr('"excerpt" is required.');

    const auth = this.agentAuth();
    try {
      const post = await this.proxy.forward('blog', '/posts', 'POST', {
        title,
        content,
        excerpt,
        categoryId:    category_id  ?? null,
        tagIds:        tag_ids       ?? [],
        featuredImage: featured_image ?? null,
        status,
        authorName:    author_name,
      }, { Authorization: auth });

      const tags = post.tags?.map((t: any) => t.name).join(', ') || 'None';
      return this.toolResult(
        `Post ${status === 'published' ? 'published' : 'saved as draft'} successfully!\n` +
        `  ID:        ${post.id}\n` +
        `  Title:     ${post.title}\n` +
        `  Slug:      ${post.slug}\n` +
        `  Status:    ${post.status}\n` +
        `  URL path:  /blog/${post.slug}\n` +
        `  Category:  ${post.category?.name ?? 'None'}\n` +
        `  Tags:      ${tags}\n` +
        `  Read time: ${post.readTime ?? '?'} min`,
      );
    } catch (e) {
      return this.toolErr((e as any)?.message ?? 'Failed to create post.');
    }
  }

  // ── Tool: update_blog ───────────────────────────────────────────────────────

  private async updateBlog(args: Record<string, any>) {
    const { id, title, content, excerpt, category_id, tag_ids, featured_image, status } = args;
    if (!id) return this.toolErr('"id" is required.');

    const patch: Record<string, any> = {};
    if (title !== undefined)          patch.title = title;
    if (content !== undefined)        patch.content = content;
    if (excerpt !== undefined)        patch.excerpt = excerpt;
    if (category_id !== undefined)    patch.categoryId = category_id;
    if (tag_ids !== undefined)        patch.tagIds = tag_ids;
    if (featured_image !== undefined) patch.featuredImage = featured_image;
    if (status !== undefined)         patch.status = status;

    if (Object.keys(patch).length === 0) {
      return this.toolErr('No update fields were provided. Include at least one field to change.');
    }

    const auth = this.agentAuth();
    try {
      const post = await this.proxy.forward('blog', `/posts/${id}`, 'PUT', patch, { Authorization: auth });
      return this.toolResult(
        `Post updated successfully.\n` +
        `  ID: ${post.id} | Slug: ${post.slug}\n` +
        `  Title:  ${post.title}\n` +
        `  Status: ${post.status}\n` +
        `  URL:    /blog/${post.slug}`,
      );
    } catch (e) {
      return this.toolErr((e as any)?.message ?? `Failed to update post ID ${id}.`);
    }
  }

  // ── Tool: list_categories ───────────────────────────────────────────────────

  private async listCategories() {
    try {
      const cats: any[] = await this.proxy.forward('blog', '/categories', 'GET');
      if (!cats?.length) return this.toolResult('No categories found on this site.');
      const lines = cats.map(
        c => `  ID: ${c.id} | Name: ${c.name} | Slug: ${c.slug} | Color: ${c.color ?? 'N/A'}\n  Description: ${c.description ?? 'N/A'}`,
      );
      return this.toolResult(`${cats.length} categories:\n\n` + lines.join('\n\n'));
    } catch (e) {
      return this.toolErr((e as any)?.message ?? 'Failed to fetch categories.');
    }
  }

  // ── Tool: list_tags ─────────────────────────────────────────────────────────

  private async listTags() {
    try {
      const tags: any[] = await this.proxy.forward('blog', '/tags', 'GET');
      if (!tags?.length) return this.toolResult('No tags found on this site.');
      const lines = tags.map(t => `  ID: ${t.id} | Name: ${t.name} | Slug: ${t.slug}`);
      return this.toolResult(`${tags.length} tags:\n\n` + lines.join('\n'));
    } catch (e) {
      return this.toolErr((e as any)?.message ?? 'Failed to fetch tags.');
    }
  }

  // ── Helpers ─────────────────────────────────────────────────────────────────

  private formatPostSummary(index: number, p: any): string {
    const tags = p.tags?.map((t: any) => t.name).join(', ') || 'None';
    return (
      `${index}. **${p.title}** (ID: ${p.id})\n` +
      `   Slug:      ${p.slug}\n` +
      `   Category:  ${p.category?.name ?? 'None'} | Tags: ${tags}\n` +
      `   Published: ${p.createdAt?.slice(0, 10)} | Views: ${p.views ?? 0} | Read time: ${p.readTime ?? '?'} min\n` +
      `   Excerpt:   ${p.excerpt ?? '(none)'}`
    );
  }

  private stripHtml(html: string): string {
    return html.replace(/<[^>]*>/g, ' ').replace(/&[a-z]+;/gi, ' ').replace(/\s+/g, ' ').trim();
  }

  private async aiSummarize(title: string, text: string): Promise<string> {
    try {
      const r = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        },
        body: JSON.stringify({
          model: 'gpt-4o-mini',
          messages: [
            {
              role: 'system',
              content: 'Summarize the blog post in exactly 2-3 concise, informative sentences. Be specific about what the reader will learn.',
            },
            { role: 'user', content: `Title: ${title}\n\n${text.slice(0, 3000)}` },
          ],
          max_tokens: 120,
          temperature: 0.3,
        }),
      });
      if (!r.ok) return '';
      const data: any = await r.json();
      return data.choices?.[0]?.message?.content?.trim() ?? '';
    } catch {
      return '';
    }
  }
}
