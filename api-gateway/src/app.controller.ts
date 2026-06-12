import {
  Controller, All, Req, Res, Next, Get, Post, Put, Delete, Param, Body, Query,
  UseGuards, Request, UseInterceptors, UploadedFile, Headers, HttpCode
} from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { FileInterceptor } from '@nestjs/platform-express';
import { memoryStorage } from 'multer';
import { ProxyService } from './proxy.service';
import { Request as ExpressRequest, Response } from 'express';


@Controller('api')
export class AppController {
  constructor(private proxy: ProxyService) {}

  private getAuthHeader(req: any) {
    return req.headers?.authorization || '';
  }

  // AUTH ROUTES
  @Post('auth/login')
  login(@Body() body: any) {
    return this.proxy.forward('auth', '/auth/login', 'POST', body);
  }

  @Get('auth/verify')
  @UseGuards(AuthGuard('jwt'))
  verify(@Request() req: any) {
    return req.user;
  }

  // USER ROUTES
  @Get('users')
  @UseGuards(AuthGuard('jwt'))
  getUsers(@Request() req: any) {
    return this.proxy.forward('auth', '/users', 'GET', null, { Authorization: this.getAuthHeader(req) });
  }

  @Post('users')
  @UseGuards(AuthGuard('jwt'))
  createUser(@Body() body: any, @Request() req: any) {
    return this.proxy.forward('auth', '/users', 'POST', body, { Authorization: this.getAuthHeader(req) });
  }

  @Put('users/:id')
  @UseGuards(AuthGuard('jwt'))
  updateUser(@Param('id') id: string, @Body() body: any, @Request() req: any) {
    return this.proxy.forward('auth', `/users/${id}`, 'PUT', body, { Authorization: this.getAuthHeader(req) });
  }

  @Delete('users/:id')
  @UseGuards(AuthGuard('jwt'))
  deleteUser(@Param('id') id: string, @Request() req: any) {
    return this.proxy.forward('auth', `/users/${id}`, 'DELETE', null, { Authorization: this.getAuthHeader(req) });
  }

  // BLOG ROUTES - Public
  @Get('posts')
  getPosts(@Query() query: any) {
    const params = new URLSearchParams(query).toString();
    return this.proxy.forward('blog', `/posts?${params}`, 'GET');
  }

  @Get('posts/featured')
  getFeatured() { return this.proxy.forward('blog', '/posts/featured', 'GET'); }

  @Get('posts/recent')
  getRecent() { return this.proxy.forward('blog', '/posts/recent', 'GET'); }

  @Get('posts/stats')
  @UseGuards(AuthGuard('jwt'))
  getStats(@Request() req: any) {
    return this.proxy.forward('blog', '/posts/stats', 'GET', null, { Authorization: this.getAuthHeader(req) });
  }

  @Get('posts/admin')
  @UseGuards(AuthGuard('jwt'))
  getAdminPosts(@Query() query: any, @Request() req: any) {
    const params = new URLSearchParams({ ...query, status: query.status || '' }).toString();
    return this.proxy.forward('blog', `/posts/admin?${params}`, 'GET', null, { Authorization: this.getAuthHeader(req) });
  }

  @Get('posts/:slug')
  getPost(@Param('slug') slug: string) {
    return this.proxy.forward('blog', `/posts/${slug}`, 'GET');
  }

  @Post('posts')
  @UseGuards(AuthGuard('jwt'))
  createPost(@Body() body: any, @Request() req: any) {
    return this.proxy.forward('blog', '/posts', 'POST', body, { Authorization: this.getAuthHeader(req) });
  }

  @Put('posts/:id')
  @UseGuards(AuthGuard('jwt'))
  updatePost(@Param('id') id: string, @Body() body: any, @Request() req: any) {
    return this.proxy.forward('blog', `/posts/${id}`, 'PUT', body, { Authorization: this.getAuthHeader(req) });
  }

  @Delete('posts/:id')
  @UseGuards(AuthGuard('jwt'))
  deletePost(@Param('id') id: string, @Request() req: any) {
    return this.proxy.forward('blog', `/posts/${id}`, 'DELETE', null, { Authorization: this.getAuthHeader(req) });
  }

  // CATEGORIES
  @Get('categories')
  getCategories() { return this.proxy.forward('blog', '/categories', 'GET'); }

  @Post('categories')
  @UseGuards(AuthGuard('jwt'))
  createCategory(@Body() body: any, @Request() req: any) {
    return this.proxy.forward('blog', '/categories', 'POST', body, { Authorization: this.getAuthHeader(req) });
  }

  @Put('categories/:id')
  @UseGuards(AuthGuard('jwt'))
  updateCategory(@Param('id') id: string, @Body() body: any, @Request() req: any) {
    return this.proxy.forward('blog', `/categories/${id}`, 'PUT', body, { Authorization: this.getAuthHeader(req) });
  }

