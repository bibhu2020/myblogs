import {
  Controller, All, Req, Res, Next, Get, Post, Put, Patch, Delete, Param, Body, Query,
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

  @Patch('posts/:id/approve')
  @UseGuards(AuthGuard('jwt'))
  approvePost(@Param('id') id: string, @Request() req: any) {
    return this.proxy.forward('blog', `/posts/${id}/approve`, 'PATCH', null, { Authorization: this.getAuthHeader(req) });
  }

  @Patch('posts/:id/reject')
  @UseGuards(AuthGuard('jwt'))
  rejectPost(@Param('id') id: string, @Request() req: any) {
    return this.proxy.forward('blog', `/posts/${id}/reject`, 'PATCH', null, { Authorization: this.getAuthHeader(req) });
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

  // STORY ROUTES - Public
  @Get('stories')
  getStories(@Query() query: any) {
    const params = new URLSearchParams(query).toString();
    return this.proxy.forward('blog', `/stories?${params}`, 'GET');
  }

  @Get('stories/recent')
  getRecentStories() { return this.proxy.forward('blog', '/stories/recent', 'GET'); }

  @Get('stories/stats')
  @UseGuards(AuthGuard('jwt'))
  getStoryStats(@Request() req: any) {
    return this.proxy.forward('blog', '/stories/stats', 'GET', null, { Authorization: this.getAuthHeader(req) });
  }

  @Get('stories/admin')
  @UseGuards(AuthGuard('jwt'))
  getAdminStories(@Query() query: any, @Request() req: any) {
    const params = new URLSearchParams({ ...query, status: query.status || '' }).toString();
    return this.proxy.forward('blog', `/stories/admin?${params}`, 'GET', null, { Authorization: this.getAuthHeader(req) });
  }

  @Get('stories/:slug')
  getStory(@Param('slug') slug: string) {
    return this.proxy.forward('blog', `/stories/${slug}`, 'GET');
  }

  @Post('stories')
  @UseGuards(AuthGuard('jwt'))
  createStory(@Body() body: any, @Request() req: any) {
    return this.proxy.forward('blog', '/stories', 'POST', body, { Authorization: this.getAuthHeader(req) });
  }

  @Patch('stories/:id/approve')
  @UseGuards(AuthGuard('jwt'))
  approveStory(@Param('id') id: string, @Request() req: any) {
    return this.proxy.forward('blog', `/stories/${id}/approve`, 'PATCH', null, { Authorization: this.getAuthHeader(req) });
  }

  @Patch('stories/:id/reject')
  @UseGuards(AuthGuard('jwt'))
  rejectStory(@Param('id') id: string, @Request() req: any) {
    return this.proxy.forward('blog', `/stories/${id}/reject`, 'PATCH', null, { Authorization: this.getAuthHeader(req) });
  }

  @Put('stories/:id')
  @UseGuards(AuthGuard('jwt'))
  updateStory(@Param('id') id: string, @Body() body: any, @Request() req: any) {
    return this.proxy.forward('blog', `/stories/${id}`, 'PUT', body, { Authorization: this.getAuthHeader(req) });
  }

  @Delete('stories/:id')
  @UseGuards(AuthGuard('jwt'))
  deleteStory(@Param('id') id: string, @Request() req: any) {
    return this.proxy.forward('blog', `/stories/${id}`, 'DELETE', null, { Authorization: this.getAuthHeader(req) });
  }

  // NEWS ROUTES
  @Get('news')
  getNews(@Query() query: any) {
    const params = new URLSearchParams(query).toString();
    return this.proxy.forward('blog', `/news?${params}`, 'GET');
  }

  @Post('news/refresh')
  @UseGuards(AuthGuard('jwt'))
  refreshNews(@Body() body: any, @Request() req: any) {
    return this.proxy.forward('blog', '/news/refresh', 'POST', body, { Authorization: this.getAuthHeader(req) });
  }

  // PUSH NOTIFICATION ROUTES
  @Get('push/vapid-key')
  getPushVapidKey() {
    return this.proxy.forward('blog', '/push/vapid-key', 'GET');
  }

  @Post('push/subscribe')
  subscribePush(@Body() body: any) {
    return this.proxy.forward('blog', '/push/subscribe', 'POST', body);
  }

  @Delete('push/unsubscribe')
  unsubscribePush(@Body() body: any) {
    return this.proxy.forward('blog', '/push/unsubscribe', 'DELETE', body);
  }

  // AGENT RUNS
  @Post('agent-runs/dispatch')
  @UseGuards(AuthGuard('jwt'))
  dispatchAgent(@Body() body: any, @Request() req: any) {
    return this.proxy.forward('blog', '/agent-runs/dispatch', 'POST', body, { Authorization: this.getAuthHeader(req) });
  }

  @Post('agent-runs')
  createAgentRun(@Body() body: any) {
    return this.proxy.forward('blog', '/agent-runs', 'POST', body);
  }

  @Put('agent-runs/:runId')
  updateAgentRun(@Param('runId') runId: string, @Body() body: any) {
    return this.proxy.forward('blog', `/agent-runs/${runId}`, 'PUT', body);
  }

  @Get('agent-runs')
  @UseGuards(AuthGuard('jwt'))
  getAgentRuns(@Request() req: any) {
    return this.proxy.forward('blog', '/agent-runs', 'GET', null, { Authorization: this.getAuthHeader(req) });
  }

  @Get('agent-runs/:runId')
  @UseGuards(AuthGuard('jwt'))
  getAgentRun(@Param('runId') runId: string, @Request() req: any) {
    return this.proxy.forward('blog', `/agent-runs/${runId}`, 'GET', null, { Authorization: this.getAuthHeader(req) });
  }

  // TEXT-TO-SPEECH — one chunk per request; style selects the voice/pace.
  // Primary: Kokoro-82M local Python service (story/blog/news voices).
  // Fallback: HuggingFace Inference API (facebook/mms-tts-eng, no style support).
  @Post('tts')
  async textToSpeech(@Body() body: { text: string; style?: string }, @Res() res: Response) {
    const text  = (body.text  || '').trim();
    const style = (body.style || '').trim();
    if (!text) { res.status(400).json({ message: 'text is required' }); return; }

    const localTts = process.env.TTS_SERVICE_URL;
    const hfToken  = process.env.HF_TOKEN;

    if (!localTts && !hfToken) {
      res.status(503).json({ message: 'TTS not configured: set TTS_SERVICE_URL or HF_TOKEN' });
      return;
    }

    const errors: string[] = [];

    // ── Primary: Kokoro-82M local service ───────────────────────────────────
    if (localTts) {
      try {
        const r = await fetch(`${localTts}/tts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, style }),
          signal: AbortSignal.timeout(120_000),
        });
        if (!r.ok) throw new Error(`Kokoro: ${r.status}`);
        const buf = Buffer.from(await r.arrayBuffer());
        res.set({ 'Content-Type': 'audio/wav', 'Content-Length': String(buf.length) });
        return res.send(buf);
      } catch (e) {
        errors.push((e as Error).message);
      }
    }

    // ── Fallback: HF Inference API (facebook/mms-tts-eng) ───────────────────
    // Retries once if HF returns 503 "model loading" (estimated_time in body).
    if (hfToken) {
      const hfCall = async () => {
        const r = await fetch(
          'https://api-inference.huggingface.co/models/facebook/mms-tts-eng',
          {
            method: 'POST',
            headers: { Authorization: `Bearer ${hfToken}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ inputs: text }),
            signal: AbortSignal.timeout(90_000),
          },
        );
        if (r.status === 503) {
          // Model is loading — read estimated_time and retry once
          const body = await r.json().catch(() => ({})) as { estimated_time?: number };
          const wait = Math.min((body.estimated_time ?? 20) * 1000, 30_000);
          await new Promise(resolve => setTimeout(resolve, wait));
          const r2 = await fetch(
            'https://api-inference.huggingface.co/models/facebook/mms-tts-eng',
            {
              method: 'POST',
              headers: { Authorization: `Bearer ${hfToken}`, 'Content-Type': 'application/json' },
              body: JSON.stringify({ inputs: text }),
              signal: AbortSignal.timeout(90_000),
            },
          );
          if (!r2.ok) throw new Error(`HF TTS: ${r2.status}`);
          return r2;
        }
        if (!r.ok) throw new Error(`HF TTS: ${r.status}`);
        return r;
      };
      try {
        const r = await hfCall();
        const buf = Buffer.from(await r.arrayBuffer());
        const ct = r.headers.get('content-type') || 'audio/flac';
        res.set({ 'Content-Type': ct, 'Content-Length': String(buf.length) });
        return res.send(buf);
      } catch (e) {
        errors.push((e as Error).message);
      }
    }

    res.status(503).json({ message: `TTS unavailable: ${errors.join(' | ')}` });
  }
}

