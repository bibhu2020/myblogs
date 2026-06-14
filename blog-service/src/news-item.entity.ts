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
  region: string;  // world | usa | india | odisha

  @Column({ nullable: true })
  publishedAt: string;

  @CreateDateColumn()
  createdAt: Date;
}
