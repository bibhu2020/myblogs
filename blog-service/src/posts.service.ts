import { Injectable, Logger, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, Like } from 'typeorm';
import { Post, PostStatus } from './post.entity';
import { Category } from './category.entity';
import { Tag } from './tag.entity';
import slugify from 'slugify';

// Fallback repo slug — non-sensitive (repo is public), avoids silent no-op
// when GITHUB_REPO env var hasn't propagated to the container yet.
const GITHUB_REPO_FALLBACK = 'bibhu2020/myblogs';

@Injectable()
export class PostsService {
  private readonly logger = new Logger(PostsService.name);

  constructor(
    @InjectRepository(Post) private postRepo: Repository<Post>,
    @InjectRepository(Category) private catRepo: Repository<Category>,
    @InjectRepository(Tag) private tagRepo: Repository<Tag>,
  ) {}

  async findAll(query: any = {}) {
    const { category, tag, status, search, page = 1, limit = 10, featured } = query;
    const qb = this.postRepo.createQueryBuilder('post')
      .leftJoinAndSelect('post.category', 'category')
      .leftJoinAndSelect('post.tags', 'tags')
      .orderBy('post.createdAt', 'DESC');

    if (status) qb.andWhere('post.status = :status', { status });
    else qb.andWhere('post.status = :status', { status: PostStatus.PUBLISHED });

    if (category) qb.andWhere('category.slug = :category', { category });
    if (tag) qb.andWhere('tags.slug = :tag', { tag });
    if (search) qb.andWhere(
      '(post.title ILIKE :search OR post.excerpt ILIKE :search OR post.content ILIKE :search)',
      { search: `%${search}%` },
    );

    const total = await qb.getCount();
    const skip = (page - 1) * limit;
    qb.skip(skip).take(+limit);
    const posts = await qb.getMany();

    return { posts, total, page: +page, limit: +limit, pages: Math.ceil(total / limit) };
  }

  async findAllAdmin(query: any = {}) {
    const { page = 1, limit = 10, status, search } = query;
    const qb = this.postRepo.createQueryBuilder('post')
      .leftJoinAndSelect('post.category', 'category')
      .leftJoinAndSelect('post.tags', 'tags')
      .orderBy('post.createdAt', 'DESC');
    if (status) qb.andWhere('post.status = :status', { status });
    if (search) qb.andWhere('post.title LIKE :search', { search: `%${search}%` });
    const total = await qb.getCount();
    qb.skip((page - 1) * limit).take(+limit);
    const posts = await qb.getMany();
    return { posts, total, page: +page, limit: +limit, pages: Math.ceil(total / limit) };
  }

  async findBySlug(slug: string) {
    const post = await this.postRepo.createQueryBuilder('post')
      .leftJoinAndSelect('post.category', 'category')
      .leftJoinAndSelect('post.tags', 'tags')
      .leftJoinAndSelect('post.comments', 'comments')
      .where('post.slug = :slug', { slug })
      .andWhere('post.status = :status', { status: PostStatus.PUBLISHED })
      .getOne();
    if (!post) throw new NotFoundException('Post not found');
    await this.postRepo.increment({ id: post.id }, 'views', 1);
    return post;
  }

  async findOne(id: number) {
    const post = await this.postRepo.findOne({ where: { id }, relations: ['category', 'tags', 'comments'] });
    if (!post) throw new NotFoundException('Post not found');
    return post;
  }

  async create(dto: any, user: any) {
    let slug = slugify(dto.title, { lower: true, strict: true });
    const existing = await this.postRepo.findOne({ where: { slug } });
    if (existing) slug = `${slug}-${Date.now()}`;

    const postData: any = {
      ...dto,
      slug,
      authorId: user?.id ?? 0,
      authorName: dto.authorName || user?.name || 'Anonymous',
      readTime: Math.ceil((dto.content || '').split(' ').length / 200),
      gallery: dto.gallery ? JSON.stringify(dto.gallery) : null,
    };
    const post = this.postRepo.create(postData as Post);

    if (dto.categoryId) {
      post.category = await this.catRepo.findOne({ where: { id: dto.categoryId } });
    }

    if (dto.tagIds?.length) {
      post.tags = await this.tagRepo.findByIds(dto.tagIds);
    }

    return this.postRepo.save(post);
  }

