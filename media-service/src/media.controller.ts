import { Controller, Get, Post, Delete, Param, Body, UseGuards, UseInterceptors, UploadedFile, Request } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { FileInterceptor } from '@nestjs/platform-express';
import { MediaService } from './media.service';

@Controller('media')
export class MediaController {
  constructor(private mediaService: MediaService) {}

  @Get()
  @UseGuards(AuthGuard('jwt'))
  findAll() { return this.mediaService.findAll(); }

  @Post('upload')
  @UseGuards(AuthGuard('jwt'))
  @UseInterceptors(FileInterceptor('file'))
  upload(@UploadedFile() file: Express.Multer.File, @Request() req: any, @Body('alt') alt: string) {
    return this.mediaService.save(file, req.user.id, alt);
  }

  // Declared before ':id' — Express/Nest route matching is order-sensitive, and ':id'
  // would otherwise greedily match the literal segment "by-filename" first.
  @Delete('by-filename/:filename')
  @UseGuards(AuthGuard('jwt'))
  removeByFilename(@Param('filename') filename: string) {
    return this.mediaService.removeByFilename(filename);
  }

  @Delete(':id')
  @UseGuards(AuthGuard('jwt'))
  remove(@Param('id') id: string) { return this.mediaService.remove(+id); }
}
