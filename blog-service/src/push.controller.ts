import { Controller, Get, Post, Delete, Body, HttpCode } from '@nestjs/common';
import { PushService } from './push.service';

@Controller('push')
export class PushController {
  constructor(private readonly pushService: PushService) {}

  @Get('vapid-key')
  getVapidKey() {
    return { publicKey: this.pushService.getVapidPublicKey() };
  }

  @Post('subscribe')
  @HttpCode(204)
  subscribe(@Body() body: { endpoint: string; keys: { p256dh: string; auth: string } }) {
    return this.pushService.subscribe(body);
  }

  @Delete('unsubscribe')
  @HttpCode(204)
  unsubscribe(@Body() body: { endpoint: string }) {
    return this.pushService.unsubscribe(body.endpoint);
  }
}
