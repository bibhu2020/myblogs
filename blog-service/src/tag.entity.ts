import { Entity, PrimaryGeneratedColumn, Column, ManyToMany } from 'typeorm';
import { Post } from './post.entity';

@Entity('blog_tags')
export class Tag {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ unique: true })
  name: string;

  @Column({ unique: true })
  slug: string;

  /* istanbul ignore next -- lazy relation resolver, only invoked by a live TypeORM connection */
  @ManyToMany(() => Post, post => post.tags)
  posts: Post[];
}
