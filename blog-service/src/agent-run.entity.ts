import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn } from 'typeorm';

@Entity('agent_runs')
export class AgentRun {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  agentType: string;

  @Column({ unique: true })
  runId: string;

  @Column()
  startedAt: string;

  @Column({ nullable: true })
  completedAt: string;

  @Column({ default: 'running' })
  status: string;

  @Column({ nullable: true, type: 'text' })
  summary: string;

  @Column({ nullable: true, type: 'text' })
  findings: string;

  @Column({ nullable: true, type: 'text' })
  metadata: string;
}
