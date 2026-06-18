import {
  Controller,
  Get,
  Post,
  Patch,
  Put,
  Param,
  Body,
  UseGuards,
  Query,
} from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { AgentRunsService } from './agent-runs.service';

@Controller('agent-runs')
export class AgentRunsController {
  constructor(private agentRunsService: AgentRunsService) {}

  @Post()
  create(
    @Body()
    body: {
      agentType: string;
      runId: string;
      startedAt: string;
      metadata?: string;
    },
  ) {
    return this.agentRunsService.create(body);
  }

  @Patch(':runId')
  updatePatch(
    @Param('runId') runId: string,
    @Body()
    body: {
      status?: string;
      completedAt?: string;
      summary?: string;
      findings?: string;
    },
  ) {
    return this.agentRunsService.update(runId, body);
  }

  @Put(':runId')
  updatePut(
    @Param('runId') runId: string,
    @Body()
    body: {
      status?: string;
      completedAt?: string;
      summary?: string;
      findings?: string;
    },
  ) {
    return this.agentRunsService.update(runId, body);
  }

  @Post('dispatch')
  @UseGuards(AuthGuard('jwt'))
  dispatch(@Body() body: { workflow: string; inputs?: Record<string, string> }) {
    return this.agentRunsService.dispatch(body.workflow, body.inputs ?? {});
  }

  @Get()
  @UseGuards(AuthGuard('jwt'))
  findAll(@Query('limit') limit?: string) {
    return this.agentRunsService.findAll(limit ? parseInt(limit, 10) : 50);
  }

  @Get(':runId')
  @UseGuards(AuthGuard('jwt'))
  findOne(@Param('runId') runId: string) {
    return this.agentRunsService.findOne(runId);
  }
}
