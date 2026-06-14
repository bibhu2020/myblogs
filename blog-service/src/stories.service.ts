import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Story, StoryStatus } from './story.entity';
import slugify from 'slugify';

@Injectable()
export class StoriesService {
  constructor(
    @InjectRepository(Story) private storyRepo: Repository<Story>,
  ) {}

  async findAll(query: any = {}) {
    const { genre, search, page = 1, limit = 12 } = query;
    const qb = this.storyRepo.createQueryBuilder('story')
      .where('story.status = :status', { status: StoryStatus.PUBLISHED })
      .orderBy('story.createdAt', 'DESC');

    if (genre) qb.andWhere('story.genre = :genre', { genre });
    if (search) qb.andWhere(
      '(story.title ILIKE :search OR story.excerpt ILIKE :search OR story.content ILIKE :search)',
      { search: `%${search}%` },
    );

    const total = await qb.getCount();
    qb.skip((+page - 1) * +limit).take(+limit);
    const stories = await qb.getMany();
    return { stories, total, page: +page, limit: +limit, pages: Math.ceil(total / +limit) };
  }

  async findAllAdmin(query: any = {}) {
    const { page = 1, limit = 15, status, search } = query;
    const qb = this.storyRepo.createQueryBuilder('story')
      .orderBy('story.createdAt', 'DESC');
    if (status) qb.andWhere('story.status = :status', { status });
    if (search) qb.andWhere('story.title ILIKE :search', { search: `%${search}%` });
    const total = await qb.getCount();
    qb.skip((+page - 1) * +limit).take(+limit);
    const stories = await qb.getMany();
    return { stories, total, page: +page, limit: +limit, pages: Math.ceil(total / +limit) };
  }

  async findBySlug(slug: string) {
    const story = await this.storyRepo.findOne({
      where: { slug, status: StoryStatus.PUBLISHED },
    });
    if (!story) throw new NotFoundException('Story not found');
    await this.storyRepo.increment({ id: story.id }, 'views', 1);
    return story;
  }

  async findOne(id: number) {
    const story = await this.storyRepo.findOne({ where: { id } });
    if (!story) throw new NotFoundException('Story not found');
    return story;
  }

  async create(dto: any, user: any) {
    let slug = slugify(dto.title, { lower: true, strict: true });
    const existing = await this.storyRepo.findOne({ where: { slug } });
    if (existing) slug = `${slug}-${Date.now()}`;

    const story = this.storyRepo.create({
      ...dto,
      slug,
      authorId: user?.id ?? 0,
      authorName: dto.authorName || user?.name || 'Anonymous',
      readTime: Math.ceil((dto.content || '').split(' ').length / 200),
    } as Story);

    return this.storyRepo.save(story);
  }

  async update(id: number, dto: any) {
    const story = await this.findOne(id);
    if (dto.title && dto.title !== story.title) {
      let slug = slugify(dto.title, { lower: true, strict: true });
      const existing = await this.storyRepo.findOne({ where: { slug } });
      if (existing && existing.id !== id) slug = `${slug}-${Date.now()}`;
      story.slug = slug;
    }
    if (dto.content) story.readTime = Math.ceil(dto.content.split(' ').length / 200);
    Object.assign(story, dto);
    return this.storyRepo.save(story);
  }

  async remove(id: number) {
    const story = await this.findOne(id);
    await this.storyRepo.remove(story);
    return { message: 'Story deleted' };
  }

  async approve(id: number) {
    const story = await this.findOne(id);
    if (story.status !== StoryStatus.PENDING) {
      throw new Error(`Story ${id} is not pending approval (status: ${story.status})`);
    }
    story.status = StoryStatus.PUBLISHED;
    return this.storyRepo.save(story);
  }

  async reject(id: number) {
    const story = await this.findOne(id);
    if (story.status !== StoryStatus.PENDING) {
      throw new Error(`Story ${id} is not pending approval (status: ${story.status})`);
    }
    const title = story.title;
    await this.storyRepo.remove(story);
    return { message: `Story "${title}" rejected and removed.` };
  }

  async getStats() {
    const total = await this.storyRepo.count();
    const published = await this.storyRepo.count({ where: { status: StoryStatus.PUBLISHED } });
    const drafts = await this.storyRepo.count({ where: { status: StoryStatus.DRAFT } });
    const pending = await this.storyRepo.count({ where: { status: StoryStatus.PENDING } });
    const views = await this.storyRepo.createQueryBuilder('story').select('SUM(story.views)', 'total').getRawOne();
    return { total, published, drafts, pending, totalViews: views?.total || 0 };
  }

  async getRecent() {
    return this.storyRepo.find({
      where: { status: StoryStatus.PUBLISHED },
      order: { createdAt: 'DESC' },
      take: 6,
    });
  }
}
