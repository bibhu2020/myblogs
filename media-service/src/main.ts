if (process.env.DATABASE_URL) {
  // Route pg.Pool through Neon's WebSocket proxy (port 443) instead of direct TCP 5432
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { neonConfig, Pool } = require('@neondatabase/serverless');
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  neonConfig.webSocketConstructor = require('ws');
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  (require('pg') as any).Pool = Pool;
}

import 'dotenv/config';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { NestExpressApplication } from '@nestjs/platform-express';
import { join } from 'path';

async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(AppModule);
  app.enableCors();
  app.useStaticAssets(join(process.cwd(), 'uploads'), { prefix: '/uploads' });
  await app.listen(3003);
  console.log('Media Service running on port 3003');
}
bootstrap();
