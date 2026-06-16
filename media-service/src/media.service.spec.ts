import { Test, TestingModule } from '@nestjs/testing';
import { MediaService } from './media.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Media } from './media.entity';
import { NotFoundException, InternalServerErrorException } from '@nestjs/common';
import * as fs from 'fs';

const mockMediaRepo = {
  find: jest.fn(),
  findOne: jest.fn(),
  create: jest.fn(),
  save: jest.fn(),
  remove: jest.fn(),
};

const mockMedia = {
  id: 1,
  filename: 'abc123.jpg',
  originalName: 'photo.jpg',
  mimetype: 'image/jpeg',
  size: 1024,
  url: '/uploads/abc123.jpg',
  alt: 'photo.jpg',
  uploadedBy: 1,
  createdAt: new Date(),
};

const mockFile = {
  path: '/tmp/abc123.jpg',
  filename: 'abc123.jpg',
  originalname: 'photo.jpg',
  mimetype: 'image/jpeg',
  size: 1024,
  buffer: Buffer.from(''),
} as Express.Multer.File;

describe('MediaService', () => {
  let service: MediaService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        MediaService,
        { provide: getRepositoryToken(Media), useValue: mockMediaRepo },
      ],
    }).compile();
    service = module.get<MediaService>(MediaService);
    jest.clearAllMocks();
    jest.spyOn(fs, 'readFileSync').mockReturnValue(Buffer.from('fake-image-data'));
    jest.spyOn(fs, 'existsSync').mockReturnValue(false);
  });

  afterEach(() => jest.restoreAllMocks());

  describe('findAll', () => {
    it('returns all media ordered by date', async () => {
      mockMediaRepo.find.mockResolvedValue([mockMedia]);
      const result = await service.findAll();
      expect(result).toHaveLength(1);
      expect(result[0].filename).toBe('abc123.jpg');
    });

    it('returns empty array when no media', async () => {
      mockMediaRepo.find.mockResolvedValue([]);
      const result = await service.findAll();
      expect(result).toHaveLength(0);
    });
  });

  describe('save', () => {
    it('falls back to local URL when SECRET_TOKEN_GITHUB not set', async () => {
      delete process.env.SECRET_TOKEN_GITHUB;
      mockMediaRepo.create.mockReturnValue(mockMedia);
      mockMediaRepo.save.mockResolvedValue(mockMedia);
      await service.save(mockFile, 1, 'alt text');
      const arg = mockMediaRepo.create.mock.calls[0][0];
      expect(arg.url).toBe('/uploads/abc123.jpg');
    });

    it('stores provided alt text', async () => {
      delete process.env.SECRET_TOKEN_GITHUB;
      mockMediaRepo.create.mockReturnValue(mockMedia);
      mockMediaRepo.save.mockResolvedValue(mockMedia);
      await service.save(mockFile, 1, 'my custom alt');
      const arg = mockMediaRepo.create.mock.calls[0][0];
      expect(arg.alt).toBe('my custom alt');
    });

    it('uses originalname as alt when alt not provided', async () => {
      delete process.env.SECRET_TOKEN_GITHUB;
      mockMediaRepo.create.mockReturnValue(mockMedia);
      mockMediaRepo.save.mockResolvedValue(mockMedia);
      await service.save(mockFile, 1);
      const arg = mockMediaRepo.create.mock.calls[0][0];
      expect(arg.alt).toBe('photo.jpg');
    });

    it('sets uploadedBy to the provided userId', async () => {
      delete process.env.SECRET_TOKEN_GITHUB;
      mockMediaRepo.create.mockReturnValue(mockMedia);
      mockMediaRepo.save.mockResolvedValue(mockMedia);
      await service.save(mockFile, 42, 'alt');
      const arg = mockMediaRepo.create.mock.calls[0][0];
      expect(arg.uploadedBy).toBe(42);
    });
  });

  describe('remove', () => {
    it('throws NotFoundException when media not found', async () => {
      mockMediaRepo.findOne.mockResolvedValue(null);
      await expect(service.remove(99)).rejects.toThrow(NotFoundException);
    });

    it('throws InternalServerErrorException when token not configured', async () => {
      delete process.env.SECRET_TOKEN_GITHUB;
      mockMediaRepo.findOne.mockResolvedValue(mockMedia);
      await expect(service.remove(1)).rejects.toThrow(InternalServerErrorException);
    });
  });
});
