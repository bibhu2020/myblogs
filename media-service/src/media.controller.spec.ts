import { MediaController } from './media.controller';
import { MediaService } from './media.service';

describe('MediaController', () => {
  const mockMediaService = {
    findAll: jest.fn(),
    save: jest.fn(),
    remove: jest.fn(),
  } as unknown as MediaService;

  let controller: MediaController;

  beforeEach(() => {
    jest.clearAllMocks();
    controller = new MediaController(mockMediaService);
  });

  it('delegates findAll to MediaService', () => {
    controller.findAll();
    expect(mockMediaService.findAll).toHaveBeenCalled();
  });

  it('delegates upload to MediaService with the file, user id, and alt text', () => {
    const file = { filename: 'a.jpg' } as Express.Multer.File;
    const req = { user: { id: 7 } };
    controller.upload(file, req, 'my alt');
    expect(mockMediaService.save).toHaveBeenCalledWith(file, 7, 'my alt');
  });

  it('delegates remove to MediaService with a numeric id', () => {
    controller.remove('12');
    expect(mockMediaService.remove).toHaveBeenCalledWith(12);
  });
});
