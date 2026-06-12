import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn } from 'typeorm';

@Entity('media_media')
export class Media {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  filename: string;

  @Column()
  originalName: string;

  @Column()
  mimetype: string;

  @Column()
  size: number;

  @Column()
  url: string;

  @Column({ nullable: true })
  alt: string;

  @Column({ nullable: true })
  uploadedBy: number;

  @CreateDateColumn()
  createdAt: Date;
}
