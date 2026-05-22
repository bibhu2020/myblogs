import { Controller, Get, Post, Put, Delete, Param, Body, UseGuards } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { CategoriesService } from './categories.service';

@Controller('categories')
export class CategoriesController {
  constructor(private categoriesService: CategoriesService) {}

  @Get()
  findAll() { return this.categoriesService.findAll(); }

  @Post()
  @UseGuards(AuthGuard('jwt'))
  create(@Body() dto: any) { return this.categoriesService.create(dto); }

  @Put(':id')
  @UseGuards(AuthGuard('jwt'))
  update(@Param('id') id: string, @Body() dto: any) { return this.categoriesService.update(+id, dto); }

  @Delete(':id')
  @UseGuards(AuthGuard('jwt'))
  remove(@Param('id') id: string) { return this.categoriesService.remove(+id); }
}
