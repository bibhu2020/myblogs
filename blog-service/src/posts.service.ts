import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, Like } from 'typeorm';
import { Post, PostStatus } from './post.entity';
import { Category } from './category.entity';
import { Tag } from './tag.entity';
import slugify from 'slugify';

@Injectable()
export class PostsService {
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
      authorId: user.id,
      authorName: user.name,
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

  async getStats() {
    const total = await this.postRepo.count();
    const published = await this.postRepo.count({ where: { status: PostStatus.PUBLISHED } });
    const drafts = await this.postRepo.count({ where: { status: PostStatus.DRAFT } });
    const views = await this.postRepo.createQueryBuilder('post').select('SUM(post.views)', 'total').getRawOne();
    return { total, published, drafts, totalViews: views?.total || 0 };
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
