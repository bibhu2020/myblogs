import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Comment } from './comment.entity';
import { Post } from './post.entity';

@Injectable()
export class CommentsService {
  constructor(
    @InjectRepository(Comment) private commentRepo: Repository<Comment>,
    @InjectRepository(Post) private postRepo: Repository<Post>,
  ) {}

  async findByPost(postId: number) {
    return this.commentRepo.find({ where: { post: { id: postId }, approved: true }, order: { createdAt: 'ASC' } });
  }

  async create(postId: number, dto: any) {
    const post = await this.postRepo.findOne({ where: { id: postId } });
    const comment = this.commentRepo.create({ ...dto, post, approved: false });
    return this.commentRepo.save(comment);
  }

  async approve(id: number) {
    await this.commentRepo.update(id, { approved: true });
    return this.commentRepo.findOne({ where: { id } });
  }

  async remove(id: number) {
    const c = await this.commentRepo.findOne({ where: { id } });
    if (c) await this.commentRepo.remove(c);
    return { message: 'Comment deleted' };
  }

  async findAll() {
    return this.commentRepo.find({ relations: ['post'], order: { createdAt: 'DESC' } });
  }
}
