import { Test, TestingModule } from '@nestjs/testing';
import { StoriesService } from './stories.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Story, StoryStatus } from './story.entity';
import { PushService } from './push.service';
import { NotFoundException } from '@nestjs/common';

const makeQb = () => ({
  where: jest.fn().mockReturnThis(),
  andWhere: jest.fn().mockReturnThis(),
  orderBy: jest.fn().mockReturnThis(),
  select: jest.fn().mockReturnThis(),
  skip: jest.fn().mockReturnThis(),
  take: jest.fn().mockReturnThis(),
  getCount: jest.fn().mockResolvedValue(0),
  getMany: jest.fn().mockResolvedValue([]),
  getRawOne: jest.fn().mockResolvedValue({ total: '0' }),
});

const mockStoryRepo = {
  createQueryBuilder: jest.fn(),
  findOne: jest.fn(),
  create: jest.fn(),
  save: jest.fn(),
  remove: jest.fn(),
  count: jest.fn(),
  find: jest.fn(),
  increment: jest.fn(),
};

const mockPushService = { send: jest.fn() };

const mockStory = {
  id: 1,
  title: 'The Brave Fox',
  slug: 'the-brave-fox',
  content: 'Once upon a time',
  status: StoryStatus.PUBLISHED,
  authorId: 1,
  authorName: 'Admin',
  views: 0,
  readTime: 1,
};

