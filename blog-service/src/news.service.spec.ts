import { Test, TestingModule } from '@nestjs/testing';
import { NewsService } from './news.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { NewsItem } from './news-item.entity';
import { PushService } from './push.service';
import { NotFoundException } from '@nestjs/common';

const makeQb = () => ({
  orderBy: jest.fn().mockReturnThis(),
  where: jest.fn().mockReturnThis(),
  getMany: jest.fn().mockResolvedValue([]),
});

const mockNewsRepo = {
  createQueryBuilder: jest.fn(),
  clear: jest.fn(),
  create: jest.fn(),
  save: jest.fn(),
  findOne: jest.fn(),
};

const mockPushService = { send: jest.fn() };

const mockItem = {
  id: 1,
  title: 'Breaking news',
  region: 'world',
  createdAt: new Date('2026-01-01'),
};

describe('NewsService', () => {
  let service: NewsService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        NewsService,
        { provide: getRepositoryToken(NewsItem), useValue: mockNewsRepo },
        { provide: PushService, useValue: mockPushService },
      ],
    }).compile();
    service = module.get<NewsService>(NewsService);
    jest.clearAllMocks();
    mockNewsRepo.createQueryBuilder.mockReturnValue(makeQb());
  });

  describe('findAll', () => {
    it('returns items and the most recent createdAt when items exist', async () => {
      const qb = makeQb();
      qb.getMany.mockResolvedValue([mockItem]);
      mockNewsRepo.createQueryBuilder.mockReturnValue(qb);
      const result = await service.findAll();
      expect(result.items).toHaveLength(1);
      expect(result.lastUpdated).toBe(mockItem.createdAt);
    });

    it('returns null lastUpdated when there are no items', async () => {
      const result = await service.findAll();
      expect(result.items).toHaveLength(0);
      expect(result.lastUpdated).toBeNull();
    });

    it('filters by region when a specific region is given', async () => {
      const qb = makeQb();
      mockNewsRepo.createQueryBuilder.mockReturnValue(qb);
      await service.findAll('usa');
      expect(qb.where).toHaveBeenCalledWith('n.region = :region', { region: 'usa' });
    });

    it('does not filter when region is "all"', async () => {
      const qb = makeQb();
      mockNewsRepo.createQueryBuilder.mockReturnValue(qb);
      await service.findAll('all');
      expect(qb.where).not.toHaveBeenCalled();
    });
  });

  describe('refresh', () => {
    it('clears existing items, saves the new ones, and sends a push notification', async () => {
      const entities = [mockItem];
      mockNewsRepo.create.mockReturnValue(entities);
      mockNewsRepo.save.mockResolvedValue(entities);
      const result = await service.refresh([{ title: 'Breaking news' } as any]);
      expect(mockNewsRepo.clear).toHaveBeenCalled();
      expect(mockNewsRepo.save).toHaveBeenCalledWith(entities);
      expect(mockPushService.send).toHaveBeenCalled();
      expect(result).toEqual({ count: 1, items: entities });
    });

    it('returns the saved entities with their assigned ids', async () => {
      const savedWithIds = [{ ...mockItem, id: 42 }];
      mockNewsRepo.create.mockReturnValue(savedWithIds);
      mockNewsRepo.save.mockResolvedValue(savedWithIds);
      const result = await service.refresh([{ title: 'Breaking news' } as any]);
      expect(result.items[0].id).toBe(42);
    });
  });

  describe('updateOne', () => {
    it('applies the partial update and saves it', async () => {
      const item = { ...mockItem };
      mockNewsRepo.findOne.mockResolvedValue(item);
      mockNewsRepo.save.mockImplementation(async (i) => i);
      const result = await service.updateOne(1, { audioUrl: '/uploads/news_1.mp3' } as any);
      expect(result.audioUrl).toBe('/uploads/news_1.mp3');
      expect(mockNewsRepo.save).toHaveBeenCalledWith(expect.objectContaining({ audioUrl: '/uploads/news_1.mp3' }));
    });

    it('throws NotFoundException when the item does not exist', async () => {
      mockNewsRepo.findOne.mockResolvedValue(null);
      await expect(service.updateOne(999, {})).rejects.toThrow(NotFoundException);
    });
  });
});
