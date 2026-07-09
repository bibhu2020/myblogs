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

  // No longer a meaningful axis — every story now targets a single fixed audience
  // (see story_agent). Column kept so nothing downstream breaks; always written as a
  // constant now rather than user-selected.
  @Column({ default: '8-15' })
  ageGroup: string;

  // Fictional flavor: Horror | Sci-Fi | Thriller
  @Column({ nullable: true })
  genre: string;

  // Subject taught: AI | Robotics | Quantum
  @Column({ nullable: true })
  category: string;

  @Column({ nullable: true, type: 'text' })
  moralLesson: string;

  // URL of the pre-rendered TTS mp3 for this story (media library /uploads/ path), or
  // null if audio generation failed/was skipped at publish time.
  @Column({ nullable: true })
  audioUrl: string;

  // When true, the 30-day retention cleanup agent will never delete this story.
  @Column({ default: false })
  doNotDelete: boolean;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}
