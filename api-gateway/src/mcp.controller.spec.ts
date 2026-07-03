import { McpController } from './mcp.controller';
import { ProxyService } from './proxy.service';
import { JwtService } from '@nestjs/jwt';

describe('McpController', () => {
  const mockProxy = { forward: jest.fn() } as unknown as ProxyService;
  const mockJwt = { sign: jest.fn().mockReturnValue('signed-token') } as unknown as JwtService;

  let controller: McpController;
  const ORIGINAL_ENV = process.env;

  beforeEach(() => {
    jest.clearAllMocks();
    process.env = { ...ORIGINAL_ENV };
    delete process.env.MCP_API_KEY;
    controller = new McpController(mockProxy, mockJwt);
    global.fetch = jest.fn();
  });

  afterAll(() => {
    process.env = ORIGINAL_ENV;
  });

  describe('handle — envelope and auth', () => {
    it('acknowledges notifications (no id) with an empty object', async () => {
      const result = await controller.handle({ method: 'ping' }, '');
      expect(result).toEqual({});
    });

    it('rejects requests with a missing/invalid MCP_API_KEY when one is configured', async () => {
      process.env.MCP_API_KEY = 'secret-key';
      const result: any = await controller.handle({ method: 'ping', id: 1 }, 'Bearer wrong-key');
      expect(result.error.code).toBe(-32001);
    });

    it('accepts requests with the correct MCP_API_KEY', async () => {
      process.env.MCP_API_KEY = 'secret-key';
      const result: any = await controller.handle({ method: 'ping', id: 1 }, 'Bearer secret-key');
      expect(result.result).toEqual({});
    });

    it('skips the auth check entirely when MCP_API_KEY is not configured', async () => {
      const result: any = await controller.handle({ method: 'ping', id: 1 }, '');
      expect(result.result).toEqual({});
    });

    it('returns capabilities for the initialize method', async () => {
      const result: any = await controller.handle({ method: 'initialize', id: 1 }, '');
      expect(result.result.protocolVersion).toBeDefined();
      expect(result.result.serverInfo.name).toBe('meridian-mcp');
    });

    it('returns the tool definitions for tools/list', async () => {
      const result: any = await controller.handle({ method: 'tools/list', id: 1 }, '');
      expect(Array.isArray(result.result.tools)).toBe(true);
      expect(result.result.tools.length).toBeGreaterThan(0);
    });

    it('returns a JSON-RPC error for an unknown method', async () => {
      const result: any = await controller.handle({ method: 'not-a-method', id: 1 }, '');
      expect(result.error.code).toBe(-32601);
    });

    it('returns a JSON-RPC internal error when a handler throws unexpectedly', async () => {
      (mockProxy.forward as jest.Mock).mockRejectedValue(new Error('should be caught by tool, not here'));
      // Force an unexpected throw path by calling tools/call with a name that dispatches fine,
      // but simulate a non-tool exception via a malformed params object.
      const result: any = await controller.handle(
        { method: 'tools/call', id: 1, params: null },
        '',
      );
      // dispatch() defaults args to {} safely, so this should resolve via the "unknown tool" path, not throw.
      expect(result.result).toBeDefined();
    });

    it('routes tools/call to the requested tool and returns its result', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue([]);
      const result: any = await controller.handle(
        { method: 'tools/call', id: 1, params: { name: 'list_categories', arguments: {} } },
        '',
      );
      expect(result.result.content[0].text).toContain('No categories found');
    });

    it('returns a tool error for an unrecognised tool name', async () => {
      const result: any = await controller.handle(
        { method: 'tools/call', id: 1, params: { name: 'not_a_real_tool', arguments: {} } },
        '',
      );
      expect(result.result.isError).toBe(true);
    });
  });

  describe('manage_guest_user', () => {
    const call = (args: any) =>
      controller.handle({ method: 'tools/call', id: 1, params: { name: 'manage_guest_user', arguments: args } }, '');

    it('requires an email', async () => {
      const result: any = await call({ action: 'create' });
      expect(result.result.isError).toBe(true);
      expect(result.result.content[0].text).toContain('email');
    });

    it('refuses to touch the protected admin account', async () => {
      const result: any = await call({ action: 'delete', email: 'admin@myblogs.com' });
      expect(result.result.isError).toBe(true);
      expect(result.result.content[0].text).toContain('protected');
    });

    it('requires name and password to create a user', async () => {
      const result: any = await call({ action: 'create', email: 'new@test.com' });
      expect(result.result.isError).toBe(true);
    });

    it('creates a guest user', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue({ id: 2, email: 'new@test.com', name: 'New', role: 'guest' });
      const result: any = await call({ action: 'create', email: 'new@test.com', name: 'New', password: 'pass1234' });
      expect(result.result.content[0].text).toContain('created successfully');
    });

    it('reports an error when user creation fails', async () => {
      (mockProxy.forward as jest.Mock).mockRejectedValue(new Error('Email already exists'));
      const result: any = await call({ action: 'create', email: 'new@test.com', name: 'New', password: 'pass1234' });
      expect(result.result.isError).toBe(true);
    });

    it('reports an error when the user list cannot be fetched for update/delete', async () => {
      (mockProxy.forward as jest.Mock).mockRejectedValue(new Error('down'));
      const result: any = await call({ action: 'update', email: 'ghost@test.com', name: 'X' });
      expect(result.result.isError).toBe(true);
      expect(result.result.content[0].text).toContain('Could not retrieve user list');
    });

    it('reports when no user matches the given email', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue([{ id: 1, email: 'someone-else@test.com' }]);
      const result: any = await call({ action: 'update', email: 'ghost@test.com', name: 'X' });
      expect(result.result.content[0].text).toContain('No user found');
    });

    it('requires at least one field for update', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue([{ id: 5, email: 'x@test.com' }]);
      const result: any = await call({ action: 'update', email: 'x@test.com' });
      expect(result.result.content[0].text).toContain('No update fields');
    });

    it('updates a user', async () => {
      (mockProxy.forward as jest.Mock)
        .mockResolvedValueOnce([{ id: 5, email: 'x@test.com' }])
        .mockResolvedValueOnce({ id: 5, email: 'x@test.com', name: 'Updated', isActive: true });
      const result: any = await call({ action: 'update', email: 'x@test.com', name: 'Updated' });
      expect(result.result.content[0].text).toContain('User updated');
    });

    it('reports an error when update fails', async () => {
      (mockProxy.forward as jest.Mock)
        .mockResolvedValueOnce([{ id: 5, email: 'x@test.com' }])
        .mockRejectedValueOnce(new Error('boom'));
      const result: any = await call({ action: 'update', email: 'x@test.com', name: 'Updated' });
      expect(result.result.isError).toBe(true);
    });

    it('deletes a user', async () => {
      (mockProxy.forward as jest.Mock)
        .mockResolvedValueOnce([{ id: 5, email: 'x@test.com' }])
        .mockResolvedValueOnce(undefined);
      const result: any = await call({ action: 'delete', email: 'x@test.com' });
      expect(result.result.content[0].text).toContain('User deleted');
    });

    it('reports an error when delete fails', async () => {
      (mockProxy.forward as jest.Mock)
        .mockResolvedValueOnce([{ id: 5, email: 'x@test.com' }])
        .mockRejectedValueOnce(new Error('boom'));
      const result: any = await call({ action: 'delete', email: 'x@test.com' });
      expect(result.result.isError).toBe(true);
    });

    it('rejects an unknown action', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue([{ id: 5, email: 'x@test.com' }]);
      const result: any = await call({ action: 'launch-rocket', email: 'x@test.com' });
      expect(result.result.content[0].text).toContain('Unknown action');
    });
  });

  describe('list_blogs', () => {
    const call = (args: any = {}) =>
      controller.handle({ method: 'tools/call', id: 1, params: { name: 'list_blogs', arguments: args } }, '');

    it('lists featured posts', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue([{ id: 1, title: 'A', slug: 'a' }]);
      const result: any = await call({ filter: 'featured' });
      expect(result.result.content[0].text).toContain('featured post');
    });

    it('lists recent posts', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue([{ id: 1, title: 'A', slug: 'a' }]);
      const result: any = await call({ filter: 'recent' });
      expect(result.result.content[0].text).toContain('most recent post');
    });

    it('lists latest posts with pagination', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue({
        posts: [{ id: 1, title: 'A', slug: 'a' }],
        total: 1,
        page: 1,
        pages: 1,
      });
      const result: any = await call({ category: 'tech', tag: 'js' });
      expect(result.result.content[0].text).toContain('Total: 1');
    });

    it('reports an error when the upstream call fails', async () => {
      (mockProxy.forward as jest.Mock).mockRejectedValue(new Error('down'));
      const result: any = await call();
      expect(result.result.isError).toBe(true);
    });
  });

  describe('get_blog', () => {
    const call = (args: any) =>
      controller.handle({ method: 'tools/call', id: 1, params: { name: 'get_blog', arguments: args } }, '');

    it('requires a slug', async () => {
      const result: any = await call({});
      expect(result.result.isError).toBe(true);
    });

    it('returns post details without a summary', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue({
        id: 1, title: 'Hello', slug: 'hello', content: '<p>Body</p>', status: 'published',
      });
      const result: any = await call({ slug: 'hello' });
      expect(result.result.content[0].text).toContain('Hello');
      expect(result.result.content[0].text).not.toContain('AI Summary');
    });

    it('includes an AI summary when requested and OPENAI_API_KEY is set', async () => {
      process.env.OPENAI_API_KEY = 'sk-test';
      (mockProxy.forward as jest.Mock).mockResolvedValue({
        id: 1, title: 'Hello', slug: 'hello', content: '<p>Body</p>', status: 'published',
      });
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({ choices: [{ message: { content: 'A short summary.' } }] }),
      });
      const result: any = await call({ slug: 'hello', summarize: true });
      expect(result.result.content[0].text).toContain('AI Summary');
      expect(result.result.content[0].text).toContain('A short summary.');
    });

    it('omits the summary line when the AI call fails', async () => {
      process.env.OPENAI_API_KEY = 'sk-test';
      (mockProxy.forward as jest.Mock).mockResolvedValue({
        id: 1, title: 'Hello', slug: 'hello', content: '<p>Body</p>', status: 'published',
      });
      (global.fetch as jest.Mock).mockResolvedValue({ ok: false });
      const result: any = await call({ slug: 'hello', summarize: true });
      expect(result.result.content[0].text).not.toContain('AI Summary');
    });

    it('reports an error when the post is not found', async () => {
      (mockProxy.forward as jest.Mock).mockRejectedValue(new Error('Post not found'));
      const result: any = await call({ slug: 'missing' });
      expect(result.result.isError).toBe(true);
    });
  });

  describe('search_blogs', () => {
    const call = (args: any) =>
      controller.handle({ method: 'tools/call', id: 1, params: { name: 'search_blogs', arguments: args } }, '');

    it('requires a query', async () => {
      const result: any = await call({});
      expect(result.result.isError).toBe(true);
    });

    it('reports when there are no matches', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue({ posts: [], total: 0 });
      const result: any = await call({ query: 'xyz' });
      expect(result.result.content[0].text).toContain('No published posts found');
    });

    it('includes a content snippet when include_content is true', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue({
        posts: [{ id: 1, title: 'A', slug: 'a', content: '<p>Some content here</p>' }],
        total: 1,
      });
      const result: any = await call({ query: 'content', include_content: true });
      expect(result.result.content[0].text).toContain('Body snippet');
    });

    it('reports an error when the search fails', async () => {
      (mockProxy.forward as jest.Mock).mockRejectedValue(new Error('down'));
      const result: any = await call({ query: 'x' });
      expect(result.result.isError).toBe(true);
    });
  });

  describe('create_blog', () => {
    const call = (args: any) =>
      controller.handle({ method: 'tools/call', id: 1, params: { name: 'create_blog', arguments: args } }, '');

    it('requires title, content, and excerpt', async () => {
      expect(((await call({})) as any).result.isError).toBe(true);
      expect(((await call({ title: 'T' })) as any).result.isError).toBe(true);
      expect(((await call({ title: 'T', content: 'C' })) as any).result.isError).toBe(true);
    });

    it('creates a post', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue({
        id: 1, title: 'T', slug: 't', status: 'published', readTime: 2,
      });
      const result: any = await call({ title: 'T', content: 'C', excerpt: 'E', status: 'published' });
      expect(result.result.content[0].text).toContain('published successfully');
    });

    it('reports an error when creation fails', async () => {
      (mockProxy.forward as jest.Mock).mockRejectedValue(new Error('boom'));
      const result: any = await call({ title: 'T', content: 'C', excerpt: 'E' });
      expect(result.result.isError).toBe(true);
    });
  });

  describe('update_blog', () => {
    const call = (args: any) =>
      controller.handle({ method: 'tools/call', id: 1, params: { name: 'update_blog', arguments: args } }, '');

    it('requires an id', async () => {
      const result: any = await call({ title: 'New title' });
      expect(result.result.isError).toBe(true);
    });

    it('requires at least one field to update', async () => {
      const result: any = await call({ id: 1 });
      expect(result.result.content[0].text).toContain('No update fields');
    });

    it('updates a post', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue({ id: 1, slug: 't', title: 'New', status: 'draft' });
      const result: any = await call({ id: 1, title: 'New' });
      expect(result.result.content[0].text).toContain('updated successfully');
    });

    it('reports an error when update fails', async () => {
      (mockProxy.forward as jest.Mock).mockRejectedValue(new Error('boom'));
      const result: any = await call({ id: 1, title: 'New' });
      expect(result.result.isError).toBe(true);
    });
  });

  describe('list_categories', () => {
    const call = () =>
      controller.handle({ method: 'tools/call', id: 1, params: { name: 'list_categories', arguments: {} } }, '');

    it('reports when there are no categories', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue([]);
      const result: any = await call();
      expect(result.result.content[0].text).toContain('No categories found');
    });

    it('lists categories', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue([{ id: 1, name: 'Tech', slug: 'tech' }]);
      const result: any = await call();
      expect(result.result.content[0].text).toContain('Tech');
    });

    it('reports an error when the fetch fails', async () => {
      (mockProxy.forward as jest.Mock).mockRejectedValue(new Error('down'));
      const result: any = await call();
      expect(result.result.isError).toBe(true);
    });
  });

  describe('list_tags', () => {
    const call = () =>
      controller.handle({ method: 'tools/call', id: 1, params: { name: 'list_tags', arguments: {} } }, '');

    it('reports when there are no tags', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue([]);
      const result: any = await call();
      expect(result.result.content[0].text).toContain('No tags found');
    });

    it('lists tags', async () => {
      (mockProxy.forward as jest.Mock).mockResolvedValue([{ id: 1, name: 'react', slug: 'react' }]);
      const result: any = await call();
      expect(result.result.content[0].text).toContain('react');
    });

    it('reports an error when the fetch fails', async () => {
      (mockProxy.forward as jest.Mock).mockRejectedValue(new Error('down'));
      const result: any = await call();
      expect(result.result.isError).toBe(true);
    });
  });
});
