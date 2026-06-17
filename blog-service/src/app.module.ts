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
import { PushSubscription } from './push-subscription.entity';
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
import { PushController } from './push.controller';
import { PushService } from './push.service';
import { JwtStrategy } from './jwt.strategy';
import { SeedService } from './seed.service';

const DB_URL = process.env.DATABASE_URL;

const dbConfig: any = DB_URL
  ? { type: 'postgres', url: DB_URL, ssl: { rejectUnauthorized: false } }
  : { type: 'better-sqlite3', database: 'blog.db' };

@Module({
  imports: [
    // @ts-ignore — DynamicModule type mismatch: @nestjs/typeorm (root, v10 peer) vs blog-service @nestjs/common (v11)
    TypeOrmModule.forRoot({
      ...dbConfig,
      entities: [Post, Category, Tag, Comment, AgentRun, Story, NewsItem, PushSubscription],
      synchronize: true,
    }),
    // @ts-ignore
    TypeOrmModule.forFeature([Post, Category, Tag, Comment, AgentRun, Story, NewsItem, PushSubscription]),
    PassportModule,
    JwtModule.register({ secret: 'myblogs-secret-key-2024' }),
  ],
  controllers: [PostsController, CategoriesController, TagsController, CommentsController, AgentRunsController, StoriesController, NewsController, PushController],
  providers: [PostsService, CategoriesService, TagsService, CommentsService, AgentRunsService, StoriesService, NewsService, PushService, JwtStrategy, SeedService],
})
export class AppModule {}
