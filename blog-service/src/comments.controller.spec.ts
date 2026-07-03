import { CommentsController } from './comments.controller';
import { CommentsService } from './comments.service';

describe('CommentsController', () => {
  const mockCommentsService = {
    findAll: jest.fn(),
    findByPost: jest.fn(),
    create: jest.fn(),
    approve: jest.fn(),
    remove: jest.fn(),
  } as unknown as CommentsService;

  let controller: CommentsController;

  beforeEach(() => {
    jest.clearAllMocks();
    controller = new CommentsController(mockCommentsService);
  });

  it('delegates findAll to CommentsService', () => {
    controller.findAll();
    expect(mockCommentsService.findAll).toHaveBeenCalled();
  });

  it('delegates findByPost to CommentsService with a numeric postId', () => {
    controller.findByPost('5');
    expect(mockCommentsService.findByPost).toHaveBeenCalledWith(5);
  });

  it('delegates create to CommentsService with a numeric postId and body', () => {
    const dto = { content: 'hi' };
    controller.create('5', dto);
    expect(mockCommentsService.create).toHaveBeenCalledWith(5, dto);
  });

  it('delegates approve to CommentsService with a numeric id', () => {
    controller.approve('9');
    expect(mockCommentsService.approve).toHaveBeenCalledWith(9);
  });

  it('delegates remove to CommentsService with a numeric id', () => {
    controller.remove('9');
    expect(mockCommentsService.remove).toHaveBeenCalledWith(9);
  });
});
