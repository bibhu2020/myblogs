import { UnauthorizedException } from '@nestjs/common';
import { LocalStrategy } from './local.strategy';
import { AuthService } from './auth.service';

describe('LocalStrategy', () => {
  const mockAuthService = { validateUser: jest.fn() } as unknown as AuthService;

  beforeEach(() => jest.clearAllMocks());

  it('returns the user when credentials are valid', async () => {
    const user = { id: 1, email: 'test@example.com' };
    (mockAuthService.validateUser as jest.Mock).mockResolvedValue(user);
    const strategy = new LocalStrategy(mockAuthService);
    const result = await strategy.validate('test@example.com', 'correct-password');
    expect(result).toBe(user);
    expect(mockAuthService.validateUser).toHaveBeenCalledWith('test@example.com', 'correct-password');
  });

  it('throws UnauthorizedException when credentials are invalid', async () => {
    (mockAuthService.validateUser as jest.Mock).mockResolvedValue(null);
    const strategy = new LocalStrategy(mockAuthService);
    await expect(strategy.validate('test@example.com', 'wrong-password')).rejects.toThrow(
      UnauthorizedException,
    );
  });
});
