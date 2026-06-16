import { Test, TestingModule } from '@nestjs/testing';
import { ProxyService } from './proxy.service';
import { HttpException } from '@nestjs/common';
import axios from 'axios';

jest.mock('axios');
const mockedAxios = axios as unknown as jest.Mock;

describe('ProxyService', () => {
  let service: ProxyService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [ProxyService],
    }).compile();
    service = module.get<ProxyService>(ProxyService);
    jest.clearAllMocks();
  });

  describe('forward', () => {
    it('calls internal service URL and returns response data', async () => {
      mockedAxios.mockResolvedValue({ data: { id: 1, email: 'admin@test.com' } });
      const result = await service.forward('auth', '/api/auth/me', 'GET');
      expect(result).toEqual({ id: 1, email: 'admin@test.com' });
      expect(mockedAxios).toHaveBeenCalledWith(
        expect.objectContaining({ url: 'http://localhost:3001/api/auth/me', method: 'GET' }),
      );
    });

    it('routes blog service to port 3002', async () => {
      mockedAxios.mockResolvedValue({ data: { posts: [] } });
      await service.forward('blog', '/api/posts', 'GET');
      expect(mockedAxios).toHaveBeenCalledWith(
        expect.objectContaining({ url: 'http://localhost:3002/api/posts' }),
      );
    });

    it('routes media service to port 3003', async () => {
      mockedAxios.mockResolvedValue({ data: [] });
      await service.forward('media', '/api/media', 'GET');
      expect(mockedAxios).toHaveBeenCalledWith(
        expect.objectContaining({ url: 'http://localhost:3003/api/media' }),
      );
    });

    it('forwards data payload on POST requests', async () => {
      mockedAxios.mockResolvedValue({ data: { access_token: 'jwt' } });
      const body = { email: 'test@test.com', password: 'pass' };
      await service.forward('auth', '/api/auth/login', 'POST', body);
      expect(mockedAxios).toHaveBeenCalledWith(
        expect.objectContaining({ method: 'POST', data: body }),
      );
    });

    it('throws HttpException with upstream status on error', async () => {
      mockedAxios.mockRejectedValue({ response: { status: 401, data: { message: 'Unauthorized' } } });
      await expect(service.forward('auth', '/api/auth/me', 'GET'))
        .rejects.toThrow(HttpException);
    });

    it('throws 500 HttpException when upstream has no response', async () => {
      mockedAxios.mockRejectedValue(new Error('Network Error'));
      try {
        await service.forward('blog', '/api/posts', 'GET');
        fail('should have thrown');
      } catch (e) {
        expect(e).toBeInstanceOf(HttpException);
        expect((e as HttpException).getStatus()).toBe(500);
      }
    });
  });
});
