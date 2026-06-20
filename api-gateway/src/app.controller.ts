import {
  Controller, All, Req, Res, Next, Get, Post, Put, Patch, Delete, Param, Body, Query,
  UseGuards, Request, UseInterceptors, UploadedFile, Headers, HttpCode
} from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { FileInterceptor } from '@nestjs/platform-express';
import { memoryStorage } from 'multer';
import { ProxyService } from './proxy.service';
import { Request as ExpressRequest, Response } from 'express';

// Detect actual audio format from magic bytes and return the correct MIME type.
function detectAudioMime(buf: Buffer): string {
  if (buf.length >= 4 && buf[0] === 0x52 && buf[1] === 0x49 && buf[2] === 0x46 && buf[3] === 0x46)
    return 'audio/wav';  // RIFF header
  if (buf.length >= 3 && buf[0] === 0x49 && buf[1] === 0x44 && buf[2] === 0x33)
    return 'audio/mpeg'; // ID3 tag (MP3)
  if (buf.length >= 2 && buf[0] === 0xFF && (buf[1] & 0xE0) === 0xE0)
    return 'audio/mpeg'; // MP3 sync word
  if (buf.length >= 4 && buf[0] === 0x4F && buf[1] === 0x67 && buf[2] === 0x67 && buf[3] === 0x53)
    return 'audio/ogg';  // OGG
  return 'audio/mpeg';
}

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

  // TEXT-TO-SPEECH — Microsoft Edge TTS, voice and pace vary by content type.
  @Post('tts')
  async textToSpeech(@Body() body: { text: string; type?: string }, @Res() res: Response) {
    const text = (body.text || '').trim();
    if (!text) { res.status(400).json({ message: 'text is required' }); return; }

    // story → Irish accent (Emily) is naturally musical and warm — classic captivating storyteller
    //         very slow rate + slightly lower pitch for dramatic, immersive feel
    // blog  → Jenny has a clear teacher-like delivery with natural enunciation — good for explaining
    // news  → Aria at brisk news-presenter pace (unchanged)
    const PROFILES: Record<string, { voice: string; rate: number; pitch: string }> = {
      story: { voice: 'en-IE-EmilyNeural', rate: 0.72, pitch: '-1st' },
      blog:  { voice: 'en-US-JennyNeural', rate: 0.82, pitch: '+0Hz' },
      news:  { voice: 'en-US-AriaNeural',  rate: 0.95, pitch: '+0Hz' },
    };
    const profile = PROFILES[body.type || ''] ?? PROFILES.blog;

    try {
      const { MsEdgeTTS, OUTPUT_FORMAT } = await import('msedge-tts');
      const tts = new MsEdgeTTS();
      await tts.setMetadata(profile.voice, OUTPUT_FORMAT.AUDIO_24KHZ_96KBITRATE_MONO_MP3);
      const { audioStream } = tts.toStream(text, { rate: profile.rate, pitch: profile.pitch });
      const buf = await new Promise<Buffer>((resolve, reject) => {
        const chunks: Buffer[] = [];
        let settled = false;
        const finish = (err?: Error) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          err ? reject(err) : resolve(Buffer.concat(chunks));
        };
        const timer = setTimeout(() => finish(new Error('stream timeout')), 30_000);
        audioStream.on('data', (chunk: Buffer) => chunks.push(chunk));
        audioStream.on('end', () => finish());
        audioStream.on('error', (e) => finish(e));
        // 'close' fires on socket teardown — use as fallback only if 'end' never fires
        audioStream.on('close', () => setTimeout(() => {
          finish(chunks.length ? undefined : new Error('stream closed with no data'));
        }, 100));
      });
      if (!buf.length) throw new Error('empty audio response');
      const mime = detectAudioMime(buf);
      res.set({ 'Content-Type': mime, 'Content-Length': String(buf.length) });
      res.send(buf);
    } catch (e) {
      res.status(500).json({ message: `TTS failed: ${(e as Error).message}` });
    }
  }

  // MUSIC — Lyrics via Gemini (reachable), voice via msedge-tts.
  // HF api-inference.huggingface.co is unreachable from this server's network.
  @Post('music/lyrics')
  async generateLyrics(@Body() body: { language: string; genre: string; era: string; theme?: string }, @Res() res: Response) {
    const language = (body.language || 'english').toLowerCase();
    const genre    = (body.genre    || 'melody').toLowerCase();
    const era      = (body.era      || 'contemporary').toLowerCase();
    const theme    = (body.theme    || '').trim();

    const langInstr: Record<string, string> = {
      english: 'Write entirely in English.',
      hindi:   'Write entirely in Hindi using Devanagari script.',
      odia:    'Write entirely in Odia using Odia script.',
    };
    const genreStyle: Record<string, string> = {
      bollywood: 'Bollywood film song — emotional, melodious, poetic imagery, romantic or dramatic themes',
      melody:    'melodic pop — catchy, heartfelt, memorable hook and repeating chorus',
      country:   'country music — storytelling, heartfelt, themes of love, home, and the open road',
      jazz:      'jazz standard — sophisticated, bluesy, smooth phrasing, atmospheric night-club imagery',
    };
    const eraStyle: Record<string, string> = {
      '1970s':      '1970s — orchestral arrangements, classic romance, idealistic and hopeful',
      '1980s':      '1980s — synth-driven energy, big emotions, passionate and anthemic',
      '1990s':      '1990s — introspective, emotional depth, acoustic warmth mixed with electric grit',
      contemporary: 'contemporary — modern production sensibility, conversational, relatable everyday themes',
    };

    const prompt = `You are a world-class lyricist. Write original, evocative song lyrics with these specifications:

Language: ${langInstr[language] ?? langInstr.english}
Style: ${genreStyle[genre] ?? genreStyle.melody}
Era: ${eraStyle[era] ?? eraStyle.contemporary}
${theme ? `Theme / concept: ${theme}` : ''}

Format your response exactly like this:
Title: [Compelling Song Title]

[Verse 1]
(4-6 lines)

[Chorus]
(4-6 lines — the emotional peak)

[Verse 2]
(4-6 lines)

[Chorus]
(repeat chorus)

[Bridge]
(2-4 lines — shift in perspective or intensity)

[Chorus]
(final chorus)

Write only the lyrics. No explanations, no commentary, no extra text.`;

    try {
      const geminiKey = process.env.GEMINI_API_KEY || '';
      if (!geminiKey) throw new Error('GEMINI_API_KEY not configured');

      const resp = await (await import('axios')).default.post(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${geminiKey}`,
        { contents: [{ parts: [{ text: prompt }] }] },
        { timeout: 30_000 }
      );
      const lyrics = resp.data?.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? '';
      if (!lyrics) throw new Error('Empty response from Gemini');
      res.json({ lyrics });
    } catch (e: any) {
      res.status(500).json({ message: `Lyrics generation failed: ${e?.response?.data?.error?.message || e.message}` });
    }
  }

  @Post('music/tts')
  async musicTts(@Body() body: { text: string; language: string }, @Res() res: Response) {
    const text     = (body.text     || '').trim();
    const language = (body.language || 'english').toLowerCase();
    if (!text) { res.status(400).json({ message: 'text is required' }); return; }

    // Edge TTS voices per language (Odia not in Edge TTS → Indian-English fallback)
    const VOICES: Record<string, { voice: string; rate: number; pitch: string }> = {
      english: { voice: 'en-US-JennyNeural',   rate: 0.88, pitch: '+0Hz' },
      hindi:   { voice: 'hi-IN-SwaraNeural',    rate: 0.88, pitch: '+0Hz' },
      odia:    { voice: 'en-IN-NeerjaNeural',   rate: 0.88, pitch: '+0Hz' },
    };
    const profile = VOICES[language] ?? VOICES.english;

    try {
      const { MsEdgeTTS, OUTPUT_FORMAT } = await import('msedge-tts');
      const tts = new MsEdgeTTS();
      await tts.setMetadata(profile.voice, OUTPUT_FORMAT.AUDIO_24KHZ_96KBITRATE_MONO_MP3);
      const { audioStream } = tts.toStream(text, { rate: profile.rate, pitch: profile.pitch });
      const buf = await new Promise<Buffer>((resolve, reject) => {
        const chunks: Buffer[] = [];
        let settled = false;
        const finish = (err?: Error) => {
          if (settled) return; settled = true; clearTimeout(timer);
          err ? reject(err) : resolve(Buffer.concat(chunks));
        };
        const timer = setTimeout(() => finish(new Error('stream timeout')), 30_000);
        audioStream.on('data', (c: Buffer) => chunks.push(c));
        audioStream.on('end', () => finish());
        audioStream.on('error', (e: Error) => finish(e));
        audioStream.on('close', () => setTimeout(() => finish(chunks.length ? undefined : new Error('closed with no data')), 100));
      });
      if (!buf.length) throw new Error('empty audio response');
      const mime = detectAudioMime(buf);
      res.set({ 'Content-Type': mime, 'Content-Length': String(buf.length) });
      res.send(buf);
    } catch (e: any) {
      res.status(500).json({ message: `Music TTS failed: ${(e as Error).message}` });
    }
  }
}
