import { Test, TestingModule } from '@nestjs/testing';
import { AuthService } from './auth.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { User, UserRole } from './user.entity';
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcryptjs';

const mockUserRepo = {
  findOne: jest.fn(),
  count: jest.fn(),
  save: jest.fn(),
};

const mockJwtService = {
  sign: jest.fn(() => 'mock.jwt.token'),
};

const baseUser: User = {
  id: 1,
  email: 'admin@myblogs.com',
  password: 'hashed',
  name: 'Admin',
  role: UserRole.ADMIN,
  bio: null,
  avatar: null,
  isActive: true,
  createdAt: new Date(),
  updatedAt: new Date(),
};

describe('AuthService', () => {
  let service: AuthService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        AuthService,
        { provide: getRepositoryToken(User), useValue: mockUserRepo },
        { provide: JwtService, useValue: mockJwtService },
      ],
    }).compile();
    service = module.get<AuthService>(AuthService);
    jest.clearAllMocks();
  });

  describe('validateUser', () => {
    it('returns user without password for valid credentials', async () => {
      const hash = await bcrypt.hash('admin123', 10);
      mockUserRepo.findOne.mockResolvedValue({ ...baseUser, password: hash });
      const result = await service.validateUser('admin@myblogs.com', 'admin123');
      expect(result).toBeDefined();
      expect(result.password).toBeUndefined();
      expect(result.email).toBe('admin@myblogs.com');
    });

    it('returns null for wrong password', async () => {
      const hash = await bcrypt.hash('correctpass', 10);
      mockUserRepo.findOne.mockResolvedValue({ ...baseUser, password: hash });
      const result = await service.validateUser('admin@myblogs.com', 'wrongpass');
      expect(result).toBeNull();
    });

    it('returns null when user does not exist', async () => {
      mockUserRepo.findOne.mockResolvedValue(null);
      const result = await service.validateUser('nobody@test.com', 'pass');
      expect(result).toBeNull();
    });
  });

  describe('login', () => {
    it('returns access_token and user object', async () => {
      const result = await service.login({ id: 1, email: 'admin@myblogs.com', name: 'Admin', role: UserRole.ADMIN });
      expect(result.access_token).toBe('mock.jwt.token');
      expect(result.user.email).toBe('admin@myblogs.com');
      expect(result.user.id).toBe(1);
    });

    it('signs JWT with correct payload fields', async () => {
      await service.login({ id: 2, email: 'user@test.com', name: 'User', role: UserRole.GUEST });
      expect(mockJwtService.sign).toHaveBeenCalledWith(
        expect.objectContaining({ sub: 2, email: 'user@test.com', role: UserRole.GUEST }),
      );
    });
  });

  describe('seed', () => {
    it('creates admin user when table is empty', async () => {
      mockUserRepo.count.mockResolvedValue(0);
      mockUserRepo.save.mockResolvedValue(baseUser);
      await service.seed();
      expect(mockUserRepo.save).toHaveBeenCalledTimes(1);
      const saved = mockUserRepo.save.mock.calls[0][0];
      expect(saved.email).toBe('admin@myblogs.com');
      expect(saved.role).toBe(UserRole.ADMIN);
    });

    it('skips seeding when users already exist', async () => {
      mockUserRepo.count.mockResolvedValue(3);
      await service.seed();
      expect(mockUserRepo.save).not.toHaveBeenCalled();
    });
  });
});
