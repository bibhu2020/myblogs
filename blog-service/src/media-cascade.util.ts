import { JwtService } from '@nestjs/jwt';

const MEDIA_SERVICE_URL = process.env.MEDIA_SERVICE_URL || 'http://localhost:3003';

/** Extract the bare filename from a hero-image / audioUrl field, or null if the URL
 * isn't one of our own hosted media files (e.g. a direct external Unsplash URL, which
 * featuredImage may legitimately hold). TypeScript port of
 * meridian_agents/cleanup.py's _uploads_filename — keep both in sync. */
export function extractMediaFilename(url?: string | null): string | null {
  if (!url) return null;
  const m = /\/(?:uploads|audio)\/([^/?#]+)/.exec(url);
  return m ? m[1] : null;
}

/** Every media filename a post/story references — its hero image, its pre-rendered
 * narration mp3 (if any), plus every inline image embedded in HTML body content — so a
 * deleted item never leaves orphaned files behind in the media library. TypeScript port
 * of meridian_agents/cleanup.py's _all_upload_filenames — keep both in sync. */
export function extractAllMediaFilenames(item: {
  featuredImage?: string | null;
  audioUrl?: string | null;
  content?: string | null;
}): string[] {
  const filenames: string[] = [];
  const hero = extractMediaFilename(item.featuredImage);
  if (hero) filenames.push(hero);
  const audio = extractMediaFilename(item.audioUrl);
  if (audio) filenames.push(audio);

  const content = item.content || '';
  const re = /\/(?:uploads|audio)\/([^"'?#\s]+)/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(content)) !== null) {
    filenames.push(match[1]);
  }
  return [...new Set(filenames)];
}

/** Self-signs a short-lived internal-service JWT — same shared secret and payload shape
 * as api-gateway/src/mcp.controller.ts's agentAuth() (sub=0 required: every service's
 * JwtStrategy reads payload.sub for the user id). */
function internalAuth(jwt: JwtService): string {
  const token = jwt.sign(
    { sub: 0, id: 0, email: 'blog-service@meridian.internal', name: 'Blog Service', role: 'admin' },
    { expiresIn: '5m' },
  );
  return `Bearer ${token}`;
}

/** Best-effort cascade-delete of every media file a post/story references (hero image,
 * narration mp3, inline content images) — called when the content itself is deleted, so
 * the media library never accumulates orphans. Never throws: a media-service outage must
 * never block the content deletion it's attached to. */
export async function deleteAssociatedMedia(
  jwt: JwtService,
  item: { featuredImage?: string | null; audioUrl?: string | null; content?: string | null },
  logger: { warn: (msg: string) => void },
): Promise<void> {
  const filenames = extractAllMediaFilenames(item);
  if (!filenames.length) return;

  const auth = internalAuth(jwt);
  await Promise.all(
    filenames.map(async (filename) => {
      try {
        const res = await fetch(`${MEDIA_SERVICE_URL}/api/media/by-filename/${encodeURIComponent(filename)}`, {
          method: 'DELETE',
          headers: { Authorization: auth },
        });
        if (!res.ok) {
          logger.warn(`media cascade-delete failed for ${filename}: ${res.status}`);
        }
      } catch (err: any) {
        logger.warn(`media cascade-delete error for ${filename}: ${err.message}`);
      }
    }),
  );
}
