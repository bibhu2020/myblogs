import { Controller, Get, Post, Put, Patch, Delete, Param, Body, Query, UseGuards, Request, Optional } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { PostsService } from './posts.service';

@Controller('posts')
export class PostsController {
  constructor(private postsService: PostsService) {}

  @Get()
  findAll(@Query() query: any) {
    return this.postsService.findAll(query);
  }

  @Get('featured')
  getFeatured() {
    return this.postsService.getFeatured();
  }

  @Get('recent')
  getRecent() {
    return this.postsService.getRecent();
  }

  @Get('stats')
  @UseGuards(AuthGuard('jwt'))
  getStats() {
    return this.postsService.getStats();
  }

  @Get('admin')
  @UseGuards(AuthGuard('jwt'))
  findAllAdmin(@Query() query: any) {
    return this.postsService.findAllAdmin(query);
  }

  @Get(':slug')
  findBySlug(@Param('slug') slug: string) {
    return this.postsService.findBySlug(slug);
  }

  @Post()
  @UseGuards(AuthGuard('jwt'))
  create(@Body() dto: any, @Request() req: any) {
    return this.postsService.create(dto, req.user);
  }

  @Patch(':id/approve')
  @UseGuards(AuthGuard('jwt'))
  approve(@Param('id') id: string) {
    return this.postsService.approve(+id);
  }

  @Patch(':id/reject')
  @UseGuards(AuthGuard('jwt'))
  reject(@Param('id') id: string) {
    return this.postsService.reject(+id);
  }

  @Put(':id')
  @UseGuards(AuthGuard('jwt'))
  update(@Param('id') id: string, @Body() dto: any) {
    return this.postsService.update(+id, dto);
  }

  @Delete(':id')
  @UseGuards(AuthGuard('jwt'))
  remove(@Param('id') id: string) {
    return this.postsService.remove(+id);
  }
}
