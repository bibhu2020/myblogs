import { NewsController } from './news.controller';
import { NewsService } from './news.service';

describe('NewsController', () => {
  const mockNewsService = {
    findAll: jest.fn(),
    refresh: jest.fn(),
  } as unknown as NewsService;

  let controller: NewsController;

  beforeEach(() => {
    jest.clearAllMocks();
    controller = new NewsController(mockNewsService);
  });

  it('delegates getAll to NewsService with the region filter', () => {
    controller.getAll('usa');
    expect(mockNewsService.findAll).toHaveBeenCalledWith('usa');
  });

  it('delegates refresh to NewsService with the items array', () => {
    const items = [{ title: 'Breaking' }];
    controller.refresh({ items });
    expect(mockNewsService.refresh).toHaveBeenCalledWith(items);
  });

  it('defaults refresh items to an empty array when omitted', () => {
    controller.refresh({} as any);
    expect(mockNewsService.refresh).toHaveBeenCalledWith([]);
  });
});
