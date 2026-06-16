import { Test, TestingModule } from '@nestjs/testing';
import { UsersService } from './users.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { User, UserRole } from './user.entity';
import { ConflictException, NotFoundException } from '@nestjs/common';

const mockUserRepo = {
  find: jest.fn(),
  findOne: jest.fn(),
  create: jest.fn(),
  save: jest.fn(),
  remove: jest.fn(),
};

const mockUser: Partial<User> = {
  id: 1,
  email: 'test@example.com',
  password: 'hashed',
  name: 'Test User',
  role: UserRole.GUEST,
  isActive: true,
};

describe('UsersService', () => {
  let service: UsersService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        UsersService,
        { provide: getRepositoryToken(User), useValue: mockUserRepo },
      ],
    }).compile();
    service = module.get<UsersService>(UsersService);
    jest.clearAllMocks();
  });

  describe('findAll', () => {
    it('returns array of users', async () => {
      mockUserRepo.find.mockResolvedValue([mockUser]);
      const result = await service.findAll();
      expect(result).toHaveLength(1);
      expect(result[0].email).toBe('test@example.com');
    });

    it('returns empty array when no users', async () => {
      mockUserRepo.find.mockResolvedValue([]);
      const result = await service.findAll();
      expect(result).toHaveLength(0);
    });
  });

  describe('findOne', () => {
    it('returns user when found', async () => {
      mockUserRepo.findOne.mockResolvedValue(mockUser);
      const result = await service.findOne(1);
      expect(result.id).toBe(1);
    });

    it('throws NotFoundException when user missing', async () => {
      mockUserRepo.findOne.mockResolvedValue(null);
      await expect(service.findOne(999)).rejects.toThrow(NotFoundException);
    });
  });

  describe('create', () => {
    it('creates user and strips password from response', async () => {
      mockUserRepo.findOne.mockResolvedValue(null);
      const saved = { ...mockUser, id: 2, email: 'new@test.com', password: 'hashed' };
      mockUserRepo.create.mockReturnValue(saved);
      mockUserRepo.save.mockResolvedValue(saved);
      const result = await service.create({ email: 'new@test.com', password: 'pass', name: 'New' });
      expect(result.email).toBe('new@test.com');
      expect((result as any).password).toBeUndefined();
    });

    it('throws ConflictException when email already exists', async () => {
      mockUserRepo.findOne.mockResolvedValue(mockUser);
      await expect(service.create({ email: 'test@example.com', password: 'pass', name: 'Dupe' }))
        .rejects.toThrow(ConflictException);
    });

    it('defaults role to GUEST when not provided', async () => {
      mockUserRepo.findOne.mockResolvedValue(null);
      const saved = { ...mockUser, id: 3, password: 'hashed' };
      mockUserRepo.create.mockReturnValue(saved);
      mockUserRepo.save.mockResolvedValue(saved);
      await service.create({ email: 'guest@test.com', password: 'pass', name: 'Guest' });
      const createArg = mockUserRepo.create.mock.calls[0][0];
      expect(createArg.role).toBe(UserRole.GUEST);
    });
  });

  describe('update', () => {
    it('updates user fields and strips password', async () => {
      mockUserRepo.findOne.mockResolvedValue({ ...mockUser });
      const updated = { ...mockUser, name: 'Updated Name', password: 'hashed' };
      mockUserRepo.save.mockResolvedValue(updated);
      const result = await service.update(1, { name: 'Updated Name' });
      expect((result as any).password).toBeUndefined();
    });

    it('throws NotFoundException for missing user', async () => {
      mockUserRepo.findOne.mockResolvedValue(null);
      await expect(service.update(99, { name: 'X' })).rejects.toThrow(NotFoundException);
    });
  });

  describe('remove', () => {
    it('removes user and returns confirmation', async () => {
      mockUserRepo.findOne.mockResolvedValue(mockUser);
      mockUserRepo.remove.mockResolvedValue(undefined);
      const result = await service.remove(1);
      expect(result).toEqual({ message: 'User deleted' });
    });

    it('throws NotFoundException for missing user', async () => {
      mockUserRepo.findOne.mockResolvedValue(null);
      await expect(service.remove(999)).rejects.toThrow(NotFoundException);
    });
  });
});
