// The installed `uuid` package ships an ESM-only build that this project's Jest transform
// isn't configured to parse — mock it so this pure-logic unit test doesn't need to import
// the real thing (nothing here depends on uuidv4()'s actual output, only its shape).
jest.mock('uuid', () => ({ v4: () => 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' }));

import { buildFilename } from './app.module';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.mp3$/i;

function req(query: Record<string, any> = {}) {
  return { query } as any;
}

const mp3File = { originalname: 'narration.mp3' } as Express.Multer.File;
const jpgFile = { originalname: 'photo.jpg' } as Express.Multer.File;

describe('buildFilename', () => {
  it('uses the requested filename with the real extension when provided and safe', () => {
    expect(buildFilename(req({ filename: 'post_123' }), mp3File)).toBe('post_123.mp3');
  });

  it('ignores any extension the caller supplies and always uses the real one', () => {
    expect(buildFilename(req({ filename: 'post_123.exe' }), mp3File)).toBe('post_123.mp3');
  });

  it('re-appends the real extension for image uploads too', () => {
    expect(buildFilename(req({ filename: 'story_9' }), jpgFile)).toBe('story_9.jpg');
  });

  it('falls back to a random UUID when no filename query param is given', () => {
    expect(buildFilename(req(), mp3File)).toMatch(UUID_RE);
  });

  it('falls back to a random UUID when the filename query param is blank', () => {
    expect(buildFilename(req({ filename: '   ' }), mp3File)).toMatch(UUID_RE);
  });

  it('falls back to a random UUID when the filename contains a path separator', () => {
    expect(buildFilename(req({ filename: '../../etc/passwd' }), mp3File)).toMatch(UUID_RE);
  });

  it('falls back to a random UUID when the filename contains unsafe characters', () => {
    expect(buildFilename(req({ filename: 'post 123!' }), mp3File)).toMatch(UUID_RE);
  });

  it('produces different names for different content ids', () => {
    expect(buildFilename(req({ filename: 'post_1' }), mp3File)).toBe('post_1.mp3');
    expect(buildFilename(req({ filename: 'post_2' }), mp3File)).toBe('post_2.mp3');
  });
});
