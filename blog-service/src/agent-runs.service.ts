import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { AgentRun } from './agent-run.entity';

const GITHUB_REPO_FALLBACK = 'bibhu2020/myblogs';

const ALLOWED_WORKFLOWS = new Set([
  'run-story-agent.yml',
  'run-news-agent.yml',
  'run-post-agent.yml',
  'run-maintenance-agent.yml',
  'run-rebranding-agent.yml',
]);

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

  async dispatch(workflow: string, inputs: Record<string, string> = {}): Promise<{ queued: boolean }> {
    if (!ALLOWED_WORKFLOWS.has(workflow)) {
      throw new BadRequestException(`Unknown workflow: ${workflow}`);
    }
    const token = process.env.SECRET_TOKEN_GITHUB;
    const repo  = process.env.GITHUB_REPO || GITHUB_REPO_FALLBACK;
    if (!token) {
      throw new BadRequestException('SECRET_TOKEN_GITHUB is not configured on the server');
    }
    const resp = await fetch(
      `https://api.github.com/repos/${repo}/actions/workflows/${workflow}/dispatches`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/vnd.github.v3+json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ref: 'main', inputs }),
      },
    );
    if (!resp.ok) {
      const body = await resp.text();
      throw new BadRequestException(`GitHub API error ${resp.status}: ${body.slice(0, 200)}`);
    }
    return { queued: true };
  }
}
