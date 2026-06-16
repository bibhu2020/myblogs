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

const DB_URL = process.env.DATABASE_URL;

const dbConfig: any = DB_URL
  ? {
      type: 'postgres',
      url: DB_URL,
      ssl: { rejectUnauthorized: false },
    }
  : {
      type: 'better-sqlite3',
      database: 'auth.db',
    };

@Module({
  imports: [
    TypeOrmModule.forRoot({
      ...dbConfig,
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
