import { CategoriesController } from './categories.controller';
import { CategoriesService } from './categories.service';

describe('CategoriesController', () => {
  const mockCategoriesService = {
    findAll: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    remove: jest.fn(),
  } as unknown as CategoriesService;

  let controller: CategoriesController;

  beforeEach(() => {
    jest.clearAllMocks();
    controller = new CategoriesController(mockCategoriesService);
  });

  it('delegates findAll to CategoriesService', () => {
    controller.findAll();
    expect(mockCategoriesService.findAll).toHaveBeenCalled();
  });

  it('delegates create to CategoriesService with the body', () => {
    const dto = { name: 'Tech' };
    controller.create(dto);
    expect(mockCategoriesService.create).toHaveBeenCalledWith(dto);
  });

  it('delegates update to CategoriesService with a numeric id and body', () => {
    const dto = { name: 'Updated' };
    controller.update('3', dto);
    expect(mockCategoriesService.update).toHaveBeenCalledWith(3, dto);
  });

  it('delegates remove to CategoriesService with a numeric id', () => {
    controller.remove('4');
    expect(mockCategoriesService.remove).toHaveBeenCalledWith(4);
  });
});
