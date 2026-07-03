import { Test, TestingModule } from '@nestjs/testing';
import { AgentRunsService } from './agent-runs.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { AgentRun } from './agent-run.entity';
import { NotFoundException, BadRequestException } from '@nestjs/common';

const mockRepo = {
  create: jest.fn(),
  save: jest.fn(),
  findOne: jest.fn(),
  find: jest.fn(),
};

const mockRun = {
  id: 1,
  agentType: 'story',
  runId: 'r1',
  startedAt: '2026-01-01',
  status: 'running',
};

describe('AgentRunsService', () => {
  let service: AgentRunsService;
  const ORIGINAL_ENV = process.env;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        AgentRunsService,
        { provide: getRepositoryToken(AgentRun), useValue: mockRepo },
      ],
    }).compile();
    service = module.get<AgentRunsService>(AgentRunsService);
    jest.clearAllMocks();
    process.env = { ...ORIGINAL_ENV };
    global.fetch = jest.fn();
  });

  afterAll(() => {
    process.env = ORIGINAL_ENV;
  });

  describe('create', () => {
    it('creates a run with status running', async () => {
      mockRepo.create.mockImplementation((r) => r);
      mockRepo.save.mockImplementation(async (r) => r);
      const result = await service.create({ agentType: 'story', runId: 'r1', startedAt: '2026-01-01' });
      expect(result.status).toBe('running');
    });
  });

  describe('update', () => {
    it('updates only the provided fields', async () => {
      mockRepo.findOne.mockResolvedValue({ ...mockRun });
      mockRepo.save.mockImplementation(async (r) => r);
      const result = await service.update('r1', { status: 'completed', summary: 'done' });
      expect(result.status).toBe('completed');
      expect(result.summary).toBe('done');
    });

    it('throws NotFoundException when the run is missing', async () => {
      mockRepo.findOne.mockResolvedValue(null);
      await expect(service.update('missing', { status: 'completed' })).rejects.toThrow(NotFoundException);
    });
  });

  describe('findAll', () => {
    it('returns runs ordered by id descending with the given limit', async () => {
      mockRepo.find.mockResolvedValue([mockRun]);
      const result = await service.findAll(10);
      expect(mockRepo.find).toHaveBeenCalledWith({ order: { id: 'DESC' }, take: 10 });
      expect(result).toHaveLength(1);
    });
  });

  describe('findOne', () => {
    it('returns the run by runId', async () => {
      mockRepo.findOne.mockResolvedValue(mockRun);
      const result = await service.findOne('r1');
      expect(result).toBe(mockRun);
    });

    it('throws NotFoundException when missing', async () => {
      mockRepo.findOne.mockResolvedValue(null);
      await expect(service.findOne('missing')).rejects.toThrow(NotFoundException);
    });
  });

  describe('dispatch', () => {
    it('throws BadRequestException for an unknown workflow', async () => {
      await expect(service.dispatch('not-a-real-workflow.yml')).rejects.toThrow(BadRequestException);
    });

    it('throws BadRequestException when no GitHub token is configured', async () => {
      delete process.env.SECRET_TOKEN_GITHUB;
      await expect(service.dispatch('run-story-agent.yml')).rejects.toThrow(BadRequestException);
    });

    it('queues the workflow when the GitHub API accepts the dispatch', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      (global.fetch as jest.Mock).mockResolvedValue({ ok: true });
      const result = await service.dispatch('run-story-agent.yml', { a: '1' });
      expect(result).toEqual({ queued: true });
    });

    it('throws BadRequestException when the GitHub API rejects the dispatch', async () => {
      process.env.SECRET_TOKEN_GITHUB = 'gh-token';
      (global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 422, text: async () => 'bad input' });
      await expect(service.dispatch('run-story-agent.yml')).rejects.toThrow(BadRequestException);
    });
  });
});
