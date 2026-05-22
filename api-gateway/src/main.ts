import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableCors({ origin: '*', methods: 'GET,HEAD,PUT,PATCH,POST,DELETE,OPTIONS', allowedHeaders: '*' });
  await app.listen(3000);
  console.log('API Gateway running on port 3000');
}
bootstrap();