  @Delete('categories/:id')
  @UseGuards(AuthGuard('jwt'))
  deleteCategory(@Param('id') id: string, @Request() req: any) {
    return this.proxy.forward('blog', `/categories/${id}`, 'DELETE', null, { Authorization: this.getAuthHeader(req) });
  }

  // TAGS
  @Get('tags')
  getTags() { return this.proxy.forward('blog', '/tags', 'GET'); }

  @Post('tags')
  @UseGuards(AuthGuard('jwt'))
  createTag(@Body() body: any, @Request() req: any) {
    return this.proxy.forward('blog', '/tags', 'POST', body, { Authorization: this.getAuthHeader(req) });
  }

  @Post('tags/many')
  @UseGuards(AuthGuard('jwt'))
  createManyTags(@Body() body: any, @Request() req: any) {
    return this.proxy.forward('blog', '/tags/many', 'POST', body, { Authorization: this.getAuthHeader(req) });
  }

  // COMMENTS
  @Get('comments')
  @UseGuards(AuthGuard('jwt'))
  getComments(@Request() req: any) {
    return this.proxy.forward('blog', '/comments', 'GET', null, { Authorization: this.getAuthHeader(req) });
  }

  @Get('comments/post/:postId')
  getPostComments(@Param('postId') postId: string) {
    return this.proxy.forward('blog', `/comments/post/${postId}`, 'GET');
  }

  @Post('comments/post/:postId')
  createComment(@Param('postId') postId: string, @Body() body: any) {
    return this.proxy.forward('blog', `/comments/post/${postId}`, 'POST', body);
  }

  @Put('comments/:id/approve')
  @UseGuards(AuthGuard('jwt'))
  approveComment(@Param('id') id: string, @Request() req: any) {
    return this.proxy.forward('blog', `/comments/${id}/approve`, 'PUT', null, { Authorization: this.getAuthHeader(req) });
  }

  @Delete('comments/:id')
  @UseGuards(AuthGuard('jwt'))
  deleteComment(@Param('id') id: string, @Request() req: any) {
    return this.proxy.forward('blog', `/comments/${id}`, 'DELETE', null, { Authorization: this.getAuthHeader(req) });
  }

  // MEDIA
  @Get('media')
  @UseGuards(AuthGuard('jwt'))
  getMedia(@Request() req: any) {
    return this.proxy.forward('media', '/media', 'GET', null, { Authorization: this.getAuthHeader(req) });
  }

  @Post('media/upload')
  @UseGuards(AuthGuard('jwt'))
  @UseInterceptors(FileInterceptor('file', { storage: memoryStorage() }))
  uploadMedia(@UploadedFile() file: Express.Multer.File, @Body() body: any, @Request() req: any) {
    return this.proxy.forwardWithFile('/media/upload', file, body, this.getAuthHeader(req));
  }

  @Delete('media/:id')
  @UseGuards(AuthGuard('jwt'))
  deleteMedia(@Param('id') id: string, @Request() req: any) {
    return this.proxy.forward('media', `/media/${id}`, 'DELETE', null, { Authorization: this.getAuthHeader(req) });
  }

  // TEXT-TO-SPEECH — one small chunk per request; chunking handled client-side
  @Post('tts')
  async textToSpeech(@Body() body: { text: string }, @Res() res: Response) {
    const text = (body.text || '').trim();
    if (!text) { res.status(400).json({ message: 'text is required' }); return; }

    const hfToken   = process.env.HF_TOKEN;
    const openaiKey = process.env.OPENAI_API_KEY;
    if (!hfToken && !openaiKey) {
      res.status(503).json({ message: 'TTS not configured: set HF_TOKEN or OPENAI_API_KEY' });
      return;
    }

    try {
      let buf: Buffer;
      let contentType: string;

      if (hfToken) {
        // HF Inference API — facebook/mms-tts-eng (fast, lightweight)
        const r = await fetch(
          'https://api-inference.huggingface.co/models/facebook/mms-tts-eng',
          {
            method: 'POST',
            headers: { Authorization: `Bearer ${hfToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ inputs: text }),
          },
        );
        if (!r.ok) { res.status(502).json({ message: `HF TTS error: ${await r.text()}` }); return; }
        contentType = r.headers.get('content-type') || 'audio/flac';
        buf = Buffer.from(await r.arrayBuffer());
      } else {
        // Fallback: OpenAI TTS
        const r = await fetch('https://api.openai.com/v1/audio/speech', {
          method: 'POST',
          headers: { Authorization: `Bearer ${openaiKey}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: 'tts-1', input: text.slice(0, 4096), voice: 'alloy' }),
        });
        if (!r.ok) { res.status(502).json({ message: `OpenAI error: ${await r.text()}` }); return; }
        contentType = 'audio/mpeg';
        buf = Buffer.from(await r.arrayBuffer());
      }

      res.set({ 'Content-Type': contentType, 'Content-Length': String(buf.length) });
      res.send(buf);
    } catch (e) {
      res.status(500).json({ message: 'TTS failed' });
    }
  }
}
