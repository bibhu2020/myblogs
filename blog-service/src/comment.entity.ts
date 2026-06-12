import { Entity, PrimaryGeneratedColumn, Column, ManyToOne, CreateDateColumn } from 'typeorm';
import { Post } from './post.entity';

@Entity('blog_comments')
export class Comment {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ type: 'text' })
  content: string;

  @Column()
  authorName: string;

  @Column({ nullable: true })
  authorEmail: string;

  @Column({ nullable: true })
  authorId: number;

  @Column({ default: false })
  approved: boolean;

  @ManyToOne(() => Post, post => post.comments)
  post: Post;

  @CreateDateColumn()
  createdAt: Date;
}
