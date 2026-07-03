import { AgentRunsController } from './agent-runs.controller';
import { AgentRunsService } from './agent-runs.service';

describe('AgentRunsController', () => {
  const mockAgentRunsService = {
    create: jest.fn(),
    update: jest.fn(),
    dispatch: jest.fn(),
    findAll: jest.fn(),
    findOne: jest.fn(),
  } as unknown as AgentRunsService;

  let controller: AgentRunsController;

  beforeEach(() => {
    jest.clearAllMocks();
    controller = new AgentRunsController(mockAgentRunsService);
  });

  it('delegates create to AgentRunsService with the body', () => {
    const body = { agentType: 'story', runId: 'r1', startedAt: '2026-01-01' };
    controller.create(body);
    expect(mockAgentRunsService.create).toHaveBeenCalledWith(body);
  });

  it('delegates updatePatch to AgentRunsService with runId and body', () => {
    const body = { status: 'completed' };
    controller.updatePatch('r1', body);
    expect(mockAgentRunsService.update).toHaveBeenCalledWith('r1', body);
  });

  it('delegates updatePut to AgentRunsService with runId and body', () => {
    const body = { status: 'completed' };
    controller.updatePut('r1', body);
    expect(mockAgentRunsService.update).toHaveBeenCalledWith('r1', body);
  });

  it('delegates dispatch to AgentRunsService with workflow and inputs', () => {
    controller.dispatch({ workflow: 'run-story-agent.yml', inputs: { a: '1' } });
    expect(mockAgentRunsService.dispatch).toHaveBeenCalledWith('run-story-agent.yml', { a: '1' });
  });

  it('defaults dispatch inputs to an empty object when omitted', () => {
    controller.dispatch({ workflow: 'run-story-agent.yml' });
    expect(mockAgentRunsService.dispatch).toHaveBeenCalledWith('run-story-agent.yml', {});
  });

  it('delegates findAll to AgentRunsService with a parsed limit', () => {
    controller.findAll('25');
    expect(mockAgentRunsService.findAll).toHaveBeenCalledWith(25);
  });

  it('defaults findAll limit to 50 when omitted', () => {
    controller.findAll();
    expect(mockAgentRunsService.findAll).toHaveBeenCalledWith(50);
  });

  it('delegates findOne to AgentRunsService with the runId', () => {
    controller.findOne('r1');
    expect(mockAgentRunsService.findOne).toHaveBeenCalledWith('r1');
  });
});
