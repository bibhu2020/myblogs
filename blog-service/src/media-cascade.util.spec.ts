import { extractMediaFilename, extractAllMediaFilenames } from './media-cascade.util';

describe('extractMediaFilename', () => {
  it('returns null for a missing url', () => {
    expect(extractMediaFilename(null)).toBeNull();
    expect(extractMediaFilename(undefined)).toBeNull();
    expect(extractMediaFilename('')).toBeNull();
  });

  it('returns null for an external url with no uploads/audio segment', () => {
    expect(extractMediaFilename('https://unsplash.com/photo.jpg')).toBeNull();
  });

  it('extracts the filename from a local /uploads/ path', () => {
    expect(extractMediaFilename('/uploads/abc123.jpg')).toBe('abc123.jpg');
  });

  it('extracts the filename from a GitHub raw uploads path', () => {
    expect(
      extractMediaFilename('https://raw.githubusercontent.com/bibhu2020/media/main/myblogs/uploads/abc123.jpg'),
    ).toBe('abc123.jpg');
  });

  it('extracts the filename from a GitHub raw audio path', () => {
    expect(
      extractMediaFilename('https://raw.githubusercontent.com/bibhu2020/media/main/myblogs/audio/post_1.mp3'),
    ).toBe('post_1.mp3');
  });

  it('ignores a query string when extracting the filename', () => {
    expect(extractMediaFilename('/uploads/abc123.jpg?w=200')).toBe('abc123.jpg');
  });
});

describe('extractAllMediaFilenames', () => {
  it('returns an empty list for a bare item', () => {
    expect(extractAllMediaFilenames({})).toEqual([]);
  });

  it('collects the hero image, audio, and inline content images', () => {
    const result = extractAllMediaFilenames({
      featuredImage: '/uploads/hero.jpg',
      audioUrl: '/uploads/post_1.mp3',
      content: '<p>text</p><img src="/uploads/inline1.jpg"><img src="/uploads/inline2.jpg">',
    });
    expect(result).toEqual(['hero.jpg', 'post_1.mp3', 'inline1.jpg', 'inline2.jpg']);
  });

  it('ignores an external hero image url', () => {
    const result = extractAllMediaFilenames({ featuredImage: 'https://unsplash.com/photo.jpg' });
    expect(result).toEqual([]);
  });

  it('de-duplicates repeated filenames', () => {
    const result = extractAllMediaFilenames({
      featuredImage: '/uploads/hero.jpg',
      content: '<img src="/uploads/hero.jpg">',
    });
    expect(result).toEqual(['hero.jpg']);
  });
});
