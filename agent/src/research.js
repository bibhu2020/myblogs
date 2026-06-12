import OpenAI from 'openai';

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const CATEGORIES = [
  {
    name: 'AI',
    discoverPrompt: (date) =>
      `Today is ${date}. Search the web for the single most exciting or surprising AI / machine learning ` +
      `discovery, breakthrough, or development from the past 7 days. Consider: new model releases with ` +
      `surprising capabilities, landmark research papers, safety/alignment breakthroughs, or industry-shaking events. ` +
      `Pick ONE topic — the one with the most discussion, surprise value, or significance. ` +
      `Return: the exact topic name, why it's buzzing right now, 3–5 key facts with specific numbers/names, ` +
      `and 2–3 direct source URLs if available.`,
    researchStyle: 'AI and machine learning',
  },
  {
    name: 'Technology',
    discoverPrompt: (date) =>
      `Today is ${date}. Search the web for the single most interesting technology development from the past 7 days — ` +
      `outside of pure AI/ML. Consider: major software releases, hardware breakthroughs, cybersecurity events, ` +
      `space tech, quantum computing, biotech, or big tech company news. ` +
      `Pick ONE topic with the most buzz or real-world impact. ` +
      `Return: the exact topic, why it matters, 3–5 concrete facts, and 2–3 source URLs if available.`,
    researchStyle: 'technology and engineering',
  },
  {
    name: 'Science',
    discoverPrompt: (date) =>
      `Today is ${date}. Search the web for the most fascinating scientific discovery or research finding ` +
      `published in the past 2 weeks. Consider: physics, astronomy, biology, climate science, medicine, ` +
      `or any field where researchers found something genuinely surprising. ` +
      `Pick ONE discovery — the kind that makes scientists say "we didn't expect this." ` +
      `Return: the finding, the research team/institution, 3–5 key facts with numbers, and source URLs.`,
    researchStyle: 'science and research',
  },
  {
    name: 'History',
    discoverPrompt: (date) =>
      `Today is ${date}. Pick a fascinating, lesser-known historical event, figure, or turning point ` +
      `that most people don't know about — something that genuinely changed the world or reveals a surprising ` +
      `truth about the past. It can be from any era or civilization. ` +
      `Focus on stories that feel relevant or have echoes in today's world. ` +
      `Return: the specific topic, why it's surprising or underappreciated, 3–5 concrete historical facts, ` +
      `and any good reference sources.`,
    researchStyle: 'history and historical analysis',
  },
  {
    name: 'Knowledge',
    discoverPrompt: (date) =>
      `Today is ${date}. Pick one genuinely fascinating concept, phenomenon, or "how does that actually work" ` +
      `question from any field — psychology, economics, mathematics, philosophy, linguistics, or everyday life. ` +
      `Choose something where the real answer surprises most people — a common misconception, a counterintuitive truth, ` +
      `or a deep idea hiding in plain sight. ` +
      `Return: the specific concept, what makes it surprising, 3–5 concrete facts or examples, ` +
      `and any reference sources.`,
    researchStyle: 'knowledge and ideas',
  },
];

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
            content: 'You are an expert researcher with deep knowledge across technology, science, history, and ideas.',
          },
          { role: 'user', content: prompt },
        ],
        max_tokens: 3000,
      });
      return response.choices[0].message.content;
    }
  }
}

function pickCategory() {
  return CATEGORIES[Math.floor(Math.random() * CATEGORIES.length)];
}

export async function discoverTrend() {
  const category = pickCategory();
  const today = new Date().toISOString().split('T')[0];

  console.log(`🔍 Discovering trending topic [category: ${category.name}]...`);
  const result = await webSearch(category.discoverPrompt(today));
  console.log(`📌 Trend: ${result.slice(0, 150)}...`);
  return { trend: result, category };
}

export async function deepResearch({ trend, category }) {
  console.log(`📚 Conducting deep research (3 parallel queries) [${category.name}]...`);
  const snippet = trend.slice(0, 600);
  const style = category.researchStyle;

  const [technical, reactions, implications] = await Promise.all([
    webSearch(
      `Deep research on this ${style} topic: "${snippet}"\n` +
        `Search for: the underlying details, methodology, key findings, data, or engineering decisions. ` +
        `What makes this technically or factually novel? Include specific numbers, names, dates, and ` +
        `direct comparisons to prior work or context. What do the primary sources or experts say?`,
    ),
    webSearch(
      `Community and expert reactions to: "${snippet}"\n` +
        `Search for: what are researchers, practitioners, journalists, and the broader public saying? ` +
        `Look at Twitter/X, Reddit, Hacker News, news outlets, and expert blogs. ` +
        `What controversies or debates has it sparked? Include specific quoted opinions with attribution. ` +
        `What are the counter-arguments and criticisms?`,
    ),
    webSearch(
      `Real-world implications of: "${snippet}"\n` +
        `Search for: which industries, communities, or fields are most impacted? ` +
        `How does this affect everyday people, professionals, or future development? ` +
        `What ethical, safety, or societal concerns does it raise? ` +
        `What are the next steps and the likely 6–12 month impact?`,
    ),
  ]);

  console.log('✅ Research complete');
  return { topicSummary: trend, category: category.name, technical, reactions, implications };
}
