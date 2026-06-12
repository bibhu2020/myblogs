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

// ── Image generation: DALL-E 3 → DALL-E 2 → FLUX.1-schnell → Gemini → Unsplash
// All try* functions return { buffer: Buffer, mimeType: string }

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

async function tryFlux(prompt) {
  const token = process.env.HF_TOKEN;
  if (!token) throw new Error('HF_TOKEN not set');

  const call = async () =>
    fetch('https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ inputs: prompt.slice(0, 500) }),
      signal: AbortSignal.timeout(120_000),
    });

  let res = await call();

  // Model cold-start: HF returns 503 with estimated_time — wait and retry once
  if (res.status === 503) {
    const json = await res.json().catch(() => ({}));
    const wait = Math.min((json.estimated_time ?? 20) * 1000, 30_000);
    console.log(`  ⏳ FLUX model loading, retrying in ${Math.round(wait / 1000)}s...`);
    await new Promise((r) => setTimeout(r, wait));
    res = await call();
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HF API ${res.status}: ${text.slice(0, 200)}`);
  }

  const mimeType = (res.headers.get('content-type') || 'image/jpeg').split(';')[0];
  if (!mimeType.startsWith('image/')) throw new Error(`HF returned non-image: ${mimeType}`);

  return { buffer: Buffer.from(await res.arrayBuffer()), mimeType };
}

async function tryGemini(prompt) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) throw new Error('GEMINI_API_KEY not set');

  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash-preview-image-generation' });

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

async function tryUnsplash(topic) {
  const key = process.env.UNSPLASH_ACCESS_KEY;
  if (!key) throw new Error('UNSPLASH_ACCESS_KEY not set');

  // Keep only the first 5 meaningful words for the search query
  const query = topic.replace(/[^\w\s]/g, ' ').split(/\s+/).slice(0, 5).join(' ');

  const searchRes = await fetch(
    `https://api.unsplash.com/photos/random?query=${encodeURIComponent(query)}&orientation=landscape&content_filter=high`,
    {
      headers: { Authorization: `Client-ID ${key}` },
      signal: AbortSignal.timeout(30_000),
    },
  );
  if (!searchRes.ok) throw new Error(`Unsplash ${searchRes.status}: ${await searchRes.text().then(t => t.slice(0, 150))}`);

  const data = await searchRes.json();
  const imgUrl = data.urls?.regular;
  if (!imgUrl) throw new Error('Unsplash returned no image URL');

  const imgRes = await fetch(imgUrl, { signal: AbortSignal.timeout(60_000) });
  if (!imgRes.ok) throw new Error(`Unsplash download failed: ${imgRes.status}`);

  const mimeType = (imgRes.headers.get('content-type') || 'image/jpeg').split(';')[0];
  return { buffer: Buffer.from(await imgRes.arrayBuffer()), mimeType, credit: data.user?.name };
}

async function generateImage(originalPrompt, size = '1024x1024') {
  const aiPrompt = `${originalPrompt}. Professional, high-quality illustration, no text overlays, no watermarks.`;

  // 1. DALL-E 3 (OpenAI Tier 1 — $5 cumulative spend required)
  try {
    const result = await tryDalle3(aiPrompt, size);
    console.log('  ✓ DALL-E 3');
    return result;
  } catch (err) {
    const missing = err.message?.includes('does not exist') || err.message?.includes('model');
    console.warn(missing
      ? '  ⚠️  DALL-E 3 unavailable (Tier 1 required), trying DALL-E 2...'
      : `  ⚠️  DALL-E 3: ${err.message}`);
  }

  // 2. DALL-E 2
  try {
    const result = await tryDalle2(aiPrompt);
    console.log('  ✓ DALL-E 2');
    return result;
  } catch (err) {
    console.warn(`  ⚠️  DALL-E 2: ${err.message}`);
  }

  // 3. FLUX.1-schnell via HF Inference API (uses existing HF_TOKEN)
  try {
    const result = await tryFlux(aiPrompt);
    console.log('  ✓ FLUX.1-schnell');
    return result;
  } catch (err) {
    console.warn(`  ⚠️  FLUX: ${err.message}`);
  }

  // 4. Gemini Imagen (requires GEMINI_API_KEY)
  try {
    const result = await tryGemini(aiPrompt);
    console.log('  ✓ Gemini');
    return result;
  } catch (err) {
    console.warn(`  ⚠️  Gemini: ${err.message}`);
  }

  // 5. Unsplash stock photo (requires UNSPLASH_ACCESS_KEY)
  try {
    const result = await tryUnsplash(originalPrompt);
    const credit = result.credit ? ` (photo by ${result.credit} on Unsplash)` : ' (Unsplash)';
    console.log(`  ✓ Unsplash${credit}`);
    return result;
  } catch (err) {
    console.warn(`  ⚠️  Unsplash: ${err.message}`);
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
