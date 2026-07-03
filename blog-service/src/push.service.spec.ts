import { Test, TestingModule } from '@nestjs/testing';
import { getRepositoryToken } from '@nestjs/typeorm';
import { PushSubscription } from './push-subscription.entity';
import { PushService } from './push.service';
import * as webpush from 'web-push';

jest.mock('web-push', () => ({
  setVapidDetails: jest.fn(),
  sendNotification: jest.fn(),
}));

const mockSubRepo = {
  findOne: jest.fn(),
  create: jest.fn(),
  save: jest.fn(),
  delete: jest.fn(),
  find: jest.fn(),
};

const ORIGINAL_ENV = process.env;

async function createService() {
  // The constructor reads process.env fresh on every instantiation, so
  // compiling a new TestingModule per test picks up whatever this test set.
  const module: TestingModule = await Test.createTestingModule({
    providers: [
      PushService,
      { provide: getRepositoryToken(PushSubscription), useValue: mockSubRepo },
    ],
  }).compile();
  return module.get(PushService);
}

describe('PushService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env = { ...ORIGINAL_ENV };
  });

  afterAll(() => {
    process.env = ORIGINAL_ENV;
  });

  describe('with VAPID keys configured', () => {
    beforeEach(() => {
      process.env.VAPID_PUBLIC_KEY = 'pub-key';
      process.env.VAPID_PRIVATE_KEY = 'priv-key';
    });

    it('configures web-push with the VAPID details', async () => {
      await createService();
      expect(webpush.setVapidDetails).toHaveBeenCalledWith(
        'mailto:admin@meridian.blog',
        'pub-key',
        'priv-key',
      );
    });

    it('returns the public key', async () => {
      const service = await createService();
      expect(service.getVapidPublicKey()).toBe('pub-key');
    });

    it('sends a notification to every subscription', async () => {
      const service = await createService();
      const subs = [
        { id: 1, endpoint: 'https://push.example/1', p256dh: 'a', auth: 'b' },
        { id: 2, endpoint: 'https://push.example/2', p256dh: 'c', auth: 'd' },
      ];
      mockSubRepo.find.mockResolvedValue(subs);
      (webpush.sendNotification as jest.Mock).mockResolvedValue(undefined);
      await service.send({ title: 'Hi', body: 'There', url: '/x' });
      expect(webpush.sendNotification).toHaveBeenCalledTimes(2);
    });

    it('does nothing when there are no subscriptions', async () => {
      const service = await createService();
      mockSubRepo.find.mockResolvedValue([]);
      await service.send({ title: 'Hi', body: 'There', url: '/x' });
      expect(webpush.sendNotification).not.toHaveBeenCalled();
    });

    it('deletes the subscription when the push endpoint is gone (410/404)', async () => {
      const service = await createService();
      const subs = [{ id: 1, endpoint: 'https://push.example/1', p256dh: 'a', auth: 'b' }];
      mockSubRepo.find.mockResolvedValue(subs);
      (webpush.sendNotification as jest.Mock).mockRejectedValue({ statusCode: 410, message: 'gone' });
      await service.send({ title: 'Hi', body: 'There', url: '/x' });
      expect(mockSubRepo.delete).toHaveBeenCalledWith(1);
    });

    it('logs and keeps the subscription on other push errors', async () => {
      const service = await createService();
      const subs = [{ id: 1, endpoint: 'https://push.example/1', p256dh: 'a', auth: 'b' }];
      mockSubRepo.find.mockResolvedValue(subs);
      (webpush.sendNotification as jest.Mock).mockRejectedValue({ statusCode: 500, message: 'boom' });
      await service.send({ title: 'Hi', body: 'There', url: '/x' });
      expect(mockSubRepo.delete).not.toHaveBeenCalled();
    });

    describe('subscribe / unsubscribe', () => {
      it('saves a new subscription when none exists yet', async () => {
        const service = await createService();
        mockSubRepo.findOne.mockResolvedValue(null);
        const created = { endpoint: 'e', p256dh: 'a', auth: 'b' };
        mockSubRepo.create.mockReturnValue(created);
        await service.subscribe({ endpoint: 'e', keys: { p256dh: 'a', auth: 'b' } });
        expect(mockSubRepo.save).toHaveBeenCalledWith(created);
      });

      it('does not duplicate an existing subscription', async () => {
        const service = await createService();
        mockSubRepo.findOne.mockResolvedValue({ id: 1, endpoint: 'e' });
        await service.subscribe({ endpoint: 'e', keys: { p256dh: 'a', auth: 'b' } });
        expect(mockSubRepo.save).not.toHaveBeenCalled();
      });

      it('deletes the subscription by endpoint', async () => {
        const service = await createService();
        await service.unsubscribe('e');
        expect(mockSubRepo.delete).toHaveBeenCalledWith({ endpoint: 'e' });
      });
    });
  });

  describe('without VAPID keys configured', () => {
    beforeEach(() => {
      delete process.env.VAPID_PUBLIC_KEY;
      delete process.env.VAPID_PRIVATE_KEY;
    });

    it('does not configure web-push', async () => {
      await createService();
      expect(webpush.setVapidDetails).not.toHaveBeenCalled();
    });

    it('send() is a no-op when push is disabled', async () => {
      const service = await createService();
      await service.send({ title: 'Hi', body: 'There', url: '/x' });
      expect(mockSubRepo.find).not.toHaveBeenCalled();
    });

    it('getVapidPublicKey returns an empty string', async () => {
      const service = await createService();
      expect(service.getVapidPublicKey()).toBe('');
    });
  });
});
