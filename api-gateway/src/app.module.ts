import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { AppController } from './app.controller';
import { McpController } from './mcp.controller';
import { ProxyService } from './proxy.service';
import { JwtStrategy } from './jwt.strategy';

@Module({
  imports: [
    PassportModule,
    JwtModule.register({ secret: 'myblogs-secret-key-2024' }),
  ],
  controllers: [AppController, McpController],
  providers: [ProxyService, JwtStrategy],
})
export class AppModule {}
