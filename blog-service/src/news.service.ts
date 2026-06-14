import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { NewsItem } from './news-item.entity';

@Injectable()
export class NewsService {
  constructor(
    @InjectRepository(NewsItem)
    private readonly repo: Repository<NewsItem>,
  ) {}

  async findAll(region?: string): Promise<{ items: NewsItem[]; lastUpdated: Date | null }> {
    const qb = this.repo.createQueryBuilder('n').orderBy('n.createdAt', 'DESC');
    if (region && region !== 'all') qb.where('n.region = :region', { region });
    const items = await qb.getMany();
    const lastUpdated = items.length ? items[0].createdAt : null;
    return { items, lastUpdated };
  }

  async refresh(items: Partial<NewsItem>[]): Promise<{ count: number }> {
    await this.repo.clear();
    const entities = this.repo.create(items);
    await this.repo.save(entities);
    return { count: entities.length };
  }
}