describe('StoriesService', () => {
  let service: StoriesService;

  beforeEach(async () => {
    const qb = makeQb();
    mockStoryRepo.createQueryBuilder.mockReturnValue(qb);

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        StoriesService,
        { provide: getRepositoryToken(Story), useValue: mockStoryRepo },
        { provide: PushService, useValue: mockPushService },
      ],
    }).compile();
    service = module.get<StoriesService>(StoriesService);
    jest.clearAllMocks();
    mockStoryRepo.createQueryBuilder.mockReturnValue(makeQb());
  });

  describe('findAll', () => {
    it('returns paginated published stories', async () => {
      const qb = makeQb();
      qb.getCount.mockResolvedValue(2);
      qb.getMany.mockResolvedValue([mockStory]);
      mockStoryRepo.createQueryBuilder.mockReturnValue(qb);
      const result = await service.findAll();
      expect(result.total).toBe(2);
      expect(result.stories).toHaveLength(1);
    });

    it('filters by genre and search when provided', async () => {
      const qb = makeQb();
      mockStoryRepo.createQueryBuilder.mockReturnValue(qb);
      await service.findAll({ genre: 'fantasy', search: 'fox' });
      expect(qb.andWhere).toHaveBeenCalledWith('story.genre = :genre', { genre: 'fantasy' });
      expect(qb.andWhere).toHaveBeenCalledWith(
        '(story.title ILIKE :search OR story.excerpt ILIKE :search OR story.content ILIKE :search)',
        { search: '%fox%' },
      );
    });
  });

  describe('findAllAdmin', () => {
    it('filters by status and search when provided', async () => {
      const qb = makeQb();
      mockStoryRepo.createQueryBuilder.mockReturnValue(qb);
      await service.findAllAdmin({ status: 'pending', search: 'fox' });
      expect(qb.andWhere).toHaveBeenCalledWith('story.status = :status', { status: 'pending' });
      expect(qb.andWhere).toHaveBeenCalledWith('story.title ILIKE :search', { search: '%fox%' });
    });

    it('returns paginated results with no filters', async () => {
      const qb = makeQb();
      qb.getCount.mockResolvedValue(1);
      qb.getMany.mockResolvedValue([mockStory]);
      mockStoryRepo.createQueryBuilder.mockReturnValue(qb);
      const result = await service.findAllAdmin();
      expect(result.total).toBe(1);
    });
  });

  describe('findBySlug', () => {
    it('returns the story and increments views', async () => {
      mockStoryRepo.findOne.mockResolvedValue(mockStory);
      const result = await service.findBySlug('the-brave-fox');
      expect(result).toBe(mockStory);
      expect(mockStoryRepo.increment).toHaveBeenCalledWith({ id: 1 }, 'views', 1);
    });

    it('throws NotFoundException when the story is missing', async () => {
      mockStoryRepo.findOne.mockResolvedValue(null);
      await expect(service.findBySlug('missing')).rejects.toThrow(NotFoundException);
    });
  });

  describe('findOne', () => {
    it('returns the story by id', async () => {
      mockStoryRepo.findOne.mockResolvedValue(mockStory);
      const result = await service.findOne(1);
      expect(result).toBe(mockStory);
    });

    it('throws NotFoundException when missing', async () => {
      mockStoryRepo.findOne.mockResolvedValue(null);
      await expect(service.findOne(999)).rejects.toThrow(NotFoundException);
    });
  });

  describe('create', () => {
    it('generates a slug and read time from the content', async () => {
      mockStoryRepo.findOne.mockResolvedValue(null);
      mockStoryRepo.create.mockImplementation((s) => s);
      mockStoryRepo.save.mockImplementation(async (s) => s);
      const words = Array(400).fill('word').join(' ');
      const result = await service.create({ title: 'The Brave Fox', content: words }, { id: 1, name: 'Admin' });
      expect(result.slug).toBe('the-brave-fox');
      expect(result.readTime).toBe(2);
    });

    it('appends a timestamp when the slug already exists', async () => {
      mockStoryRepo.findOne.mockResolvedValue(mockStory);
      mockStoryRepo.create.mockImplementation((s) => s);
      mockStoryRepo.save.mockImplementation(async (s) => s);
      const result = await service.create({ title: 'The Brave Fox', content: 'text' }, { id: 1, name: 'Admin' });
      expect(result.slug).toMatch(/^the-brave-fox-\d+$/);
    });

    it('defaults authorName to Anonymous when neither dto nor user provide one', async () => {
      mockStoryRepo.findOne.mockResolvedValue(null);
      mockStoryRepo.create.mockImplementation((s) => s);
      mockStoryRepo.save.mockImplementation(async (s) => s);
      const result = await service.create({ title: 'Untitled', content: 'text' }, {});
      expect(result.authorName).toBe('Anonymous');
      expect(result.authorId).toBe(0);
    });
  });

  describe('update', () => {
    it('regenerates the slug when the title changes', async () => {
      mockStoryRepo.findOne.mockResolvedValueOnce({ ...mockStory }).mockResolvedValueOnce(null);
      mockStoryRepo.save.mockImplementation(async (s) => s);
      const result = await service.update(1, { title: 'A New Title' });
      expect(result.slug).toBe('a-new-title');
    });

    it('keeps the slug when title is unchanged', async () => {
      mockStoryRepo.findOne.mockResolvedValue({ ...mockStory });
      mockStoryRepo.save.mockImplementation(async (s) => s);
      const result = await service.update(1, { views: 5 });
      expect(result.slug).toBe('the-brave-fox');
    });

    it('recalculates readTime when content changes', async () => {
      mockStoryRepo.findOne.mockResolvedValue({ ...mockStory });
      mockStoryRepo.save.mockImplementation(async (s) => s);
      const words = Array(600).fill('word').join(' ');
      const result = await service.update(1, { content: words });
      expect(result.readTime).toBe(3);
    });
  });

  describe('remove', () => {
    it('removes the story', async () => {
      mockStoryRepo.findOne.mockResolvedValue(mockStory);
      mockStoryRepo.remove.mockResolvedValue(undefined);
      const result = await service.remove(1);
      expect(result).toEqual({ message: 'Story deleted' });
    });
  });

  describe('approve', () => {
    it('throws when the story is not pending', async () => {
      mockStoryRepo.findOne.mockResolvedValue({ ...mockStory, status: StoryStatus.PUBLISHED });
      await expect(service.approve(1)).rejects.toThrow();
    });

    it('publishes a pending story and sends a push notification', async () => {
      const pending = { ...mockStory, status: StoryStatus.PENDING };
      mockStoryRepo.findOne.mockResolvedValue(pending);
      mockStoryRepo.save.mockResolvedValue({ ...pending, status: StoryStatus.PUBLISHED });
      const result = await service.approve(1);
      expect(result.status).toBe(StoryStatus.PUBLISHED);
      expect(mockPushService.send).toHaveBeenCalled();
    });
  });

  describe('reject', () => {
    it('throws when the story is not pending', async () => {
      mockStoryRepo.findOne.mockResolvedValue({ ...mockStory, status: StoryStatus.PUBLISHED });
      await expect(service.reject(1)).rejects.toThrow();
    });

    it('removes a pending story', async () => {
      const pending = { ...mockStory, status: StoryStatus.PENDING };
      mockStoryRepo.findOne.mockResolvedValue(pending);
      mockStoryRepo.remove.mockResolvedValue(undefined);
      const result = await service.reject(1);
      expect(result.message).toContain('rejected');
    });
  });

  describe('getStats', () => {
    it('returns story statistics', async () => {
      mockStoryRepo.count
        .mockResolvedValueOnce(5)
        .mockResolvedValueOnce(3)
        .mockResolvedValueOnce(1)
        .mockResolvedValueOnce(1);
      const qb = makeQb();
      qb.getRawOne.mockResolvedValue({ total: '100' });
      mockStoryRepo.createQueryBuilder.mockReturnValue(qb);
      const result = await service.getStats();
      expect(result.total).toBe(5);
      expect(result.published).toBe(3);
      expect(result.totalViews).toBe('100');
    });
  });

  describe('getRecent', () => {
    it('returns recently published stories', async () => {
      mockStoryRepo.find.mockResolvedValue([mockStory]);
      const result = await service.getRecent();
      expect(result).toHaveLength(1);
    });
  });
});
