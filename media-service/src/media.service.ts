import { Injectable, InternalServerErrorException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Media } from './media.entity';
import * as fs from 'fs';

const GH_OWNER = 'bibhu2020';
const GH_REPO = 'media';
const GH_BRANCH = 'main';
const GH_PATH = 'uploads';
const RAW_BASE = `https://raw.githubusercontent.com/${GH_OWNER}/${GH_REPO}/${GH_BRANCH}/${GH_PATH}`;
const API_BASE = `https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/contents/${GH_PATH}`;

@Injectable()
export class MediaService {
  constructor(@InjectRepository(Media) private mediaRepo: Repository<Media>) {}

  private headers() {
    return {
      Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
      'Content-Type': 'application/json',
      Accept: 'application/vnd.github.v3+json',
      'User-Agent': 'myblogs-media-service',
    };
  }

  async save(file: Express.Multer.File, userId: number, alt?: string) {
    const content = fs.readFileSync(file.path).toString('base64');

    const res = await fetch(`${API_BASE}/${file.filename}`, {
      method: 'PUT',
      headers: this.headers(),
      body: JSON.stringify({ message: `Upload ${file.filename}`, content, branch: GH_BRANCH }),
    });

    if (fs.existsSync(file.path)) fs.unlinkSync(file.path);

    if (!res.ok) {
      throw new InternalServerErrorException(`GitHub upload failed: ${await res.text()}`);
    }

    const media = this.mediaRepo.create({
      filename: file.filename,
      originalName: file.originalname,
      mimetype: file.mimetype,
      size: file.size,
      url: `${RAW_BASE}/${file.filename}`,
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
      const apiUrl = `${API_BASE}/${media.filename}`;
      const getRes = await fetch(apiUrl, { headers: this.headers() });
      if (getRes.ok) {
        const { sha } = await getRes.json() as { sha: string };
        await fetch(apiUrl, {
          method: 'DELETE',
          headers: this.headers(),
          body: JSON.stringify({ message: `Delete ${media.filename}`, sha, branch: GH_BRANCH }),
        });
      }
      await this.mediaRepo.remove(media);
    }
    return { message: 'Media deleted' };
  }
}
