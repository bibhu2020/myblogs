import { Test, TestingModule } from '@nestjs/testing';
import { CommentsService } from './comments.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Comment } from './comment.entity';
import { Post } from './post.entity';

const mockCommentRepo = {
  find: jest.fn(),
  findOne: jest.fn(),
  create: jest.fn(),
  save: jest.fn(),
  update: jest.fn(),
  remove: jest.fn(),
};

const mockPostRepo = {
  findOne: jest.fn(),
};

const mockComment = {
  id: 1,
  content: 'Nice post!',
  authorName: 'Jane',
  approved: false,
};

describe('CommentsService', () => {
  let service: CommentsService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        CommentsService,
        { provide: getRepositoryToken(Comment), useValue: mockCommentRepo },
        { provide: getRepositoryToken(Post), useValue: mockPostRepo },
      ],
    }).compile();
    service = module.get<CommentsService>(CommentsService);
    jest.clearAllMocks();
  });

  describe('findByPost', () => {
    it('returns only approved comments for the post, oldest first', async () => {
      mockCommentRepo.find.mockResolvedValue([mockComment]);
      const result = await service.findByPost(1);
      expect(mockCommentRepo.find).toHaveBeenCalledWith({
        where: { post: { id: 1 }, approved: true },
        order: { createdAt: 'ASC' },
      });
      expect(result).toHaveLength(1);
    });
  });

  describe('create', () => {
    it('attaches the post and defaults approved to false', async () => {
      const post = { id: 1, title: 'Hello' };
      mockPostRepo.findOne.mockResolvedValue(post);
      mockCommentRepo.create.mockReturnValue(mockComment);
      mockCommentRepo.save.mockResolvedValue(mockComment);
      await service.create(1, { content: 'Nice post!', authorName: 'Jane' });
      const arg = mockCommentRepo.create.mock.calls[0][0];
      expect(arg.post).toBe(post);
      expect(arg.approved).toBe(false);
    });
  });

  describe('approve', () => {
    it('marks the comment approved and returns it', async () => {
      mockCommentRepo.update.mockResolvedValue(undefined);
      mockCommentRepo.findOne.mockResolvedValue({ ...mockComment, approved: true });
      const result = await service.approve(1);
      expect(mockCommentRepo.update).toHaveBeenCalledWith(1, { approved: true });
      expect(result.approved).toBe(true);
    });
  });

  describe('remove', () => {
    it('removes the comment when found', async () => {
      mockCommentRepo.findOne.mockResolvedValue(mockComment);
      mockCommentRepo.remove.mockResolvedValue(undefined);
      const result = await service.remove(1);
      expect(mockCommentRepo.remove).toHaveBeenCalledWith(mockComment);
      expect(result).toEqual({ message: 'Comment deleted' });
    });

    it('does nothing when the comment is already gone', async () => {
      mockCommentRepo.findOne.mockResolvedValue(null);
      const result = await service.remove(999);
      expect(mockCommentRepo.remove).not.toHaveBeenCalled();
      expect(result).toEqual({ message: 'Comment deleted' });
    });
  });

  describe('findAll', () => {
    it('returns all comments with their post relation, newest first', async () => {
      mockCommentRepo.find.mockResolvedValue([mockComment]);
      const result = await service.findAll();
      expect(mockCommentRepo.find).toHaveBeenCalledWith({
        relations: ['post'],
        order: { createdAt: 'DESC' },
      });
      expect(result).toHaveLength(1);
    });
  });
});
