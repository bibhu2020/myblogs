import { Controller, Get, Post, Put, Patch, Delete, Param, Body, Query, UseGuards, Request } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { StoriesService } from './stories.service';

@Controller('stories')
export class StoriesController {
  constructor(private storiesService: StoriesService) {}

  @Get()
  findAll(@Query() query: any) {
    return this.storiesService.findAll(query);
  }

  @Get('recent')
  getRecent() {
    return this.storiesService.getRecent();
  }

  @Get('stats')
  @UseGuards(AuthGuard('jwt'))
  getStats() {
    return this.storiesService.getStats();
  }

  @Get('admin')
  @UseGuards(AuthGuard('jwt'))
  findAllAdmin(@Query() query: any) {
    return this.storiesService.findAllAdmin(query);
  }

  @Get(':slug')
  findBySlug(@Param('slug') slug: string) {
    return this.storiesService.findBySlug(slug);
  }

  @Post()
  @UseGuards(AuthGuard('jwt'))
  create(@Body() dto: any, @Request() req: any) {
    return this.storiesService.create(dto, req.user);
  }

  @Patch(':id/approve')
  @UseGuards(AuthGuard('jwt'))
  approve(@Param('id') id: string) {
    return this.storiesService.approve(+id);
  }

  @Patch(':id/reject')
  @UseGuards(AuthGuard('jwt'))
  reject(@Param('id') id: string) {
    return this.storiesService.reject(+id);
  }

  @Put(':id')
  @UseGuards(AuthGuard('jwt'))
  update(@Param('id') id: string, @Body() dto: any) {
    return this.storiesService.update(+id, dto);
  }

  @Delete(':id')
  @UseGuards(AuthGuard('jwt'))
  remove(@Param('id') id: string) {
    return this.storiesService.remove(+id);
  }
}
