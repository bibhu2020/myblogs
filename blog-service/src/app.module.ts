import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { Post } from './post.entity';
import { Category } from './category.entity';
import { Tag } from './tag.entity';
import { Comment } from './comment.entity';
import { PostsController } from './posts.controller';
import { PostsService } from './posts.service';
import { CategoriesController } from './categories.controller';
import { CategoriesService } from './categories.service';
import { TagsController } from './tags.controller';
import { TagsService } from './tags.service';
import { CommentsController } from './comments.controller';
import { CommentsService } from './comments.service';
import { JwtStrategy } from './jwt.strategy';
import { SeedService } from './seed.service';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      url: process.env.DATABASE_URL || 'postgresql://neondb_owner:npg_96zZibhKwEcG@ep-delicate-fire-atgeeiwh-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require',
      ssl: { rejectUnauthorized: false },
      entities: [Post, Category, Tag, Comment],
      synchronize: true,
    }),
    TypeOrmModule.forFeature([Post, Category, Tag, Comment]),
    PassportModule,
    JwtModule.register({ secret: 'myblogs-secret-key-2024' }),
  ],
  controllers: [PostsController, CategoriesController, TagsController, CommentsController],
  providers: [PostsService, CategoriesService, TagsService, CommentsService, JwtStrategy, SeedService],
})
export class AppModule {}
