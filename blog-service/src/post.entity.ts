import { Entity, PrimaryGeneratedColumn, Column, ManyToOne, ManyToMany, OneToMany, JoinTable, CreateDateColumn, UpdateDateColumn } from 'typeorm';
import { Category } from './category.entity';
import { Tag } from './tag.entity';
import { Comment } from './comment.entity';

export enum PostStatus {
  DRAFT = 'draft',
  PENDING = 'pending',
  PUBLISHED = 'published',
}

@Entity('blog_posts')
export class Post {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  title: string;

  @Column({ unique: true })
  slug: string;

  @Column({ type: 'text' })
  content: string;

  @Column({ nullable: true, type: 'text' })
  excerpt: string;

  @Column({ nullable: true })
  featuredImage: string;

  @Column({ nullable: true, type: 'text' })
  gallery: string;

  @Column({ type: 'varchar', default: PostStatus.DRAFT })
  status: PostStatus;

  @Column()
  authorId: number;

  @Column({ nullable: true })
  authorName: string;

  @Column({ nullable: true })
  readTime: number;

  @Column({ default: 0 })
  views: number;

  /* istanbul ignore next -- lazy relation resolver, only invoked by a live TypeORM connection */
  @ManyToOne(() => Category, cat => cat.posts, { nullable: true, eager: true })
  category: Category;

  /* istanbul ignore next -- lazy relation resolver, only invoked by a live TypeORM connection */
  @ManyToMany(() => Tag, { eager: true, cascade: true })
  @JoinTable({
    name: 'blog_posts_tags_tags',
    joinColumn: { name: 'postsId', referencedColumnName: 'id' },
    inverseJoinColumn: { name: 'tagsId', referencedColumnName: 'id' },
  })
  tags: Tag[];

  /* istanbul ignore next -- lazy relation resolver, only invoked by a live TypeORM connection */
  @OneToMany(() => Comment, c => c.post)
  comments: Comment[];

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}
