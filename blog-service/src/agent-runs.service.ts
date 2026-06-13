import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { AgentRun } from './agent-run.entity';

@Injectable()
export class AgentRunsService {
  constructor(
    @InjectRepository(AgentRun) private repo: Repository<AgentRun>,
  ) {}

  async create(dto: {
    agentType: string;
    runId: string;
    startedAt: string;
    metadata?: string;
  }): Promise<AgentRun> {
    const run = this.repo.create({
      agentType: dto.agentType,
      runId: dto.runId,
      startedAt: dto.startedAt,
      metadata: dto.metadata ?? null,
      status: 'running',
    });
    return this.repo.save(run);
  }

  async update(
    runId: string,
    dto: {
      status?: string;
      completedAt?: string;
      summary?: string;
      findings?: string;
    },
  ): Promise<AgentRun> {
    const run = await this.repo.findOne({ where: { runId } });
    if (!run) throw new NotFoundException(`AgentRun ${runId} not found`);
    if (dto.status !== undefined) run.status = dto.status;
    if (dto.completedAt !== undefined) run.completedAt = dto.completedAt;
    if (dto.summary !== undefined) run.summary = dto.summary;
    if (dto.findings !== undefined) run.findings = dto.findings;
    return this.repo.save(run);
  }

  async findAll(limit = 50): Promise<AgentRun[]> {
    return this.repo.find({ order: { id: 'DESC' }, take: limit });
  }

  async findOne(runId: string): Promise<AgentRun> {
    const run = await this.repo.findOne({ where: { runId } });
    if (!run) throw new NotFoundException(`AgentRun ${runId} not found`);
    return run;
  }
}
