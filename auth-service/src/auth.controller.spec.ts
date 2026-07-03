import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';

describe('AuthController', () => {
  const mockAuthService = {
    seed: jest.fn(),
    login: jest.fn(),
  } as unknown as AuthService;

  let controller: AuthController;

  beforeEach(() => {
    jest.clearAllMocks();
    controller = new AuthController(mockAuthService);
  });

  it('seeds the admin user on module init', async () => {
    await controller.onModuleInit();
    expect(mockAuthService.seed).toHaveBeenCalled();
  });

  it('delegates login to AuthService with the authenticated user', async () => {
    const user = { id: 1, email: 'test@example.com' };
    const loginResult = { access_token: 'token', user };
    (mockAuthService.login as jest.Mock).mockResolvedValue(loginResult);
    const result = await controller.login({ user } as any);
    expect(mockAuthService.login).toHaveBeenCalledWith(user);
    expect(result).toBe(loginResult);
  });

  it('returns the request user for verify', () => {
    const user = { id: 1, email: 'test@example.com' };
    const result = controller.verify({ user } as any);
    expect(result).toBe(user);
  });
});
