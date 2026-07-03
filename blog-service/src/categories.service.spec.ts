import { Test, TestingModule } from '@nestjs/testing';
import { CategoriesService } from './categories.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Category } from './category.entity';
import { NotFoundException } from '@nestjs/common';

const mockCatRepo = {
  find: jest.fn(),
  findOne: jest.fn(),
  create: jest.fn(),
  save: jest.fn(),
  remove: jest.fn(),
};

const mockCat = { id: 1, name: 'Technology', slug: 'technology', description: 'Tech posts', color: '#3b82f6', icon: 'cpu' };

describe('CategoriesService', () => {
  let service: CategoriesService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        CategoriesService,
        { provide: getRepositoryToken(Category), useValue: mockCatRepo },
      ],
    }).compile();
    service = module.get<CategoriesService>(CategoriesService);
    jest.clearAllMocks();
  });

  describe('findAll', () => {
    it('returns all categories', async () => {
      mockCatRepo.find.mockResolvedValue([mockCat]);
      const result = await service.findAll();
      expect(result).toHaveLength(1);
      expect(result[0].slug).toBe('technology');
    });
  });

  describe('findOne', () => {
    it('returns category when found', async () => {
      mockCatRepo.findOne.mockResolvedValue(mockCat);
      const result = await service.findOne(1);
      expect(result.name).toBe('Technology');
    });

    it('throws NotFoundException when not found', async () => {
      mockCatRepo.findOne.mockResolvedValue(null);
      await expect(service.findOne(99)).rejects.toThrow(NotFoundException);
    });
  });

  describe('create', () => {
    it('slugifies the name on create', async () => {
      const created = { ...mockCat, id: 2, name: 'Machine Learning', slug: 'machine-learning' };
      mockCatRepo.create.mockReturnValue(created);
      mockCatRepo.save.mockResolvedValue(created);
      await service.create({ name: 'Machine Learning' });
      const arg = mockCatRepo.create.mock.calls[0][0];
      expect(arg.slug).toBe('machine-learning');
    });

    it('saves optional fields', async () => {
      mockCatRepo.create.mockReturnValue(mockCat);
      mockCatRepo.save.mockResolvedValue(mockCat);
      await service.create({ name: 'Technology', description: 'Tech', color: '#blue', icon: 'cpu' });
      const arg = mockCatRepo.create.mock.calls[0][0];
      expect(arg.description).toBe('Tech');
      expect(arg.icon).toBe('cpu');
    });
  });

  describe('update', () => {
    it('updates slug when name changes', async () => {
      mockCatRepo.findOne.mockResolvedValue({ ...mockCat });
      mockCatRepo.save.mockResolvedValue({ ...mockCat, name: 'Science', slug: 'science' });
      await service.update(1, { name: 'Science' });
      const saved = mockCatRepo.save.mock.calls[0][0];
      expect(saved.slug).toBe('science');
    });

    it('throws NotFoundException for missing category', async () => {
      mockCatRepo.findOne.mockResolvedValue(null);
      await expect(service.update(99, { name: 'X' })).rejects.toThrow(NotFoundException);
    });

    it('leaves slug untouched when name is not part of the update', async () => {
      mockCatRepo.findOne.mockResolvedValue({ ...mockCat });
      mockCatRepo.save.mockImplementation(async (c) => c);
      const result = await service.update(1, { description: 'New description' });
      expect(result.slug).toBe('technology');
      expect(result.description).toBe('New description');
    });
  });

  describe('remove', () => {
    it('removes category and returns message', async () => {
      mockCatRepo.findOne.mockResolvedValue(mockCat);
      mockCatRepo.remove.mockResolvedValue(undefined);
      const result = await service.remove(1);
      expect(result).toEqual({ message: 'Category deleted' });
    });

    it('throws NotFoundException when category missing', async () => {
      mockCatRepo.findOne.mockResolvedValue(null);
      await expect(service.remove(99)).rejects.toThrow(NotFoundException);
    });
  });
});
