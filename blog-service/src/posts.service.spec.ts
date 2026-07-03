import { Test, TestingModule } from '@nestjs/testing';
import { PostsService } from './posts.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Post, PostStatus } from './post.entity';
import { Category } from './category.entity';
import { Tag } from './tag.entity';
import { NotFoundException } from '@nestjs/common';
import { PushService } from './push.service';

const makeQb = () => ({
  leftJoinAndSelect: jest.fn().mockReturnThis(),
  orderBy: jest.fn().mockReturnThis(),
  andWhere: jest.fn().mockReturnThis(),
  where: jest.fn().mockReturnThis(),
  select: jest.fn().mockReturnThis(),
  skip: jest.fn().mockReturnThis(),
  take: jest.fn().mockReturnThis(),
  getCount: jest.fn().mockResolvedValue(0),
  getMany: jest.fn().mockResolvedValue([]),
  getOne: jest.fn().mockResolvedValue(null),
  getRawOne: jest.fn().mockResolvedValue({ total: '0' }),
});

const mockPostRepo = {
  createQueryBuilder: jest.fn(),
  findOne: jest.fn(),
  create: jest.fn(),
  save: jest.fn(),
  remove: jest.fn(),
  count: jest.fn(),
  find: jest.fn(),
  increment: jest.fn(),
};

const mockCatRepo = { findOne: jest.fn() };
const mockTagRepo = { findByIds: jest.fn() };
const mockPushService = { send: jest.fn() };

const mockPost = {
  id: 1,
  title: 'Hello World',
  slug: 'hello-world',
  content: 'Some content here',
  status: PostStatus.PUBLISHED,
  authorId: 1,
  authorName: 'Admin',
  views: 0,
  readTime: 1,
};

