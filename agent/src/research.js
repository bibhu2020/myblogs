import OpenAI from 'openai';

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

async function webSearch(prompt) {
  // Primary: Responses API with web_search_preview (grounded, live web results)
  try {
    const response = await openai.responses.create({
      model: 'gpt-4o',
      tools: [{ type: 'web_search_preview' }],
      input: prompt,
    });
    return response.output_text;
  } catch {
    // Secondary: gpt-4o-search-preview via Chat Completions
    try {
      const response = await openai.chat.completions.create({
        model: 'gpt-4o-search-preview',
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 3000,
      });
      return response.choices[0].message.content;
    } catch {
      // Fallback: GPT-4o from training knowledge
      console.warn('⚠️  Live web search unavailable — using GPT-4o training knowledge');
      const response = await openai.chat.completions.create({
        model: 'gpt-4o',
        messages: [
          {
            role: 'system',
            content:
              'You are an expert AI researcher with deep knowledge of the field. Discuss the most significant recent AI developments, breakthroughs, and debates you are aware of.',
          },
          { role: 'user', content: prompt },
        ],
        max_tokens: 3000,
      });
      return response.choices[0].message.content;
    }
  }
}

export async function discoverTrend() {
  console.log('🔍 Discovering trending AI topic...');
  const today = new Date().toISOString().split('T')[0];

  const result = await webSearch(
    `Today is ${today}. Search the web for the single most exciting, buzzing, or surprising AI discovery, ` +
      `breakthrough, or development from the past 7 days. Consider: new model releases with surprising capabilities, ` +
      `landmark research papers, major product announcements, safety/alignment breakthroughs, or industry-shaking events. ` +
      `Pick ONE topic — the one with the most discussion, surprise value, or significance. ` +
      `Return: the exact topic name, why it's buzzing right now, 3-5 key facts with specific numbers/names, ` +
      `and 2-3 direct source URLs if available.`,
  );

  console.log(`📌 Trend: ${result.slice(0, 150)}...`);
  return result;
}

export async function deepResearch(topicSummary) {
  console.log('📚 Conducting deep research (3 parallel queries)...');
  const snippet = topicSummary.slice(0, 600);

  const [technical, reactions, implications] = await Promise.all([
    webSearch(
      `Deep technical research on this AI development: "${snippet}"\n` +
        `Search for: the underlying architecture, training methodology, dataset details, benchmark scores, ` +
        `ablation studies, or engineering decisions. What makes this technically novel? ` +
        `Include specific numbers, model names, parameter counts, and direct comparisons to prior work. ` +
        `What do the paper authors or engineering team say about the technical approach?`,
    ),
    webSearch(
      `Community reactions to this AI development: "${snippet}"\n` +
        `Search for: what are AI researchers, ML practitioners, industry leaders, and the broader tech community saying? ` +
        `Look at Twitter/X, Reddit r/MachineLearning, Hacker News, LinkedIn, and expert blogs. ` +
        `What controversies or debates has it sparked? Include specific quoted opinions with attribution. ` +
        `What are the counter-arguments and criticisms?`,
    ),
    webSearch(
      `Real-world implications of this AI development: "${snippet}"\n` +
        `Search for: Which industries are most impacted? How does this affect developers, researchers, businesses, ` +
        `and everyday users? What products or workflows could this enable or disrupt? ` +
        `What ethical, safety, or regulatory concerns does it raise? ` +
        `What are the next logical steps and what might the 6-12 month impact be?`,
    ),
  ]);

  console.log('✅ Research complete');
  return { topicSummary, technical, reactions, implications };
}
