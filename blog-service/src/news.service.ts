import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { NewsItem } from './news-item.entity';
import { PushService } from './push.service';

@Injectable()
export class NewsService {
  constructor(
    @InjectRepository(NewsItem)
    private readonly repo: Repository<NewsItem>,
    private readonly pushService: PushService,
  ) {}

  async findAll(region?: string): Promise<{ items: NewsItem[]; lastUpdated: Date | null }> {
    // sortOrder reflects the agent's intentional curation order and is always set by the
    // only writer (refresh()) — createdAt would tie across all items in the same batch.
    const qb = this.repo.createQueryBuilder('n').orderBy('n.sortOrder', 'ASC');
    if (region && region !== 'all') qb.where('n.region = :region', { region });
    const items = await qb.getMany();
    const lastUpdated = items.length ? items[0].createdAt : null;
    return { items, lastUpdated };
  }

  async refresh(items: Partial<NewsItem>[]): Promise<{ count: number; items: NewsItem[] }> {
    await this.repo.clear();
    const entities = this.repo.create(items);
    // save() returns the entities with their TypeORM-assigned auto-increment ids —
    // the news agent needs these to name each item's narration mp3 deterministically
    // (news_<id>.mp3) and to attach the resulting audioUrl via updateOne() afterwards.
    const saved = await this.repo.save(entities);
    void this.pushService.send({
      title: `News — ${saved.length} new articles`,
      body: 'Tap to read the latest news on Meridian',
      url: '/news',
    });
    return { count: saved.length, items: saved };
  }

  async updateOne(id: number, dto: Partial<NewsItem>): Promise<NewsItem> {
    const item = await this.repo.findOne({ where: { id } });
    if (!item) throw new NotFoundException('News item not found');
    Object.assign(item, dto);
    return this.repo.save(item);
  }
}
