import { PostsController } from './posts.controller';
import { PostsService } from './posts.service';

describe('PostsController', () => {
  const mockPostsService = {
    findAll: jest.fn(),
    getFeatured: jest.fn(),
    getRecent: jest.fn(),
    getStats: jest.fn(),
    findAllAdmin: jest.fn(),
    findBySlug: jest.fn(),
    create: jest.fn(),
    approve: jest.fn(),
    reject: jest.fn(),
    update: jest.fn(),
    remove: jest.fn(),
  } as unknown as PostsService;

  let controller: PostsController;

  beforeEach(() => {
    jest.clearAllMocks();
    controller = new PostsController(mockPostsService);
  });

  it('delegates findAll to PostsService with the query', () => {
    const query = { category: 'tech' };
    controller.findAll(query);
    expect(mockPostsService.findAll).toHaveBeenCalledWith(query);
  });

  it('delegates getFeatured to PostsService', () => {
    controller.getFeatured();
    expect(mockPostsService.getFeatured).toHaveBeenCalled();
  });

  it('delegates getRecent to PostsService', () => {
    controller.getRecent();
    expect(mockPostsService.getRecent).toHaveBeenCalled();
  });

  it('delegates getStats to PostsService', () => {
    controller.getStats();
    expect(mockPostsService.getStats).toHaveBeenCalled();
  });

  it('delegates findAllAdmin to PostsService with the query', () => {
    const query = { status: 'pending' };
    controller.findAllAdmin(query);
    expect(mockPostsService.findAllAdmin).toHaveBeenCalledWith(query);
  });

  it('delegates findBySlug to PostsService', () => {
    controller.findBySlug('a-post');
    expect(mockPostsService.findBySlug).toHaveBeenCalledWith('a-post');
  });

  it('delegates create to PostsService with the dto and request user', () => {
    const dto = { title: 'A Post' };
    const req = { user: { id: 1, name: 'Admin' } };
    controller.create(dto, req);
    expect(mockPostsService.create).toHaveBeenCalledWith(dto, req.user);
  });

  it('delegates approve to PostsService with a numeric id', () => {
    controller.approve('3');
    expect(mockPostsService.approve).toHaveBeenCalledWith(3);
  });

  it('delegates reject to PostsService with a numeric id', () => {
    controller.reject('3');
    expect(mockPostsService.reject).toHaveBeenCalledWith(3);
  });

  it('delegates update to PostsService with a numeric id and dto', () => {
    const dto = { title: 'Updated' };
    controller.update('3', dto);
    expect(mockPostsService.update).toHaveBeenCalledWith(3, dto);
  });

  it('delegates remove to PostsService with a numeric id', () => {
    controller.remove('3');
    expect(mockPostsService.remove).toHaveBeenCalledWith(3);
  });
});
