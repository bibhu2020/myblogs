import OpenAI from 'openai';

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const SYSTEM_PROMPT = `You are a senior technology journalist writing for Meridian, a premium AI and technology blog.
Your posts are detailed, authoritative, and read like long-form magazine features — not listicles.

CONTENT RULES:
- Minimum 3,000 words of body content (aim for 3,500–4,500 for a 12-15 min read)
- Write flowing narrative prose, not bullet-point summaries
- Explain the WHY and HOW, not just the WHAT
- Include concrete examples, analogies, and real technical depth
- Use pull quotes from real people (from the research) inside <blockquote> tags
- Add code snippets with <pre><code class="language-X"> where illustrative

IMAGE PLACEHOLDERS:
Place 4–6 image placeholders throughout using this EXACT format (on its own line):
[[IMAGE: detailed DALL-E 3 prompt — be specific about style, content, composition, colors]]

Suggested placement:
- One after the opening paragraph (scene-setting visual)
- One for each major technical concept
- One showing real-world application or impact
- One near the conclusion

OUTPUT FORMAT — return a single JSON object with these exact keys:
{
  "title": "55–70 character headline, specific and compelling, no clickbait",
  "excerpt": "140–160 character teaser for blog listing cards — hook the reader",
  "suggestedCategoryKeywords": ["ai", "machine-learning", "research"],
  "suggestedTagKeywords": ["openai", "llm", "transformer", "neural-network", "gpt"],
  "featuredImagePrompt": "Detailed DALL-E 3 prompt for a 16:9 hero image. Photorealistic or artistic render. No text/logos.",
  "content": "Full HTML blog content string using ONLY these tags: <h2> <h3> <h4> <p> <strong> <em> <a href=''> <ul> <ol> <li> <blockquote> <pre><code class='language-X'> <img src='' alt=''>"
}

Do not include markdown, only valid HTML in the content field. Escape all quotes inside JSON strings.`;

export async function writePost(research) {
  console.log('✍️  Writing blog post (this takes ~60s)...');

  const userPrompt = `Write a comprehensive, deeply researched blog post based on the research below.
The post must be AT LEAST 3,000 words — do not cut corners. This is long-form editorial journalism.

## TOPIC & KEY FACTS
${research.topicSummary}

## TECHNICAL DEPTH
${research.technical}

## EXPERT OPINIONS & COMMUNITY REACTION
${research.reactions}

## REAL-WORLD IMPLICATIONS
${research.implications}

Structure suggestion (adapt as needed):
1. Hook — Open with the most surprising or dramatic element
2. Background — What was the state of the art before this?
3. The Breakthrough — What exactly happened / was built / was discovered?
4. Under the Hood — Technical deep-dive (architecture, methodology, results)
5. Expert Voices — Reactions from the community (use real quotes from the research)
6. Implications — Who benefits? Who's disrupted? What changes?
7. The Bigger Picture — Where does this fit in the arc of AI progress?
8. Key Takeaways — 4–6 bullet points in a <ul>
9. Conclusion — Forward-looking synthesis`;

  const response = await openai.chat.completions.create({
    model: 'gpt-4o',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: userPrompt },
    ],
    response_format: { type: 'json_object' },
    max_tokens: 10000,
    temperature: 0.8,
  });

  let post = JSON.parse(response.choices[0].message.content);
  const wordCount = countWords(post.content);
  console.log(`📊 Draft word count: ${wordCount}`);

  if (wordCount < 2200) {
    console.log('📝 Expanding post to meet length requirements...');
    const expansion = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: userPrompt },
        { role: 'assistant', content: JSON.stringify(post) },
        {
          role: 'user',
          content:
            'The content is too short. Expand the HTML content to at least 3,000 words by: ' +
            'adding more paragraphs to each section, deepening the technical explanation, ' +
            'adding more expert quotes and context, and expanding the implications section. ' +
            'Return the complete updated JSON with the same structure.',
        },
      ],
      response_format: { type: 'json_object' },
      max_tokens: 10000,
      temperature: 0.7,
    });
    post = JSON.parse(expansion.choices[0].message.content);
    console.log(`📊 Final word count: ${countWords(post.content)}`);
  }

  return post;
}

function countWords(html) {
  return html.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
}
