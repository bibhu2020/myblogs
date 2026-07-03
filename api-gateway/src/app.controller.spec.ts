import { AppController } from './app.controller';
import { ProxyService } from './proxy.service';

describe('AppController', () => {
  const mockProxy = {
    forward: jest.fn(),
    forwardWithFile: jest.fn(),
  } as unknown as ProxyService;

  let controller: AppController;
  const req = { headers: { authorization: 'Bearer jwt-token' }, user: { id: 1 } };

  beforeEach(() => {
    jest.clearAllMocks();
    controller = new AppController(mockProxy);
  });

  describe('auth routes', () => {
    it('forwards login to the auth service', () => {
      const body = { email: 'a@test.com', password: 'x' };
      controller.login(body);
      expect(mockProxy.forward).toHaveBeenCalledWith('auth', '/auth/login', 'POST', body);
    });

    it('returns the request user for verify', () => {
      expect(controller.verify(req)).toBe(req.user);
    });
  });

  describe('user routes', () => {
    it('forwards getUsers with the auth header', () => {
      controller.getUsers(req);
      expect(mockProxy.forward).toHaveBeenCalledWith('auth', '/users', 'GET', null, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards createUser with body and auth header', () => {
      const body = { email: 'new@test.com' };
      controller.createUser(body, req);
      expect(mockProxy.forward).toHaveBeenCalledWith('auth', '/users', 'POST', body, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards updateUser with id, body and auth header', () => {
      const body = { name: 'New' };
      controller.updateUser('5', body, req);
      expect(mockProxy.forward).toHaveBeenCalledWith('auth', '/users/5', 'PUT', body, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards deleteUser with id and auth header', () => {
      controller.deleteUser('5', req);
      expect(mockProxy.forward).toHaveBeenCalledWith('auth', '/users/5', 'DELETE', null, { Authorization: 'Bearer jwt-token' });
    });
  });

  describe('post routes', () => {
    it('forwards getPosts with querystring params', () => {
      controller.getPosts({ category: 'tech' });
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/posts?category=tech', 'GET');
    });

    it('forwards getFeatured', () => {
      controller.getFeatured();
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/posts/featured', 'GET');
    });

    it('forwards getRecent', () => {
      controller.getRecent();
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/posts/recent', 'GET');
    });

    it('forwards getStats with auth header', () => {
      controller.getStats(req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/posts/stats', 'GET', null, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards getAdminPosts with query and auth header', () => {
      controller.getAdminPosts({ status: 'pending' }, req);
      expect(mockProxy.forward).toHaveBeenCalledWith(
        'blog', '/posts/admin?status=pending', 'GET', null, { Authorization: 'Bearer jwt-token' },
      );
    });

    it('forwards getPost by slug', () => {
      controller.getPost('hello-world');
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/posts/hello-world', 'GET');
    });

    it('forwards createPost with body and auth header', () => {
      const body = { title: 'New Post' };
      controller.createPost(body, req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/posts', 'POST', body, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards approvePost', () => {
      controller.approvePost('1', req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/posts/1/approve', 'PATCH', null, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards rejectPost', () => {
      controller.rejectPost('1', req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/posts/1/reject', 'PATCH', null, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards updatePost', () => {
      const body = { title: 'Updated' };
      controller.updatePost('1', body, req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/posts/1', 'PUT', body, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards deletePost', () => {
      controller.deletePost('1', req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/posts/1', 'DELETE', null, { Authorization: 'Bearer jwt-token' });
    });
  });

  describe('category routes', () => {
    it('forwards getCategories', () => {
      controller.getCategories();
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/categories', 'GET');
    });

    it('forwards createCategory', () => {
      const body = { name: 'Tech' };
      controller.createCategory(body, req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/categories', 'POST', body, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards updateCategory', () => {
      const body = { name: 'Updated' };
      controller.updateCategory('1', body, req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/categories/1', 'PUT', body, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards deleteCategory', () => {
      controller.deleteCategory('1', req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/categories/1', 'DELETE', null, { Authorization: 'Bearer jwt-token' });
    });
  });

  describe('tag routes', () => {
    it('forwards getTags', () => {
      controller.getTags();
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/tags', 'GET');
    });

    it('forwards createTag', () => {
      const body = { name: 'react' };
      controller.createTag(body, req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/tags', 'POST', body, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards createManyTags', () => {
      const body = { names: ['a', 'b'] };
      controller.createManyTags(body, req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/tags/many', 'POST', body, { Authorization: 'Bearer jwt-token' });
    });
  });

  describe('comment routes', () => {
    it('forwards getComments', () => {
      controller.getComments(req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/comments', 'GET', null, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards getPostComments', () => {
      controller.getPostComments('5');
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/comments/post/5', 'GET');
    });

    it('forwards createComment', () => {
      const body = { content: 'Nice!' };
      controller.createComment('5', body);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/comments/post/5', 'POST', body);
    });

    it('forwards approveComment', () => {
      controller.approveComment('9', req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/comments/9/approve', 'PUT', null, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards deleteComment', () => {
      controller.deleteComment('9', req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/comments/9', 'DELETE', null, { Authorization: 'Bearer jwt-token' });
    });
  });

  describe('media routes', () => {
    it('forwards getMedia', () => {
      controller.getMedia(req);
      expect(mockProxy.forward).toHaveBeenCalledWith('media', '/media', 'GET', null, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards uploadMedia via forwardWithFile', () => {
      const file = { originalname: 'a.jpg' } as Express.Multer.File;
      const body = { alt: 'photo' };
      controller.uploadMedia(file, body, req);
      expect(mockProxy.forwardWithFile).toHaveBeenCalledWith('/media/upload', file, body, 'Bearer jwt-token');
    });

    it('forwards deleteMedia', () => {
      controller.deleteMedia('7', req);
      expect(mockProxy.forward).toHaveBeenCalledWith('media', '/media/7', 'DELETE', null, { Authorization: 'Bearer jwt-token' });
    });
  });

  describe('story routes', () => {
    it('forwards getStories with querystring params', () => {
      controller.getStories({ genre: 'fantasy' });
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/stories?genre=fantasy', 'GET');
    });

    it('forwards getRecentStories', () => {
      controller.getRecentStories();
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/stories/recent', 'GET');
    });

    it('forwards getStoryStats', () => {
      controller.getStoryStats(req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/stories/stats', 'GET', null, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards getAdminStories', () => {
      controller.getAdminStories({ status: 'pending' }, req);
      expect(mockProxy.forward).toHaveBeenCalledWith(
        'blog', '/stories/admin?status=pending', 'GET', null, { Authorization: 'Bearer jwt-token' },
      );
    });

    it('forwards getStory by slug', () => {
      controller.getStory('a-story');
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/stories/a-story', 'GET');
    });

    it('forwards createStory', () => {
      const body = { title: 'A Story' };
      controller.createStory(body, req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/stories', 'POST', body, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards approveStory', () => {
      controller.approveStory('1', req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/stories/1/approve', 'PATCH', null, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards rejectStory', () => {
      controller.rejectStory('1', req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/stories/1/reject', 'PATCH', null, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards updateStory', () => {
      const body = { title: 'Updated' };
      controller.updateStory('1', body, req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/stories/1', 'PUT', body, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards deleteStory', () => {
      controller.deleteStory('1', req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/stories/1', 'DELETE', null, { Authorization: 'Bearer jwt-token' });
    });
  });

  describe('news routes', () => {
    it('forwards getNews with querystring params', () => {
      controller.getNews({ region: 'usa' });
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/news?region=usa', 'GET');
    });

    it('forwards refreshNews', () => {
      const body = { items: [] };
      controller.refreshNews(body, req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/news/refresh', 'POST', body, { Authorization: 'Bearer jwt-token' });
    });
  });

  describe('push routes', () => {
    it('forwards getPushVapidKey', () => {
      controller.getPushVapidKey();
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/push/vapid-key', 'GET');
    });

    it('forwards subscribePush', () => {
      const body = { endpoint: 'e' };
      controller.subscribePush(body);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/push/subscribe', 'POST', body);
    });

    it('forwards unsubscribePush', () => {
      const body = { endpoint: 'e' };
      controller.unsubscribePush(body);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/push/unsubscribe', 'DELETE', body);
    });
  });

  describe('agent run routes', () => {
    it('forwards dispatchAgent', () => {
      const body = { workflow: 'run-story-agent.yml' };
      controller.dispatchAgent(body, req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/agent-runs/dispatch', 'POST', body, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards createAgentRun', () => {
      const body = { agentType: 'story' };
      controller.createAgentRun(body);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/agent-runs', 'POST', body);
    });

    it('forwards updateAgentRun', () => {
      const body = { status: 'completed' };
      controller.updateAgentRun('r1', body);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/agent-runs/r1', 'PUT', body);
    });

    it('forwards getAgentRuns', () => {
      controller.getAgentRuns(req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/agent-runs', 'GET', null, { Authorization: 'Bearer jwt-token' });
    });

    it('forwards getAgentRun', () => {
      controller.getAgentRun('r1', req);
      expect(mockProxy.forward).toHaveBeenCalledWith('blog', '/agent-runs/r1', 'GET', null, { Authorization: 'Bearer jwt-token' });
    });
  });

  describe('textToSpeech', () => {
    const makeRes = () => ({
      status: jest.fn().mockReturnThis(),
      json: jest.fn().mockReturnThis(),
      set: jest.fn().mockReturnThis(),
      send: jest.fn().mockReturnThis(),
    });
    const ORIGINAL_ENV = process.env;

    beforeEach(() => {
      process.env = { ...ORIGINAL_ENV };
      delete process.env.TTS_SERVICE_URL;
      delete process.env.HF_TOKEN;
      global.fetch = jest.fn();
    });

    afterAll(() => {
      process.env = ORIGINAL_ENV;
    });

    it('rejects an empty text body', async () => {
      const res = makeRes();
      await controller.textToSpeech({ text: '  ' }, res as any);
      expect(res.status).toHaveBeenCalledWith(400);
    });

    it('returns 503 when no TTS backend is configured', async () => {
      const res = makeRes();
      await controller.textToSpeech({ text: 'hello' }, res as any);
      expect(res.status).toHaveBeenCalledWith(503);
    });

    it('uses the local Kokoro service when configured and it succeeds', async () => {
      process.env.TTS_SERVICE_URL = 'http://localhost:5050';
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        arrayBuffer: async () => new ArrayBuffer(8),
      });
      const res = makeRes();
      await controller.textToSpeech({ text: 'hello' }, res as any);
      expect(res.set).toHaveBeenCalledWith(expect.objectContaining({ 'Content-Type': 'audio/wav' }));
      expect(res.send).toHaveBeenCalled();
    });

    it('falls back to the HF facebook model when the local service fails', async () => {
      process.env.TTS_SERVICE_URL = 'http://localhost:5050';
      process.env.HF_TOKEN = 'hf-token';
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({ ok: false, status: 500 }) // local Kokoro fails
        .mockResolvedValueOnce({
          ok: true,
          arrayBuffer: async () => new ArrayBuffer(8),
          headers: { get: () => 'audio/flac' },
        });
      const res = makeRes();
      await controller.textToSpeech({ text: 'hello' }, res as any);
      expect(res.send).toHaveBeenCalled();
    });

    it('tries the maya1 model first for style="news"', async () => {
      process.env.HF_TOKEN = 'hf-token';
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        arrayBuffer: async () => new ArrayBuffer(8),
        headers: { get: () => 'audio/flac' },
      });
      const res = makeRes();
      await controller.textToSpeech({ text: 'breaking news', style: 'news' }, res as any);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('maya-research/maya1'),
        expect.anything(),
      );
      expect(res.send).toHaveBeenCalled();
    });

    it('returns 503 with aggregated errors when every backend fails', async () => {
      process.env.TTS_SERVICE_URL = 'http://localhost:5050';
      process.env.HF_TOKEN = 'hf-token';
      (global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 500 });
      const res = makeRes();
      await controller.textToSpeech({ text: 'hello' }, res as any);
      expect(res.status).toHaveBeenCalledWith(503);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({ message: expect.stringContaining('TTS unavailable') }),
      );
    });
  });
});
