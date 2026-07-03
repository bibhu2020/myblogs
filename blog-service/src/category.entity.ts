import { Entity, PrimaryGeneratedColumn, Column, OneToMany, CreateDateColumn } from 'typeorm';
import { Post } from './post.entity';

@Entity('blog_categories')
export class Category {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ unique: true })
  name: string;

  @Column({ unique: true })
  slug: string;

  @Column({ nullable: true })
  description: string;

  @Column({ nullable: true })
  color: string;

  @Column({ nullable: true })
  icon: string;

  /* istanbul ignore next -- lazy relation resolver, only invoked by a live TypeORM connection */
  @OneToMany(() => Post, post => post.category)
  posts: Post[];

  @CreateDateColumn()
  createdAt: Date;
}
