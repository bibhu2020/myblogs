import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Tag } from './tag.entity';
import slugify from 'slugify';

@Injectable()
export class TagsService {
  constructor(@InjectRepository(Tag) private tagRepo: Repository<Tag>) {}

  findAll() { return this.tagRepo.find(); }

  async create(dto: { name: string }) {
    const slug = slugify(dto.name, { lower: true, strict: true });
    const existing = await this.tagRepo.findOne({ where: { slug } });
    if (existing) return existing;
    return this.tagRepo.save(this.tagRepo.create({ name: dto.name, slug }));
  }

  async createMany(names: string[]) {
    return Promise.all(names.map(name => this.create({ name })));
  }

  async remove(id: number) {
    const tag = await this.tagRepo.findOne({ where: { id } });
    if (tag) await this.tagRepo.remove(tag);
    return { message: 'Tag deleted' };
  }
}
