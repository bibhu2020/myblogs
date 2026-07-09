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

  // When true, the 30-day retention cleanup agent will never delete this post.
  @Column({ default: false })
  doNotDelete: boolean;

  // URL of the pre-rendered TTS mp3 for this post (media library /uploads/ path), or null
  // if audio generation failed/was skipped at publish time.
  @Column({ nullable: true })
  audioUrl: string;

  // Curriculum series tracking (Educational category only) — e.g. "general-relativity".
  @Column({ nullable: true })
  seriesKey: string;

  // 0-based position within the seriesKey track's ordered topic list.
  @Column({ nullable: true, type: 'int' })
  seriesIndex: number;

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
