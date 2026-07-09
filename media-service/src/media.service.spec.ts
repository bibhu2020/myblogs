import { Test, TestingModule } from '@nestjs/testing';
import { MediaService } from './media.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Media } from './media.entity';
import { NotFoundException, InternalServerErrorException } from '@nestjs/common';
import * as fs from 'fs';

// Node's built-in fs module exports non-configurable properties in this
// runtime, which makes jest.spyOn(fs, ...) throw "Cannot redefine property".
// Replacing the module with a mock factory sidesteps that entirely.
jest.mock('fs', () => ({
  ...jest.requireActual('fs'),
  readFileSync: jest.fn(),
  existsSync: jest.fn(),
  unlinkSync: jest.fn(),
}));

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

const mockAudioFile = {
  path: '/tmp/narration-1.mp3',
  filename: 'narration-1.mp3',
  originalname: 'narration.mp3',
  mimetype: 'audio/mpeg',
  size: 4096,
  buffer: Buffer.from(''),
} as Express.Multer.File;

const mockAudioMedia = {
  id: 2,
  filename: 'narration-1.mp3',
  originalName: 'narration.mp3',
  mimetype: 'audio/mpeg',
  size: 4096,
  url: '/uploads/narration-1.mp3',
  alt: 'narration.mp3',
  uploadedBy: 1,
  createdAt: new Date(),
};

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
    (fs.readFileSync as jest.Mock).mockReturnValue(Buffer.from('fake-image-data'));
    (fs.existsSync as jest.Mock).mockReturnValue(false);
    (fs.unlinkSync as jest.Mock).mockReset();
    global.fetch = jest.fn();
  });

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

    it('uses the GitHub raw URL and deletes the local file when upload succeeds', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      (global.fetch as jest.Mock).mockResolvedValue({ ok: true });
      (fs.existsSync as jest.Mock).mockReturnValue(true);
      mockMediaRepo.create.mockReturnValue(mockMedia);
      mockMediaRepo.save.mockResolvedValue(mockMedia);
      await service.save(mockFile, 1, 'alt');
      const arg = mockMediaRepo.create.mock.calls[0][0];
      expect(arg.url).toContain('raw.githubusercontent.com');
      expect(fs.unlinkSync).toHaveBeenCalledWith(mockFile.path);
    });

    it('falls back to local URL when GitHub responds with an error status', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      (global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 500, text: async () => 'server error' });
      mockMediaRepo.create.mockReturnValue(mockMedia);
      mockMediaRepo.save.mockResolvedValue(mockMedia);
      await service.save(mockFile, 1, 'alt');
      const arg = mockMediaRepo.create.mock.calls[0][0];
      expect(arg.url).toBe('/uploads/abc123.jpg');
      expect(fs.unlinkSync).not.toHaveBeenCalled();
    });

    it('falls back to local URL when the GitHub request throws', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      (global.fetch as jest.Mock).mockRejectedValue(new Error('network down'));
      mockMediaRepo.create.mockReturnValue(mockMedia);
      mockMediaRepo.save.mockResolvedValue(mockMedia);
      await service.save(mockFile, 1, 'alt');
      const arg = mockMediaRepo.create.mock.calls[0][0];
      expect(arg.url).toBe('/uploads/abc123.jpg');
    });

    it('uploads audio files to the myblogs/audio GitHub path, not myblogs/uploads', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      (global.fetch as jest.Mock).mockResolvedValue({ ok: true });
      (fs.existsSync as jest.Mock).mockReturnValue(true);
      mockMediaRepo.create.mockReturnValue(mockAudioMedia);
      mockMediaRepo.save.mockResolvedValue(mockAudioMedia);
      await service.save(mockAudioFile, 1, 'alt');
      const putUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(putUrl).toContain('/contents/myblogs/audio/');
      expect(putUrl).not.toContain('myblogs/uploads');
      const arg = mockMediaRepo.create.mock.calls[0][0];
      expect(arg.url).toContain('raw.githubusercontent.com');
      expect(arg.url).toContain('/myblogs/audio/');
    });

    it('still uploads image files to the myblogs/uploads GitHub path', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      (global.fetch as jest.Mock).mockResolvedValue({ ok: true });
      (fs.existsSync as jest.Mock).mockReturnValue(true);
      mockMediaRepo.create.mockReturnValue(mockMedia);
      mockMediaRepo.save.mockResolvedValue(mockMedia);
      await service.save(mockFile, 1, 'alt');
      const putUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(putUrl).toContain('/contents/myblogs/uploads/');
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

    it('deletes the GitHub file when it exists there, then removes the DB record', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      mockMediaRepo.findOne.mockResolvedValue(mockMedia);
      mockMediaRepo.remove.mockResolvedValue(undefined);
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({ ok: true, json: async () => ({ sha: 'abc' }) }) // GET
        .mockResolvedValueOnce({ ok: true }); // DELETE
      const result = await service.remove(1);
      expect(global.fetch).toHaveBeenCalledTimes(2);
      expect(mockMediaRepo.remove).toHaveBeenCalledWith(mockMedia);
      expect(result).toEqual({ message: 'Media deleted' });
    });

    it('skips the GitHub delete call when the file is not found there', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      mockMediaRepo.findOne.mockResolvedValue(mockMedia);
      mockMediaRepo.remove.mockResolvedValue(undefined);
      (global.fetch as jest.Mock).mockResolvedValue({ ok: false });
      const result = await service.remove(1);
      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(mockMediaRepo.remove).toHaveBeenCalledWith(mockMedia);
      expect(result).toEqual({ message: 'Media deleted' });
    });

    it('looks up audio files under the myblogs/audio GitHub path', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      mockMediaRepo.findOne.mockResolvedValue(mockAudioMedia);
      mockMediaRepo.remove.mockResolvedValue(undefined);
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({ ok: true, json: async () => ({ sha: 'abc' }) })
        .mockResolvedValueOnce({ ok: true });
      await service.remove(2);
      const getUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(getUrl).toContain('/contents/myblogs/audio/narration-1.mp3');
    });
  });
});
