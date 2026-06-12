import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { User } from './user.entity';
import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';
import { UsersController } from './users.controller';
import { UsersService } from './users.service';
import { JwtStrategy } from './jwt.strategy';
import { LocalStrategy } from './local.strategy';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      url: process.env.DATABASE_URL || 'postgresql://neondb_owner:npg_96zZibhKwEcG@ep-delicate-fire-atgeeiwh-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require',
      ssl: { rejectUnauthorized: false },
      entities: [User],
      synchronize: true,
    }),
    TypeOrmModule.forFeature([User]),
    PassportModule,
    JwtModule.register({
      secret: 'myblogs-secret-key-2024',
      signOptions: { expiresIn: '7d' },
    }),
  ],
  controllers: [AuthController, UsersController],
  providers: [AuthService, UsersService, JwtStrategy, LocalStrategy],
})
export class AppModule {}