  async update(id: number, dto: any) {
    const post = await this.findOne(id);
    if (dto.title && dto.title !== post.title) {
      let slug = slugify(dto.title, { lower: true, strict: true });
      const existing = await this.postRepo.findOne({ where: { slug } });
      if (existing && existing.id !== id) slug = `${slug}-${Date.now()}`;
      post.slug = slug;
    }
    if (dto.categoryId !== undefined) {
      post.category = dto.categoryId ? await this.catRepo.findOne({ where: { id: dto.categoryId } }) : null;
    }
    if (dto.tagIds) {
      post.tags = dto.tagIds.length ? await this.tagRepo.findByIds(dto.tagIds) : [];
    }
    if (dto.gallery) dto.gallery = JSON.stringify(dto.gallery);
    if (dto.content) post.readTime = Math.ceil(dto.content.split(' ').length / 200);
    Object.assign(post, dto);
    return this.postRepo.save(post);
  }

  async remove(id: number) {
    const post = await this.findOne(id);
    await this.postRepo.remove(post);
    return { message: 'Post deleted' };
  }

  async approve(id: number) {
    const post = await this.findOne(id);
    if (post.status !== PostStatus.PENDING) {
      throw new Error(`Post ${id} is not pending approval (status: ${post.status})`);
    }
    post.status = PostStatus.PUBLISHED;
    const saved = await this.postRepo.save(post);
    void this.dispatchPostDecision('approve', id);
    return saved;
  }

  async reject(id: number) {
    const post = await this.findOne(id);
    if (post.status !== PostStatus.PENDING) {
      throw new Error(`Post ${id} is not pending approval (status: ${post.status})`);
    }
    const title = post.title;
    await this.postRepo.remove(post);
    // Fire-and-forget: triggers the resume workflow which runs media cleanup
    void this.dispatchPostDecision('reject', id);
    return { message: `Post "${title}" rejected and removed.` };
  }

  // Fires a repository_dispatch event to GitHub so the post-agent resume
  // workflow can clean up media (on reject) and update the pending registry.
  // Requires SECRET_TOKEN_GITHUB to have repo scope (classic PAT) or
  // Actions:write + Contents:write (fine-grained PAT).
  private async dispatchPostDecision(action: 'approve' | 'reject', postId: number): Promise<void> {
    const token = process.env.SECRET_TOKEN_GITHUB;
    const repo  = process.env.GITHUB_REPO || GITHUB_REPO_FALLBACK;

    if (!token) {
      this.logger.error('[post-agent] SECRET_TOKEN_GITHUB is not set — cannot trigger resume workflow');
      return;
    }

    this.logger.log(`[post-agent] Dispatching post-decision (${action}) for post #${postId} → ${repo}`);

    try {
      const resp = await fetch(`https://api.github.com/repos/${repo}/dispatches`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/vnd.github.v3+json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          event_type: 'post-decision',
          client_payload: { action, post_id: postId },
        }),
      });

      if (resp.ok) {
        this.logger.log(`[post-agent] GitHub dispatch accepted (${resp.status}) — resume workflow triggered`);
      } else {
        const body = await resp.text();
        this.logger.error(
          `[post-agent] GitHub dispatch failed (${resp.status}) — check PAT has repo/Actions:write scope. Response: ${body.slice(0, 300)}`,
        );
      }
    } catch (err: any) {
      this.logger.error(`[post-agent] GitHub dispatch threw: ${err.message}`);
    }
  }

  async getStats() {
    const total = await this.postRepo.count();
    const published = await this.postRepo.count({ where: { status: PostStatus.PUBLISHED } });
    const drafts = await this.postRepo.count({ where: { status: PostStatus.DRAFT } });
    const pending = await this.postRepo.count({ where: { status: PostStatus.PENDING } });
    const views = await this.postRepo.createQueryBuilder('post').select('SUM(post.views)', 'total').getRawOne();
    return { total, published, drafts, pending, totalViews: views?.total || 0 };
  }

  async getFeatured() {
    return this.postRepo.find({
      where: { status: PostStatus.PUBLISHED },
      relations: ['category', 'tags'],
      order: { views: 'DESC' },
      take: 5,
    });
  }

  async getRecent() {
    return this.postRepo.find({
      where: { status: PostStatus.PUBLISHED },
      relations: ['category', 'tags'],
      order: { createdAt: 'DESC' },
      take: 6,
    });
  }
}
