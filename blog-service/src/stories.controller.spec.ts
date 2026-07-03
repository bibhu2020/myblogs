import { StoriesController } from './stories.controller';
import { StoriesService } from './stories.service';

describe('StoriesController', () => {
  const mockStoriesService = {
    findAll: jest.fn(),
    getRecent: jest.fn(),
    getStats: jest.fn(),
    findAllAdmin: jest.fn(),
    findBySlug: jest.fn(),
    create: jest.fn(),
    approve: jest.fn(),
    reject: jest.fn(),
    update: jest.fn(),
    remove: jest.fn(),
  } as unknown as StoriesService;

  let controller: StoriesController;

  beforeEach(() => {
    jest.clearAllMocks();
    controller = new StoriesController(mockStoriesService);
  });

  it('delegates findAll to StoriesService with the query', () => {
    const query = { genre: 'fantasy' };
    controller.findAll(query);
    expect(mockStoriesService.findAll).toHaveBeenCalledWith(query);
  });

  it('delegates getRecent to StoriesService', () => {
    controller.getRecent();
    expect(mockStoriesService.getRecent).toHaveBeenCalled();
  });

  it('delegates getStats to StoriesService', () => {
    controller.getStats();
    expect(mockStoriesService.getStats).toHaveBeenCalled();
  });

  it('delegates findAllAdmin to StoriesService with the query', () => {
    const query = { status: 'pending' };
    controller.findAllAdmin(query);
    expect(mockStoriesService.findAllAdmin).toHaveBeenCalledWith(query);
  });

  it('delegates findBySlug to StoriesService', () => {
    controller.findBySlug('a-story');
    expect(mockStoriesService.findBySlug).toHaveBeenCalledWith('a-story');
  });

  it('delegates create to StoriesService with the dto and request user', () => {
    const dto = { title: 'A Story' };
    const req = { user: { id: 1, name: 'Admin' } };
    controller.create(dto, req);
    expect(mockStoriesService.create).toHaveBeenCalledWith(dto, req.user);
  });

  it('delegates approve to StoriesService with a numeric id', () => {
    controller.approve('3');
    expect(mockStoriesService.approve).toHaveBeenCalledWith(3);
  });

  it('delegates reject to StoriesService with a numeric id', () => {
    controller.reject('3');
    expect(mockStoriesService.reject).toHaveBeenCalledWith(3);
  });

  it('delegates update to StoriesService with a numeric id and dto', () => {
    const dto = { title: 'Updated' };
    controller.update('3', dto);
    expect(mockStoriesService.update).toHaveBeenCalledWith(3, dto);
  });

  it('delegates remove to StoriesService with a numeric id', () => {
    controller.remove('3');
    expect(mockStoriesService.remove).toHaveBeenCalledWith(3);
  });
});
