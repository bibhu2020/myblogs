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
      type: 'better-sqlite3',
      database: 'blog.db',
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
