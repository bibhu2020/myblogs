import OpenAI from 'openai';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { createHmac } from 'crypto';

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

function makeAgentJWT() {
  const secret = process.env.JWT_SECRET || 'myblogs-secret-key-2024';
  const now = Math.floor(Date.now() / 1000);
  // sub is required: JwtStrategy reads payload.sub for authorId
  const payload = {
    sub: 0, id: 0,
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

// ── Image generation: DALL-E 3 → DALL-E 2 → Gemini Imagen ───────────────────
// Returns { buffer: Buffer, mimeType: string } or null

async function tryDalle3(prompt, size) {
  const VALID_SIZES = new Set(['1024x1024', '1792x1024', '1024x1792']);
  const resp = await openai.images.generate({
    model: 'dall-e-3',
    prompt: prompt.slice(0, 900),
    size: VALID_SIZES.has(size) ? size : '1024x1024',
    quality: 'hd',
    n: 1,
  });
  const url = resp.data[0].url;
  const imgRes = await fetch(url, { signal: AbortSignal.timeout(60_000) });
  if (!imgRes.ok) throw new Error(`Download failed: ${imgRes.status}`);
  return { buffer: Buffer.from(await imgRes.arrayBuffer()), mimeType: 'image/png' };
}

async function tryDalle2(prompt) {
  const resp = await openai.images.generate({
    model: 'dall-e-2',
    prompt: prompt.slice(0, 1000),
    size: '1024x1024',
    n: 1,
  });
  const url = resp.data[0].url;
  const imgRes = await fetch(url, { signal: AbortSignal.timeout(60_000) });
  if (!imgRes.ok) throw new Error(`Download failed: ${imgRes.status}`);
  return { buffer: Buffer.from(await imgRes.arrayBuffer()), mimeType: 'image/png' };
}

async function tryGemini(prompt) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) throw new Error('GEMINI_API_KEY not set');

  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({
    model: 'gemini-2.0-flash-preview-image-generation',
  });

  const response = await model.generateContent({
    contents: [{ role: 'user', parts: [{ text: prompt.slice(0, 1000) }] }],
    generationConfig: { responseModalities: ['image', 'text'] },
  });

  const parts = response.response.candidates?.[0]?.content?.parts ?? [];
  const imgPart = parts.find((p) => p.inlineData?.mimeType?.startsWith('image/'));
  if (!imgPart) throw new Error('Gemini returned no image data');

  return {
    buffer: Buffer.from(imgPart.inlineData.data, 'base64'),
    mimeType: imgPart.inlineData.mimeType,
  };
}

async function generateImage(prompt, size = '1024x1024') {
  const safePrompt = `${prompt}. Professional, high-quality illustration, no text overlays, no watermarks.`;

  // 1. DALL-E 3 (requires OpenAI Tier 1 — $5 cumulative spend)
  try {
    const result = await tryDalle3(safePrompt, size);
    console.log('  ✓ DALL-E 3');
    return result;
  } catch (err) {
    const isDalleMissing = err.message?.includes('does not exist') || err.message?.includes('model');
    if (!isDalleMissing) console.warn(`  ⚠️  DALL-E 3 error: ${err.message}`);
    else console.warn('  ⚠️  DALL-E 3 unavailable (Tier 1 required), trying DALL-E 2...');
  }

  // 2. DALL-E 2 (available on all paid tiers)
  try {
    const result = await tryDalle2(safePrompt);
    console.log('  ✓ DALL-E 2');
    return result;
  } catch (err) {
    console.warn(`  ⚠️  DALL-E 2 failed (${err.message}), trying Gemini...`);
  }

  // 3. Gemini Imagen (requires GEMINI_API_KEY)
  try {
    const result = await tryGemini(safePrompt);
    console.log('  ✓ Gemini');
    return result;
  } catch (err) {
    console.warn(`  ⚠️  Gemini failed (${err.message})`);
  }

  return null;
}

async function uploadToMediaService({ buffer, mimeType }, altText, serverBase) {
  const jwt = makeAgentJWT();
  const ext = mimeType.includes('jpeg') ? 'jpg' : mimeType.includes('webp') ? 'webp' : 'png';

  const form = new FormData();
  form.append('file', new Blob([buffer], { type: mimeType }), `ai-${Date.now()}.${ext}`);
  form.append('alt', altText.slice(0, 200));

  const res = await fetch(`${serverBase}/api/media/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${jwt}` },
    body: form,
    signal: AbortSignal.timeout(120_000),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Media upload failed (${res.status}): ${text.slice(0, 300)}`);
  }

  const data = await res.json();
  if (!data.url) throw new Error(`Upload response missing url: ${JSON.stringify(data)}`);
  return data.url;
}

export async function generateFeaturedImage(prompt, serverBase) {
  console.log('🎨 Generating featured image (1792×1024)...');
  const result = await generateImage(prompt, '1792x1024');
  if (!result) {
    console.warn('  ⚠️  No image model available — post will publish without a featured image');
    return null;
  }
  const url = await uploadToMediaService(result, prompt.slice(0, 120), serverBase);
  console.log(`  ✅ ${url}`);
  return url;
}

export async function processInlineImages(content, serverBase) {
  const regex = /\[\[IMAGE:\s*([\s\S]*?)\]\]/g;
  const matches = [...content.matchAll(regex)];
  if (matches.length === 0) return content;

  console.log(`🖼️  Processing ${matches.length} inline image(s)...`);
  let processed = content;

  for (const match of matches) {
    const [fullMatch, prompt] = match;
    const alt = prompt.trim().replace(/\s+/g, ' ').slice(0, 120);

    try {
      console.log(`  → "${alt.slice(0, 65)}"`);
      const result = await generateImage(prompt.trim(), '1024x1024');
      if (!result) {
        console.warn('  ⚠️  All image models failed — removing placeholder');
        processed = processed.replace(fullMatch, '');
        continue;
      }
      const url = await uploadToMediaService(result, alt, serverBase);

      const tag =
        `<figure class="my-8 text-center">` +
        `<img src="${url}" alt="${escapeAttr(alt)}" class="w-full rounded-xl shadow-lg mx-auto" />` +
        `<figcaption class="mt-3 text-sm text-gray-500 italic">${escapeHtml(alt)}</figcaption>` +
        `</figure>`;

      processed = processed.replace(fullMatch, tag);
      console.log(`  ✅ ${url}`);
    } catch (err) {
      console.error(`  ❌ Image upload failed: ${err.message}`);
      processed = processed.replace(fullMatch, '');
    }

    // Throttle between images to respect API rate limits
    await new Promise((r) => setTimeout(r, 2000));
  }

  return processed;
}

function escapeAttr(s) {
  return s.replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
