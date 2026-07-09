import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn } from 'typeorm';

@Entity('news_items')
export class NewsItem {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  title: string;

  @Column({ type: 'text' })
  summary: string;

  @Column({ nullable: true })
  imageUrl: string;

  @Column({ type: 'text' })
  sourceUrl: string;

  @Column({ nullable: true })
  sourceName: string;

  @Column({ default: 'world' })
  region: string;  // ai | quantum | jobmarket

  @Column({ nullable: true })
  publishedAt: string;

  // URL of this item's pre-rendered TTS mp3 (media library /uploads/ path), or null if
  // audio generation failed/was skipped when the agent published this item.
  @Column({ nullable: true })
  audioUrl: string;

  // 0-based curation order assigned by the news agent (0-9) — used both to order the
  // "Listen to all" playlist deterministically and as the item's narration file number.
  @Column({ nullable: true, type: 'int' })
  sortOrder: number;

  @CreateDateColumn()
  createdAt: Date;
}
