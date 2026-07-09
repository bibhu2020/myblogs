import { Injectable, NotFoundException, InternalServerErrorException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Media } from './media.entity';
import * as fs from 'fs';

const GH_OWNER = 'bibhu2020';
const GH_REPO  = 'media';
const GH_BRANCH = 'main';
// Images/other files go under myblogs/uploads; audio narration mp3s get their own
// folder so the media repo stays organised by content type.
const GH_UPLOADS_PATH = 'myblogs/uploads';
const GH_AUDIO_PATH   = 'myblogs/audio';

function ghPathFor(mimetype: string): string {
  return mimetype?.startsWith('audio/') ? GH_AUDIO_PATH : GH_UPLOADS_PATH;
}
function rawBaseFor(mimetype: string): string {
  return `https://raw.githubusercontent.com/${GH_OWNER}/${GH_REPO}/${GH_BRANCH}/${ghPathFor(mimetype)}`;
}
function apiBaseFor(mimetype: string): string {
  return `https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/contents/${ghPathFor(mimetype)}`;
}

@Injectable()
export class MediaService {
  constructor(@InjectRepository(Media) private mediaRepo: Repository<Media>) {}

  private ghHeaders() {
    const token = process.env.SECRET_TOKEN_GITHUB;
    if (!token) throw new InternalServerErrorException('SECRET_TOKEN_GITHUB is not configured');
    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      Accept: 'application/vnd.github.v3+json',
      'User-Agent': 'meridian-media-service',
    };
  }

  async save(file: Express.Multer.File, userId: number, alt?: string) {
    const content = fs.readFileSync(file.path).toString('base64');

    // Try GitHub upload; on failure keep the local copy and serve it from /uploads/
    let url = `/uploads/${file.filename}`;
    try {
      const headers = this.ghHeaders();
      const res = await fetch(`${apiBaseFor(file.mimetype)}/${file.filename}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({ message: `Upload ${file.filename}`, content, branch: GH_BRANCH }),
      });
      if (res.ok) {
        url = `${rawBaseFor(file.mimetype)}/${file.filename}`;
        if (fs.existsSync(file.path)) fs.unlinkSync(file.path);
      } else {
        const body = await res.text();
        console.warn(`GitHub upload failed (${res.status}) — using local storage: ${body.slice(0, 200)}`);
      }
    } catch (err) {
      console.warn(`GitHub upload error — using local storage: ${err.message}`);
    }

    const media = this.mediaRepo.create({
      filename: file.filename,
      originalName: file.originalname,
      mimetype: file.mimetype,
      size: file.size,
      url,
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
    if (!media) throw new NotFoundException('Media not found');

    const headers = this.ghHeaders();
    const apiUrl = `${apiBaseFor(media.mimetype)}/${media.filename}`;

    const getRes = await fetch(apiUrl, { headers });
    if (getRes.ok) {
      const { sha } = await getRes.json() as { sha: string };
      await fetch(apiUrl, {
        method: 'DELETE',
        headers,
        body: JSON.stringify({
          message: `Delete ${media.filename}`,
          sha,
          branch: GH_BRANCH,
        }),
      });
    }

    await this.mediaRepo.remove(media);
    return { message: 'Media deleted' };
  }
}
