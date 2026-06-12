import OpenAI from 'openai';
import { createHmac } from 'crypto';

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

function makeAgentJWT() {
  const secret = process.env.JWT_SECRET || 'myblogs-secret-key-2024';
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    id: 0,
    email: 'ai-agent@meridian.internal',
    name: 'AI Agent',
    role: 'admin',
    iat: now,
    exp: now + 3600,
  };
  const b64url = (obj) => Buffer.from(JSON.stringify(obj)).toString('base64url');
  const header = b64url({ alg: 'HS256', typ: 'JWT' });
  const body = b64url(payload);
  const sig = createHmac('sha256', secret).update(`${header}.${body}`).digest('base64url');
  return `${header}.${body}.${sig}`;
}

async function generateDalleImage(prompt, size = '1792x1024') {
  const response = await openai.images.generate({
    model: 'dall-e-3',
    prompt: `${prompt.slice(0, 900)}. Professional, high-quality, no text overlays, no watermarks.`,
    size,
    quality: 'hd',
    n: 1,
  });
  return response.data[0].url;
}

async function uploadToMediaService(dalleUrl, altText, serverBase) {
  const jwt = makeAgentJWT();

  // Download the DALL-E temporary image
  const imgRes = await fetch(dalleUrl, { signal: AbortSignal.timeout(60_000) });
  if (!imgRes.ok) throw new Error(`Failed to download DALL-E image: ${imgRes.status}`);
  const imgBuffer = await imgRes.arrayBuffer();

  // POST multipart to media service — Node 18+ FormData/fetch built-in
  const form = new FormData();
  form.append(
    'file',
    new Blob([imgBuffer], { type: 'image/png' }),
    `ai-${Date.now()}.png`,
  );
  form.append('alt', altText.slice(0, 200));

  const uploadRes = await fetch(`${serverBase}/api/media/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${jwt}` },
    body: form,
    signal: AbortSignal.timeout(120_000),
  });

  if (!uploadRes.ok) {
    const text = await uploadRes.text();
    throw new Error(`Media upload failed (${uploadRes.status}): ${text.slice(0, 300)}`);
  }

  const data = await uploadRes.json();
  if (!data.url) throw new Error(`Upload response missing url field: ${JSON.stringify(data)}`);
  return data.url;
}

export async function generateFeaturedImage(prompt, serverBase) {
  console.log('🎨 Generating featured image (1792×1024)...');
  const dalleUrl = await generateDalleImage(prompt, '1792x1024');
  const url = await uploadToMediaService(dalleUrl, prompt.slice(0, 120), serverBase);
  console.log(`✅ Featured image: ${url}`);
  return url;
}

export async function processInlineImages(content, serverBase) {
  // Match [[IMAGE: prompt]] — lazily, handles multi-word prompts
  const regex = /\[\[IMAGE:\s*([\s\S]*?)\]\]/g;
  const matches = [...content.matchAll(regex)];

  if (matches.length === 0) return content;
  console.log(`🖼️  Processing ${matches.length} inline image placeholder(s)...`);

  let processed = content;

  for (const match of matches) {
    const [fullMatch, prompt] = match;
    const alt = prompt.trim().replace(/\s+/g, ' ').slice(0, 120);

    try {
      console.log(`  → "${alt.slice(0, 60)}..."`);
      const dalleUrl = await generateDalleImage(prompt.trim(), '1024x1024');
      const url = await uploadToMediaService(dalleUrl, alt, serverBase);

      const tag =
        `<figure class="my-8 text-center">` +
        `<img src="${url}" alt="${escapeAttr(alt)}" class="w-full rounded-xl shadow-lg mx-auto" />` +
        `<figcaption class="mt-3 text-sm text-gray-500 italic">${escapeHtml(alt)}</figcaption>` +
        `</figure>`;

      processed = processed.replace(fullMatch, tag);
      console.log(`  ✅ ${url}`);
    } catch (err) {
      console.error(`  ❌ Image failed: ${err.message}`);
      // Remove placeholder so post still publishes cleanly
      processed = processed.replace(fullMatch, '');
    }

    // Throttle: DALL-E HD has a 5 img/min rate limit on Tier 1
    await new Promise((r) => setTimeout(r, 3000));
  }

  return processed;
}

function escapeAttr(s) {
  return s.replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
