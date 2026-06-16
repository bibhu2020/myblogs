import { Test, TestingModule } from '@nestjs/testing';
import { TagsService } from './tags.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Tag } from './tag.entity';

const mockTagRepo = {
  find: jest.fn(),
  findOne: jest.fn(),
  create: jest.fn(),
  save: jest.fn(),
  remove: jest.fn(),
};

const mockTag = { id: 1, name: 'JavaScript', slug: 'javascript' };

describe('TagsService', () => {
  let service: TagsService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        TagsService,
        { provide: getRepositoryToken(Tag), useValue: mockTagRepo },
      ],
    }).compile();
    service = module.get<TagsService>(TagsService);
    jest.clearAllMocks();
  });

  describe('findAll', () => {
    it('returns all tags', async () => {
      mockTagRepo.find.mockResolvedValue([mockTag]);
      const result = await service.findAll();
      expect(result).toHaveLength(1);
      expect(result[0].name).toBe('JavaScript');
    });
  });

  describe('create', () => {
    it('returns existing tag when slug already exists', async () => {
      mockTagRepo.findOne.mockResolvedValue(mockTag);
      const result = await service.create({ name: 'JavaScript' });
      expect(result).toEqual(mockTag);
      expect(mockTagRepo.save).not.toHaveBeenCalled();
    });

    it('creates and saves new tag when slug is unique', async () => {
      mockTagRepo.findOne.mockResolvedValue(null);
      const newTag = { id: 2, name: 'TypeScript', slug: 'typescript' };
      mockTagRepo.create.mockReturnValue(newTag);
      mockTagRepo.save.mockResolvedValue(newTag);
      const result = await service.create({ name: 'TypeScript' });
      expect(mockTagRepo.save).toHaveBeenCalledTimes(1);
      expect(result.slug).toBe('typescript');
    });

    it('slugifies multi-word tag names', async () => {
      mockTagRepo.findOne.mockResolvedValue(null);
      mockTagRepo.create.mockImplementation(d => d);
      mockTagRepo.save.mockImplementation(d => Promise.resolve({ ...d, id: 10 }));
      await service.create({ name: 'Machine Learning' });
      const arg = mockTagRepo.create.mock.calls[0][0];
      expect(arg.slug).toBe('machine-learning');
    });
  });

  describe('createMany', () => {
    it('creates multiple tags in parallel', async () => {
      mockTagRepo.findOne.mockResolvedValue(null);
      mockTagRepo.create.mockImplementation(d => d);
      mockTagRepo.save.mockImplementation(d => Promise.resolve({ ...d, id: Math.floor(Math.random() * 100) }));
      const result = await service.createMany(['Vue', 'React', 'Angular']);
      expect(result).toHaveLength(3);
    });

    it('returns existing tags without duplicating', async () => {
      mockTagRepo.findOne.mockResolvedValue(mockTag);
      const result = await service.createMany(['JavaScript']);
      expect(result).toHaveLength(1);
      expect(mockTagRepo.save).not.toHaveBeenCalled();
    });
  });

  describe('remove', () => {
    it('removes tag when found', async () => {
      mockTagRepo.findOne.mockResolvedValue(mockTag);
      mockTagRepo.remove.mockResolvedValue(undefined);
      const result = await service.remove(1);
      expect(mockTagRepo.remove).toHaveBeenCalledWith(mockTag);
      expect(result).toEqual({ message: 'Tag deleted' });
    });

    it('returns message without error when tag not found', async () => {
      mockTagRepo.findOne.mockResolvedValue(null);
      const result = await service.remove(99);
      expect(mockTagRepo.remove).not.toHaveBeenCalled();
      expect(result).toEqual({ message: 'Tag deleted' });
    });
  });
});