describe('PostsService', () => {
  let service: PostsService;

  beforeEach(async () => {
    const qb = makeQb();
    mockPostRepo.createQueryBuilder.mockReturnValue(qb);

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        PostsService,
        { provide: getRepositoryToken(Post), useValue: mockPostRepo },
        { provide: getRepositoryToken(Category), useValue: mockCatRepo },
        { provide: getRepositoryToken(Tag), useValue: mockTagRepo },
        { provide: PushService, useValue: mockPushService },
      ],
    }).compile();
    service = module.get<PostsService>(PostsService);
    jest.clearAllMocks();
    mockPostRepo.createQueryBuilder.mockReturnValue(makeQb());
    global.fetch = jest.fn();
  });

  describe('findOne', () => {
    it('returns post by id', async () => {
      mockPostRepo.findOne.mockResolvedValue(mockPost);
      const result = await service.findOne(1);
      expect(result.id).toBe(1);
      expect(result.title).toBe('Hello World');
    });

    it('throws NotFoundException when post missing', async () => {
      mockPostRepo.findOne.mockResolvedValue(null);
      await expect(service.findOne(999)).rejects.toThrow(NotFoundException);
    });
  });

  describe('findAll', () => {
    it('returns paginated posts with defaults', async () => {
      const qb = makeQb();
      qb.getCount.mockResolvedValue(3);
      qb.getMany.mockResolvedValue([mockPost]);
      mockPostRepo.createQueryBuilder.mockReturnValue(qb);
      const result = await service.findAll();
      expect(result.total).toBe(3);
      expect(result.posts).toHaveLength(1);
      expect(result.page).toBe(1);
    });

    it('returns empty result when no posts', async () => {
      const result = await service.findAll();
      expect(result.posts).toHaveLength(0);
      expect(result.total).toBe(0);
    });

    it('filters by explicit status, category, tag, and search', async () => {
      const qb = makeQb();
      mockPostRepo.createQueryBuilder.mockReturnValue(qb);
      await service.findAll({ status: 'draft', category: 'tech', tag: 'react', search: 'hello' });
      expect(qb.andWhere).toHaveBeenCalledWith('post.status = :status', { status: 'draft' });
      expect(qb.andWhere).toHaveBeenCalledWith('category.slug = :category', { category: 'tech' });
      expect(qb.andWhere).toHaveBeenCalledWith('tags.slug = :tag', { tag: 'react' });
    });
  });

  describe('findAllAdmin', () => {
    it('filters by status and search when provided', async () => {
      const qb = makeQb();
      mockPostRepo.createQueryBuilder.mockReturnValue(qb);
      await service.findAllAdmin({ status: 'pending', search: 'hello' });
      expect(qb.andWhere).toHaveBeenCalledWith('post.status = :status', { status: 'pending' });
      expect(qb.andWhere).toHaveBeenCalledWith('post.title LIKE :search', { search: '%hello%' });
    });

    it('returns paginated results with no filters', async () => {
      const qb = makeQb();
      qb.getCount.mockResolvedValue(1);
      qb.getMany.mockResolvedValue([mockPost]);
      mockPostRepo.createQueryBuilder.mockReturnValue(qb);
      const result = await service.findAllAdmin();
      expect(result.total).toBe(1);
    });
  });

  describe('findBySlug', () => {
    it('returns the post and increments views', async () => {
      const qb = makeQb();
      qb.getOne.mockResolvedValue(mockPost);
      mockPostRepo.createQueryBuilder.mockReturnValue(qb);
      const result = await service.findBySlug('hello-world');
      expect(result).toBe(mockPost);
      expect(mockPostRepo.increment).toHaveBeenCalledWith({ id: 1 }, 'views', 1);
    });

    it('throws NotFoundException when the post is missing', async () => {
      const qb = makeQb();
      qb.getOne.mockResolvedValue(null);
      mockPostRepo.createQueryBuilder.mockReturnValue(qb);
      await expect(service.findBySlug('missing')).rejects.toThrow(NotFoundException);
    });
  });

  describe('create', () => {
    it('generates slug from title', async () => {
      mockPostRepo.findOne.mockResolvedValue(null);
      mockPostRepo.create.mockReturnValue({ ...mockPost });
      mockPostRepo.save.mockResolvedValue(mockPost);
      await service.create({ title: 'Hello World', content: 'body' }, { id: 1, name: 'Admin' });
      const arg = mockPostRepo.create.mock.calls[0][0];
      expect(arg.slug).toBe('hello-world');
    });

    it('appends timestamp when slug is already taken', async () => {
      mockPostRepo.findOne.mockResolvedValue(mockPost);
      mockPostRepo.create.mockReturnValue({ ...mockPost });
      mockPostRepo.save.mockResolvedValue(mockPost);
      await service.create({ title: 'Hello World', content: 'body' }, { id: 1, name: 'Admin' });
      const arg = mockPostRepo.create.mock.calls[0][0];
      expect(arg.slug).toMatch(/^hello-world-\d+$/);
    });

    it('calculates readTime from word count', async () => {
      mockPostRepo.findOne.mockResolvedValue(null);
      mockPostRepo.create.mockReturnValue({ ...mockPost });
      mockPostRepo.save.mockResolvedValue(mockPost);
      const words = Array(400).fill('word').join(' ');
      await service.create({ title: 'Long Post', content: words }, { id: 1, name: 'Admin' });
      const arg = mockPostRepo.create.mock.calls[0][0];
      expect(arg.readTime).toBe(2);
    });

    it('attaches category when categoryId provided', async () => {
      mockPostRepo.findOne.mockResolvedValue(null);
      mockCatRepo.findOne.mockResolvedValue({ id: 1, name: 'Tech' });
      const post = { ...mockPost, category: null, tags: [] };
      mockPostRepo.create.mockReturnValue(post);
      mockPostRepo.save.mockResolvedValue({ ...post, category: { id: 1 } });
      await service.create({ title: 'Post', content: 'body', categoryId: 1 }, { id: 1, name: 'Admin' });
      expect(mockCatRepo.findOne).toHaveBeenCalledWith({ where: { id: 1 } });
    });

    it('attaches tags when tagIds provided', async () => {
      mockPostRepo.findOne.mockResolvedValue(null);
      mockTagRepo.findByIds.mockResolvedValue([{ id: 1 }, { id: 2 }]);
      const post = { ...mockPost, category: null, tags: [] };
      mockPostRepo.create.mockReturnValue(post);
      mockPostRepo.save.mockResolvedValue({ ...post, tags: [{ id: 1 }, { id: 2 }] });
      await service.create({ title: 'Post', content: 'body', tagIds: [1, 2] }, { id: 1, name: 'Admin' });
      expect(mockTagRepo.findByIds).toHaveBeenCalledWith([1, 2]);
    });

    it('serializes gallery to JSON and defaults author fields when no user given', async () => {
      mockPostRepo.findOne.mockResolvedValue(null);
      mockPostRepo.create.mockImplementation((p) => p);
      mockPostRepo.save.mockImplementation(async (p) => p);
      const result = await service.create(
        { title: 'Untitled', content: 'body', gallery: ['a.jpg', 'b.jpg'] },
        undefined,
      );
      expect(result.gallery).toBe(JSON.stringify(['a.jpg', 'b.jpg']));
      expect(result.authorId).toBe(0);
      expect(result.authorName).toBe('Anonymous');
    });
  });

  describe('update', () => {
    it('regenerates the slug when the title changes', async () => {
      mockPostRepo.findOne.mockResolvedValueOnce({ ...mockPost }).mockResolvedValueOnce(null);
      mockPostRepo.save.mockImplementation(async (p) => p);
      const result = await service.update(1, { title: 'A New Title' });
      expect(result.slug).toBe('a-new-title');
    });

    it('appends a timestamp when the new slug collides with a different post', async () => {
      mockPostRepo.findOne
        .mockResolvedValueOnce({ ...mockPost })
        .mockResolvedValueOnce({ id: 999, title: 'Other' });
      mockPostRepo.save.mockImplementation(async (p) => p);
      const result = await service.update(1, { title: 'A New Title' });
      expect(result.slug).toMatch(/^a-new-title-\d+$/);
    });

    it('keeps the slug when title is unchanged', async () => {
      mockPostRepo.findOne.mockResolvedValue({ ...mockPost });
      mockPostRepo.save.mockImplementation(async (p) => p);
      const result = await service.update(1, { views: 5 });
      expect(result.slug).toBe('hello-world');
    });

    it('clears the category when categoryId is set to falsy', async () => {
      mockPostRepo.findOne.mockResolvedValue({ ...mockPost, category: { id: 1 } });
      mockPostRepo.save.mockImplementation(async (p) => p);
      const result = await service.update(1, { categoryId: null });
      expect(result.category).toBeNull();
      expect(mockCatRepo.findOne).not.toHaveBeenCalled();
    });

    it('sets a new category when categoryId is provided', async () => {
      mockPostRepo.findOne.mockResolvedValue({ ...mockPost });
      mockCatRepo.findOne.mockResolvedValue({ id: 2, name: 'Science' });
      mockPostRepo.save.mockImplementation(async (p) => p);
      const result = await service.update(1, { categoryId: 2 });
      expect(result.category).toEqual({ id: 2, name: 'Science' });
    });

    it('clears tags when tagIds is an empty array', async () => {
      mockPostRepo.findOne.mockResolvedValue({ ...mockPost, tags: [{ id: 1 }] });
      mockPostRepo.save.mockImplementation(async (p) => p);
      const result = await service.update(1, { tagIds: [] });
      expect(result.tags).toEqual([]);
      expect(mockTagRepo.findByIds).not.toHaveBeenCalled();
    });

    it('sets new tags when tagIds is non-empty', async () => {
      mockPostRepo.findOne.mockResolvedValue({ ...mockPost });
      mockTagRepo.findByIds.mockResolvedValue([{ id: 3 }]);
      mockPostRepo.save.mockImplementation(async (p) => p);
      const result = await service.update(1, { tagIds: [3] });
      expect(result.tags).toEqual([{ id: 3 }]);
    });

    it('serializes gallery and recalculates readTime when content changes', async () => {
      mockPostRepo.findOne.mockResolvedValue({ ...mockPost });
      mockPostRepo.save.mockImplementation(async (p) => p);
      const words = Array(600).fill('word').join(' ');
      const result = await service.update(1, { gallery: ['a.jpg'], content: words });
      expect(result.gallery).toBe(JSON.stringify(['a.jpg']));
      expect(result.readTime).toBe(3);
    });
  });

  describe('remove', () => {
    it('removes post and returns message', async () => {
      mockPostRepo.findOne.mockResolvedValue(mockPost);
      mockPostRepo.remove.mockResolvedValue(undefined);
      const result = await service.remove(1);
      expect(result).toEqual({ message: 'Post deleted' });
    });

    it('throws NotFoundException when post missing', async () => {
      mockPostRepo.findOne.mockResolvedValue(null);
      await expect(service.remove(999)).rejects.toThrow(NotFoundException);
    });
  });

  describe('getStats', () => {
    it('returns post statistics object', async () => {
      mockPostRepo.count
        .mockResolvedValueOnce(10)
        .mockResolvedValueOnce(8)
        .mockResolvedValueOnce(1)
        .mockResolvedValueOnce(1);
      const qb = makeQb();
      qb.getRawOne.mockResolvedValue({ total: '500' });
      mockPostRepo.createQueryBuilder.mockReturnValue(qb);
      const result = await service.getStats();
      expect(result.total).toBe(10);
      expect(result.published).toBe(8);
      expect(result.totalViews).toBe('500');
    });
  });

  describe('approve', () => {
    it('throws when post is not pending', async () => {
      mockPostRepo.findOne.mockResolvedValue({ ...mockPost, status: PostStatus.PUBLISHED });
      await expect(service.approve(1)).rejects.toThrow();
    });

    it('publishes a pending post without a GitHub token configured', async () => {
      delete process.env.SECRET_TOKEN_GITHUB;
      const pending = { ...mockPost, status: PostStatus.PENDING };
      mockPostRepo.findOne.mockResolvedValue(pending);
      mockPostRepo.save.mockResolvedValue({ ...pending, status: PostStatus.PUBLISHED });
      const result = await service.approve(1);
      expect(result.status).toBe(PostStatus.PUBLISHED);
      expect(mockPushService.send).toHaveBeenCalled();
    });

    it('dispatches to GitHub and sends a push notification when a token is configured', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      (global.fetch as jest.Mock).mockResolvedValue({ ok: true, status: 204 });
      const pending = { ...mockPost, status: PostStatus.PENDING };
      mockPostRepo.findOne.mockResolvedValue(pending);
      mockPostRepo.save.mockResolvedValue({ ...pending, status: PostStatus.PUBLISHED });
      await service.approve(1);
      // dispatchPostDecision is fire-and-forget (`void`); flush the microtask queue.
      await new Promise((r) => setImmediate(r));
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/dispatches'),
        expect.objectContaining({ method: 'POST' }),
      );
    });

    it('logs but does not throw when the GitHub dispatch responds with an error', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      (global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 403, text: async () => 'forbidden' });
      const pending = { ...mockPost, status: PostStatus.PENDING };
      mockPostRepo.findOne.mockResolvedValue(pending);
      mockPostRepo.save.mockResolvedValue({ ...pending, status: PostStatus.PUBLISHED });
      const result = await service.approve(1);
      await new Promise((r) => setImmediate(r));
      expect(result.status).toBe(PostStatus.PUBLISHED);
    });

    it('logs but does not throw when the GitHub dispatch request itself throws', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      (global.fetch as jest.Mock).mockRejectedValue(new Error('network down'));
      const pending = { ...mockPost, status: PostStatus.PENDING };
      mockPostRepo.findOne.mockResolvedValue(pending);
      mockPostRepo.save.mockResolvedValue({ ...pending, status: PostStatus.PUBLISHED });
      const result = await service.approve(1);
      await new Promise((r) => setImmediate(r));
      expect(result.status).toBe(PostStatus.PUBLISHED);
    });
  });

  describe('reject', () => {
    it('throws when post is not pending', async () => {
      mockPostRepo.findOne.mockResolvedValue({ ...mockPost, status: PostStatus.PUBLISHED });
      await expect(service.reject(1)).rejects.toThrow();
    });

    it('removes a pending post', async () => {
      delete process.env.SECRET_TOKEN_GITHUB;
      const pending = { ...mockPost, status: PostStatus.PENDING };
      mockPostRepo.findOne.mockResolvedValue(pending);
      mockPostRepo.remove.mockResolvedValue(undefined);
      const result = await service.reject(1);
      expect(result.message).toContain('rejected');
    });
  });

  describe('getFeatured', () => {
    it('returns most viewed posts', async () => {
      mockPostRepo.find.mockResolvedValue([mockPost]);
      const result = await service.getFeatured();
      expect(result).toHaveLength(1);
    });
  });

  describe('getRecent', () => {
    it('returns recently published posts', async () => {
      mockPostRepo.find.mockResolvedValue([mockPost]);
      const result = await service.getRecent();
      expect(result).toHaveLength(1);
    });
  });
});
