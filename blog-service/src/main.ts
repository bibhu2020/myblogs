if (process.env.DATABASE_URL) {
  // Route pg.Pool through Neon's WebSocket proxy (port 443) instead of direct TCP 5432
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { neonConfig, Pool } = require('@neondatabase/serverless');
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  neonConfig.webSocketConstructor = require('ws');
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  (require('pg') as any).Pool = Pool;
}

import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { ValidationPipe } from '@nestjs/common';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableCors();
  app.useGlobalPipes(new ValidationPipe({ whitelist: true }));
  await app.listen(3002);
  console.log('Blog Service running on port 3002');
}
bootstrap();
