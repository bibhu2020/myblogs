import { PushController } from './push.controller';
import { PushService } from './push.service';

describe('PushController', () => {
  const mockPushService = {
    getVapidPublicKey: jest.fn(),
    subscribe: jest.fn(),
    unsubscribe: jest.fn(),
  } as unknown as PushService;

  let controller: PushController;

  beforeEach(() => {
    jest.clearAllMocks();
    controller = new PushController(mockPushService);
  });

  it('returns the VAPID public key', () => {
    (mockPushService.getVapidPublicKey as jest.Mock).mockReturnValue('public-key');
    expect(controller.getVapidKey()).toEqual({ publicKey: 'public-key' });
  });

  it('delegates subscribe to PushService with the body', () => {
    const body = { endpoint: 'https://push.example/1', keys: { p256dh: 'a', auth: 'b' } };
    controller.subscribe(body);
    expect(mockPushService.subscribe).toHaveBeenCalledWith(body);
  });

  it('delegates unsubscribe to PushService with the endpoint', () => {
    controller.unsubscribe({ endpoint: 'https://push.example/1' });
    expect(mockPushService.unsubscribe).toHaveBeenCalledWith('https://push.example/1');
  });
});
