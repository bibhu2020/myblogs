import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Category } from './category.entity';
import slugify from 'slugify';

@Injectable()
export class CategoriesService {
  constructor(@InjectRepository(Category) private catRepo: Repository<Category>) {}

  findAll() {
    return this.catRepo.find();
  }

  async findOne(id: number) {
    const cat = await this.catRepo.findOne({ where: { id } });
    if (!cat) throw new NotFoundException('Category not found');
    return cat;
  }

  async create(dto: { name: string; description?: string; color?: string; icon?: string }) {
    const slug = slugify(dto.name, { lower: true, strict: true });
    return this.catRepo.save(this.catRepo.create({ ...dto, slug }));
  }

  async update(id: number, dto: any) {
    const cat = await this.findOne(id);
    if (dto.name) dto.slug = slugify(dto.name, { lower: true, strict: true });
    Object.assign(cat, dto);
    return this.catRepo.save(cat);
  }

  async remove(id: number) {
    const cat = await this.findOne(id);
    await this.catRepo.remove(cat);
    return { message: 'Category deleted' };
  }
}
