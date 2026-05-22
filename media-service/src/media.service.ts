import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Media } from './media.entity';

@Injectable()
export class MediaService {
  constructor(@InjectRepository(Media) private mediaRepo: Repository<Media>) {}

  async save(file: Express.Multer.File, userId: number, alt?: string) {
    const media = this.mediaRepo.create({
      filename: file.filename,
      originalName: file.originalname,
      mimetype: file.mimetype,
      size: file.size,
      url: `/uploads/${file.filename}`,
      alt: alt || file.originalname,
      uploadedBy: userId,
    });
    return this.mediaRepo.save(media);
  }

  findAll() {
    return this.mediaRepo.find({ order: { createdAt: 'DESC' } });
  }

  async remove(id: number) {
    const media = await this.mediaRepo.findOne({ where: { id } });
    if (media) {
      const fs = require('fs');
      const path = require('path');
      const filePath = path.join(process.cwd(), 'uploads', media.filename);
      if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
      await this.mediaRepo.remove(media);
    }
    return { message: 'Media deleted' };
  }
}
