import { TagsController } from './tags.controller';
import { TagsService } from './tags.service';

describe('TagsController', () => {
  const mockTagsService = {
    findAll: jest.fn(),
    create: jest.fn(),
    createMany: jest.fn(),
    remove: jest.fn(),
  } as unknown as TagsService;

  let controller: TagsController;

  beforeEach(() => {
    jest.clearAllMocks();
    controller = new TagsController(mockTagsService);
  });

  it('delegates findAll to TagsService', () => {
    controller.findAll();
    expect(mockTagsService.findAll).toHaveBeenCalled();
  });

  it('delegates create to TagsService with the body', () => {
    const dto = { name: 'react' };
    controller.create(dto);
    expect(mockTagsService.create).toHaveBeenCalledWith(dto);
  });

  it('delegates createMany to TagsService with the names array', () => {
    controller.createMany({ names: ['a', 'b'] });
    expect(mockTagsService.createMany).toHaveBeenCalledWith(['a', 'b']);
  });

  it('delegates remove to TagsService with a numeric id', () => {
    controller.remove('6');
    expect(mockTagsService.remove).toHaveBeenCalledWith(6);
  });
});
