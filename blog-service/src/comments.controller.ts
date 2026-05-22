import { Controller, Get, Post, Delete, Put, Param, Body, UseGuards } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { CommentsService } from './comments.service';

@Controller('comments')
export class CommentsController {
  constructor(private commentsService: CommentsService) {}

  @Get()
  @UseGuards(AuthGuard('jwt'))
  findAll() { return this.commentsService.findAll(); }

  @Get('post/:postId')
  findByPost(@Param('postId') postId: string) { return this.commentsService.findByPost(+postId); }

  @Post('post/:postId')
  create(@Param('postId') postId: string, @Body() dto: any) { return this.commentsService.create(+postId, dto); }

  @Put(':id/approve')
  @UseGuards(AuthGuard('jwt'))
  approve(@Param('id') id: string) { return this.commentsService.approve(+id); }

  @Delete(':id')
  @UseGuards(AuthGuard('jwt'))
  remove(@Param('id') id: string) { return this.commentsService.remove(+id); }
}
