import { Test, TestingModule } from '@nestjs/testing';
import { PostsService } from './posts.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Post, PostStatus } from './post.entity';
import { Category } from './category.entity';
import { Tag } from './tag.entity';
import { NotFoundException } from '@nestjs/common';

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
      ],
    }).compile();
    service = module.get<PostsService>(PostsService);
    jest.clearAllMocks();
    mockPostRepo.createQueryBuilder.mockReturnValue(makeQb());
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

    it('publishes a pending post', async () => {
      const pending = { ...mockPost, status: PostStatus.PENDING };
      mockPostRepo.findOne.mockResolvedValue(pending);
      mockPostRepo.save.mockResolvedValue({ ...pending, status: PostStatus.PUBLISHED });
      const result = await service.approve(1);
      expect(result.status).toBe(PostStatus.PUBLISHED);
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
