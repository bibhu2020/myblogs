import { UsersController } from './users.controller';
import { UsersService } from './users.service';

describe('UsersController', () => {
  const mockUsersService = {
    findAll: jest.fn(),
    findOne: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    remove: jest.fn(),
  } as unknown as UsersService;

  let controller: UsersController;

  beforeEach(() => {
    jest.clearAllMocks();
    controller = new UsersController(mockUsersService);
  });

  it('delegates findAll to UsersService', () => {
    controller.findAll();
    expect(mockUsersService.findAll).toHaveBeenCalled();
  });

  it('delegates findOne to UsersService with a numeric id', () => {
    controller.findOne('42');
    expect(mockUsersService.findOne).toHaveBeenCalledWith(42);
  });

  it('delegates create to UsersService with the body', () => {
    const dto = { email: 'new@test.com' };
    controller.create(dto);
    expect(mockUsersService.create).toHaveBeenCalledWith(dto);
  });

  it('delegates update to UsersService with a numeric id and body', () => {
    const dto = { name: 'Updated' };
    controller.update('7', dto);
    expect(mockUsersService.update).toHaveBeenCalledWith(7, dto);
  });

  it('delegates remove to UsersService with a numeric id', () => {
    controller.remove('9');
    expect(mockUsersService.remove).toHaveBeenCalledWith(9);
  });
});
