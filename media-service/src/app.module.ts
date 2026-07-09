import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { MulterModule } from '@nestjs/platform-express';
import { diskStorage } from 'multer';
import { extname, join } from 'path';
import { v4 as uuidv4 } from 'uuid';
import { Media } from './media.entity';
import { MediaController } from './media.controller';
import { MediaService } from './media.service';
import { JwtStrategy } from './jwt.strategy';
import * as fs from 'fs';

// __dirname-relative so these always resolve under media-service/ regardless of
// process.cwd() — see auth-service/src/app.module.ts for why.
const uploadDir = join(__dirname, '..', 'uploads');
if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true });

// Callers (e.g. the content agents naming a narration mp3 "post_123") can request a
// deterministic filename via ?filename=<name> on the upload URL — read from the query
// string rather than a body field, since query params are available synchronously
// before Multer starts streaming the multipart body (unlike form fields, which would
// require the caller to guarantee field ordering). Only a bare alphanumeric/-/_ name is
// accepted; the real file extension is always re-appended, never trusted from the query
// param, so a caller can't smuggle in an unexpected extension. Falls back to the
// existing random UUID scheme when absent or invalid — every other upload caller
// (admin manual uploads, inline post/story images) is unaffected.
const SAFE_FILENAME = /^[a-zA-Z0-9_-]+$/;

export function buildFilename(req: any, file: Express.Multer.File): string {
  const ext = extname(file.originalname);
  const requested = (req.query?.filename as string | undefined)?.trim();
  if (requested) {
    const base = requested.replace(/\.[a-zA-Z0-9]+$/, '');
    if (SAFE_FILENAME.test(base)) {
      return `${base}${ext}`;
    }
  }
  return `${uuidv4()}${ext}`;
}

const DB_URL = process.env.DATABASE_URL;

const dbConfig: any = DB_URL
  ? { type: 'postgres', url: DB_URL, ssl: { rejectUnauthorized: false } }
  : { type: 'better-sqlite3', database: join(__dirname, '..', 'media.db') };

@Module({
  imports: [
    TypeOrmModule.forRoot({
      ...dbConfig,
      entities: [Media],
      synchronize: true,
    }),
    TypeOrmModule.forFeature([Media]),
    PassportModule,
    JwtModule.register({ secret: 'myblogs-secret-key-2024' }),
    MulterModule.register({
      storage: diskStorage({
        destination: uploadDir,
        filename: (req, file, cb) => {
          cb(null, buildFilename(req, file));
        },
      }),
      fileFilter: (req, file, cb) => {
        const allowed = /jpeg|jpg|png|gif|webp|svg|mp3/;
        cb(null, allowed.test(extname(file.originalname).toLowerCase()));
      },
      // 25MB — comfortably covers a several-minute spoken-word mp3 (~96kbps ≈ 1MB/min)
      // on top of the original image use case.
      limits: { fileSize: 25 * 1024 * 1024 },
    }),
  ],
  controllers: [MediaController],
  providers: [MediaService, JwtStrategy],
})
export class AppModule {}
