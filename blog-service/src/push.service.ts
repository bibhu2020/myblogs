import { Injectable, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import * as webpush from 'web-push';
import { PushSubscription } from './push-subscription.entity';

@Injectable()
export class PushService {
  private readonly logger = new Logger(PushService.name);
  private readonly enabled: boolean;

  constructor(
    @InjectRepository(PushSubscription)
    private readonly subRepo: Repository<PushSubscription>,
  ) {
    const publicKey = process.env.VAPID_PUBLIC_KEY;
    const privateKey = process.env.VAPID_PRIVATE_KEY;
    const email = process.env.VAPID_EMAIL || 'mailto:admin@meridian.blog';

    if (publicKey && privateKey) {
      webpush.setVapidDetails(email, publicKey, privateKey);
      this.enabled = true;
      this.logger.log('Push notifications enabled (VAPID configured)');
    } else {
      this.logger.warn('VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY not set — push notifications disabled');
      this.enabled = false;
    }
  }

  getVapidPublicKey(): string {
    return process.env.VAPID_PUBLIC_KEY || '';
  }

  async subscribe(data: { endpoint: string; keys: { p256dh: string; auth: string } }): Promise<void> {
    const existing = await this.subRepo.findOne({ where: { endpoint: data.endpoint } });
    if (existing) return;
    await this.subRepo.save(
      this.subRepo.create({ endpoint: data.endpoint, p256dh: data.keys.p256dh, auth: data.keys.auth }),
    );
  }

  async unsubscribe(endpoint: string): Promise<void> {
    await this.subRepo.delete({ endpoint });
  }

  async send(payload: { title: string; body: string; url: string }): Promise<void> {
    if (!this.enabled) return;
    const subs = await this.subRepo.find();
    if (!subs.length) return;

    const message = JSON.stringify(payload);
    await Promise.allSettled(
      subs.map(async (sub) => {
        try {
          await webpush.sendNotification(
            { endpoint: sub.endpoint, keys: { p256dh: sub.p256dh, auth: sub.auth } },
            message,
          );
        } catch (err: any) {
          if (err.statusCode === 410 || err.statusCode === 404) {
            await this.subRepo.delete(sub.id);
          } else {
            this.logger.error(`Push failed for ${sub.endpoint.slice(0, 60)}…: ${err.message}`);
          }
        }
      }),
    );
  }
}
