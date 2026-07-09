import { Controller, Get, Post, Patch, Body, Param, Query, UseGuards } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { NewsService } from './news.service';

@Controller('news')
export class NewsController {
  constructor(private readonly newsService: NewsService) {}

  @Get()
  getAll(@Query('region') region?: string) {
    return this.newsService.findAll(region);
  }

  @Post('refresh')
  @UseGuards(AuthGuard('jwt'))
  refresh(@Body() body: { items: any[] }) {
    return this.newsService.refresh(body.items || []);
  }

  @Patch(':id')
  @UseGuards(AuthGuard('jwt'))
  updateOne(@Param('id') id: string, @Body() body: any) {
    return this.newsService.updateOne(+id, body);
  }
}
