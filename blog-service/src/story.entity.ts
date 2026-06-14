import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn } from 'typeorm';

export enum StoryStatus {
  DRAFT = 'draft',
  PENDING = 'pending',
  PUBLISHED = 'published',
}

@Entity('stories')
export class Story {
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

  @Column({ type: 'varchar', default: StoryStatus.DRAFT })
  status: StoryStatus;

  @Column({ default: 0 })
  authorId: number;

  @Column({ nullable: true })
  authorName: string;

  @Column({ nullable: true })
  readTime: number;

  @Column({ default: 0 })
  views: number;

  @Column({ default: '8-15' })
  ageGroup: string;

  @Column({ nullable: true })
  genre: string;

  @Column({ nullable: true, type: 'text' })
  moralLesson: string;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}
