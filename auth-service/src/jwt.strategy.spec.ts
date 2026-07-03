import { JwtStrategy } from './jwt.strategy';

describe('JwtStrategy', () => {
  it('maps the JWT payload to a user object', async () => {
    const strategy = new JwtStrategy();
    const result = await strategy.validate({
      sub: 1,
      email: 'test@example.com',
      role: 'admin',
      name: 'Test User',
    });
    expect(result).toEqual({
      id: 1,
      email: 'test@example.com',
      role: 'admin',
      name: 'Test User',
    });
  });
});
