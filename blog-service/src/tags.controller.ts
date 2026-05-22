import { Controller, Get, Post, Delete, Param, Body, UseGuards } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { TagsService } from './tags.service';

@Controller('tags')
export class TagsController {
  constructor(private tagsService: TagsService) {}

  @Get()
  findAll() { return this.tagsService.findAll(); }

  @Post()
  @UseGuards(AuthGuard('jwt'))
  create(@Body() dto: any) { return this.tagsService.create(dto); }

  @Post('many')
  @UseGuards(AuthGuard('jwt'))
  createMany(@Body() dto: { names: string[] }) { return this.tagsService.createMany(dto.names); }

  @Delete(':id')
  @UseGuards(AuthGuard('jwt'))
  remove(@Param('id') id: string) { return this.tagsService.remove(+id); }
}
