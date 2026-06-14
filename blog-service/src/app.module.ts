import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { Post } from './post.entity';
import { Category } from './category.entity';
import { Tag } from './tag.entity';
import { Comment } from './comment.entity';
import { AgentRun } from './agent-run.entity';
import { Story } from './story.entity';
import { NewsItem } from './news-item.entity';
import { PostsController } from './posts.controller';
import { PostsService } from './posts.service';
import { CategoriesController } from './categories.controller';
import { CategoriesService } from './categories.service';
import { TagsController } from './tags.controller';
import { TagsService } from './tags.service';
import { CommentsController } from './comments.controller';
import { CommentsService } from './comments.service';
import { AgentRunsController } from './agent-runs.controller';
import { AgentRunsService } from './agent-runs.service';
import { StoriesController } from './stories.controller';
import { StoriesService } from './stories.service';
import { NewsController } from './news.controller';
import { NewsService } from './news.service';
import { JwtStrategy } from './jwt.strategy';
import { SeedService } from './seed.service';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      url: process.env.DATABASE_URL || 'postgresql://neondb_owner:npg_96zZibhKwEcG@ep-delicate-fire-atgeeiwh-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require',
      ssl: { rejectUnauthorized: false },
      entities: [Post, Category, Tag, Comment, AgentRun, Story, NewsItem],
      synchronize: true,
    }),
    TypeOrmModule.forFeature([Post, Category, Tag, Comment, AgentRun, Story, NewsItem]),
    PassportModule,
    JwtModule.register({ secret: 'myblogs-secret-key-2024' }),
  ],
  controllers: [PostsController, CategoriesController, TagsController, CommentsController, AgentRunsController, StoriesController, NewsController],
  providers: [PostsService, CategoriesService, TagsService, CommentsService, AgentRunsService, StoriesService, NewsService, JwtStrategy, SeedService],
})
export class AppModule {}
