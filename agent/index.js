import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

// Load .env from project root (two levels up from agent/)
dotenv.config({ path: resolve(dirname(fileURLToPath(import.meta.url)), '../.env') });

import { discoverTrend, deepResearch } from './src/research.js';
import { writePost } from './src/writer.js';
import { generateFeaturedImage, processInlineImages } from './src/images.js';
import { mcpInit, mcpCall } from './src/mcp.js';

const SERVER_BASE = process.env.SERVER_BASE || 'https://mishrabp-myblogs.hf.space';
const AUTHOR_EMAIL = process.env.AGENT_AUTHOR_EMAIL || 'ai.researcher@meridian.blog';
const AUTHOR_NAME = process.env.AGENT_AUTHOR_NAME || 'Meridian AI Researcher';
const AUTHOR_PASSWORD =
  process.env.AGENT_AUTHOR_PASSWORD || `MeridianAI${new Date().getFullYear()}!rsch`;

async function ensureGuestAuthor() {
  console.log(`👤 Ensuring guest author "${AUTHOR_NAME}" exists...`);
  try {
    await mcpCall('manage_guest_user', {
      action: 'create',
      email: AUTHOR_EMAIL,
      name: AUTHOR_NAME,
      password: AUTHOR_PASSWORD,
      bio:
        'AI-powered research journalist covering the latest breakthroughs in artificial intelligence, ' +
        'machine learning, and emerging technologies. Each post is grounded in live web research ' +
        'and expert analysis.',
    });
    console.log(`✅ Guest author created: ${AUTHOR_NAME}`);
  } catch (err) {
    // "already exists" or similar — that's fine
    const msg = err.message.toLowerCase();
    if (
      msg.includes('already') ||
      msg.includes('duplicate') ||
      msg.includes('exists') ||
      msg.includes('conflict')
    ) {
      console.log(`✅ Guest author already exists: ${AUTHOR_NAME}`);
    } else {
      console.warn(`⚠️  Could not create guest author (${err.message}). Using name as display.`);
    }
  }
  return AUTHOR_NAME;
}

// MCP list_categories and list_tags return formatted text, not JSON.
// Parse "  ID: N | Name: X | Slug: y ..." lines into [{id, name, slug}].
function parseMcpItems(data) {
  if (Array.isArray(data)) return data;
  const text = typeof data === 'string' ? data : '';
  return text
    .split('\n')
    .map((line) => {
      const m = line.match(/ID:\s*(\d+)\s*\|\s*Name:\s*([^|]+?)\s*\|\s*Slug:\s*(\S+)/);
      return m ? { id: parseInt(m[1]), name: m[2].trim(), slug: m[3].trim() } : null;
    })
    .filter(Boolean);
}

// create_blog returns formatted text; extract slug and ID for reporting.
function parsePublishedPost(data) {
  if (typeof data === 'object' && data !== null) return data;
  const text = String(data);
  const slug = text.match(/Slug:\s*(\S+)/)?.[1] ?? null;
  const id = text.match(/ID:\s*(\d+)/)?.[1] ?? null;
  return { slug, id: id ? parseInt(id) : null, _raw: text };
}

async function pickCategoryAndTags(categoryKeywords, tagKeywords) {
  const [rawCats, rawTags] = await Promise.all([
    mcpCall('list_categories', {}),
    mcpCall('list_tags', {}),
  ]);

  const categories = parseMcpItems(rawCats);
  const tags = parseMcpItems(rawTags);

  // Pick the best matching category
  let categoryId = null;
  if (categories.length) {
    const kws = categoryKeywords.map((k) => k.toLowerCase());
    const match = categories.find((c) =>
      kws.some((k) => c.name.toLowerCase().includes(k) || c.slug.toLowerCase().includes(k)),
    );
    categoryId = (match || categories[0]).id;
  }

  // Pick up to 6 matching tags
  let tagIds = [];
  if (tags.length) {
    const kws = tagKeywords.map((k) => k.toLowerCase());
    const matched = tags.filter((t) =>
      kws.some((k) => t.name.toLowerCase().includes(k) || t.slug.toLowerCase().includes(k)),
    );
    tagIds = matched.slice(0, 6).map((t) => t.id);

    // Pad to at least 3 tags
    if (tagIds.length < 3) {
      const extras = tags
        .filter((t) => !tagIds.includes(t.id))
        .slice(0, 3 - tagIds.length)
        .map((t) => t.id);
      tagIds = [...tagIds, ...extras];
    }
  }

  console.log(`🏷️  Category: ${categoryId}, Tags: [${tagIds.join(', ')}]`);
  return { categoryId, tagIds };
}

export async function runAgent() {
  console.log('\n╔══════════════════════════════════════════╗');
  console.log('║        Meridian AI Blog Agent            ║');
  console.log('╚══════════════════════════════════════════╝\n');

  const t0 = Date.now();

  if (!process.env.OPENAI_API_KEY) {
    throw new Error('OPENAI_API_KEY is required. Add it to .env or export it in your shell.');
  }

  // 1. Connect to MCP
  console.log(`🔌 Connecting to MCP: ${process.env.MCP_URL || 'https://mishrabp-myblogs.hf.space/api/mcp'}`);
  await mcpInit();
  console.log('✅ MCP ready\n');

  // 2. Ensure guest author exists
  const authorName = await ensureGuestAuthor();
  console.log();

  // 3. Research
  const trendResult = await discoverTrend();
  console.log();
  const research = await deepResearch(trendResult);
  console.log();

  // 4. Write post
  const post = await writePost(research);
  console.log(`\n📝 "${post.title}"\n`);

  // 5. Generate featured image
  const featuredImage = await generateFeaturedImage(post.featuredImagePrompt, SERVER_BASE);
  console.log();

  // 6. Process inline images
  const finalContent = await processInlineImages(post.content, SERVER_BASE);
  console.log();

  // 7. Pick category + tags
  const { categoryId, tagIds } = await pickCategoryAndTags(
    post.suggestedCategoryKeywords || [],
    post.suggestedTagKeywords || [],
  );

  // 8. Publish via MCP
  console.log('\n📡 Publishing post...');
  const createArgs = {
    title: post.title,
    content: finalContent,
    excerpt: post.excerpt,
    category_id: categoryId,
    tag_ids: tagIds,
    status: 'published',
    author_name: authorName,
  };
  if (featuredImage) createArgs.featured_image = featuredImage;

  const rawPublished = await mcpCall('create_blog', createArgs);
  const published = parsePublishedPost(rawPublished);

  const elapsed = Math.round((Date.now() - t0) / 1000);
  const slug = published.slug || published.id || '(see site)';

  console.log('\n╔══════════════════════════════════════════╗');
  console.log('║  ✅  Post published successfully!        ║');
  console.log('╚══════════════════════════════════════════╝');
  console.log(`  Title:   ${post.title}`);
  console.log(`  Slug:    ${slug}`);
  console.log(`  Author:  ${authorName}`);
  if (featuredImage) console.log(`  Image:   ${featuredImage}`);
  console.log(`  Time:    ${elapsed}s\n`);

  return published;
}

// Run immediately when invoked as main module
const isMain = process.argv[1] === fileURLToPath(import.meta.url);
if (isMain) {
  runAgent().catch((err) => {
    console.error('\n❌ Agent failed:', err.message);
    process.exit(1);
  });
}
