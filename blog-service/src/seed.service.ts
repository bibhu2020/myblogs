import { Injectable, OnModuleInit } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Post, PostStatus } from './post.entity';
import { Category } from './category.entity';
import { Tag } from './tag.entity';
import slugify from 'slugify';

@Injectable()
export class SeedService implements OnModuleInit {
  constructor(
    @InjectRepository(Post) private postRepo: Repository<Post>,
    @InjectRepository(Category) private catRepo: Repository<Category>,
    @InjectRepository(Tag) private tagRepo: Repository<Tag>,
  ) {}

  async onModuleInit() {
    await this.migrateCategories();
    const count = await this.catRepo.count();
    if (count > 0) return;
    await this.seed();
  }

  // Rename old categories to the new physics/AI theme and add Relativity if missing.
  // Runs on every startup — safe to call multiple times (idempotent).
  async migrateCategories() {
    const renames = [
      { oldSlug: 'technology', name: 'AI/ML',       slug: 'ai-ml',       color: '#6366F1', icon: '🤖',  description: 'Deep explorations of artificial intelligence, machine learning, neural networks, and the emerging world of thinking machines' },
      { oldSlug: 'science',    name: 'Quantum',      slug: 'quantum',     color: '#8B5CF6', icon: '⚛️',  description: 'Quantum mechanics, quantum computing, and the strange world below the classical limit — from the ultraviolet catastrophe to entanglement' },
      { oldSlug: 'knowledge',  name: 'Educational',  slug: 'educational', color: '#F59E0B', icon: '📚',  description: 'Clear, animated explanations of the most beautiful ideas in physics and computing, designed for curious laypeople' },
    ];
    for (const r of renames) {
      const cat = await this.catRepo.findOne({ where: { slug: r.oldSlug } });
      if (cat) {
        await this.catRepo.update(cat.id, { name: r.name, slug: r.slug, color: r.color, icon: r.icon, description: r.description });
        console.log(`Migrated category: ${r.oldSlug} → ${r.slug}`);
      }
    }
    // Add Relativity if it doesn't already exist
    const hasRelativity = await this.catRepo.findOne({ where: { slug: 'relativity' } });
    if (!hasRelativity) {
      await this.catRepo.save({ name: 'Relativity', slug: 'relativity', color: '#0EA5E9', icon: '🌌', description: "Einstein's theories of special and general relativity, spacetime, black holes, time dilation, and the large-scale structure of the cosmos" });
      console.log('Added category: Relativity');
    }
    // Update Travel description to science-travel focus
    const travel = await this.catRepo.findOne({ where: { slug: 'travel' } });
    if (travel && !travel.description?.includes('CERN')) {
      await this.catRepo.update(travel.id, { description: "Journeys to the world's most scientifically fascinating places — CERN, observatories, quantum labs, and destinations where breakthroughs happen", color: '#10B981', icon: '✈️' });
    }
    // Update History description to science history
    const history = await this.catRepo.findOne({ where: { slug: 'history' } });
    if (history && !history.description?.includes('quantum')) {
      await this.catRepo.update(history.id, { description: 'The history of quantum mechanics, relativity, computing, and the scientists who fundamentally changed our understanding of the universe', color: '#92400E', icon: '🏛️' });
    }
  }

  async seed() {
    // Categories
    const aiml      = await this.catRepo.save({ name: 'AI/ML',       slug: 'ai-ml',       description: 'Deep explorations of artificial intelligence, machine learning, neural networks, and the emerging world of thinking machines',                   color: '#6366F1', icon: '🤖' });
    const travel    = await this.catRepo.save({ name: 'Travel',       slug: 'travel',       description: 'Journeys to the world\'s most scientifically fascinating places — CERN, observatories, quantum labs, and destinations where breakthroughs happen', color: '#10B981', icon: '✈️' });
    const history   = await this.catRepo.save({ name: 'History',      slug: 'history',      description: 'The history of quantum mechanics, relativity, computing, and the scientists who fundamentally changed our understanding of the universe',            color: '#92400E', icon: '🏛️' });
    const quantum   = await this.catRepo.save({ name: 'Quantum',      slug: 'quantum',      description: 'Quantum mechanics, quantum computing, and the strange world below the classical limit — from the ultraviolet catastrophe to entanglement',          color: '#8B5CF6', icon: '⚛️' });
    const educational = await this.catRepo.save({ name: 'Educational', slug: 'educational', description: 'Clear, animated explanations of the most beautiful ideas in physics and computing, designed for curious laypeople',                                color: '#F59E0B', icon: '📚' });
    const relativity  = await this.catRepo.save({ name: 'Relativity',  slug: 'relativity',  description: 'Einstein\'s theories of special and general relativity, spacetime, black holes, time dilation, and the large-scale structure of the cosmos',       color: '#0EA5E9', icon: '🌌' });

    // Tags
    const tags = await this.tagRepo.save([
      // AI/ML
      { name: 'AI', slug: 'ai' },
      { name: 'Machine Learning', slug: 'machine-learning' },
      { name: 'Neural Networks', slug: 'neural-networks' },
      { name: 'LLM', slug: 'llm' },
      { name: 'Generative AI', slug: 'generative-ai' },
      // Quantum
      { name: 'Quantum Mechanics', slug: 'quantum-mechanics' },
      { name: 'Quantum Computing', slug: 'quantum-computing' },
      { name: 'Entanglement', slug: 'entanglement' },
      { name: 'Superposition', slug: 'superposition' },
      { name: 'Wave Function', slug: 'wave-function' },
      // Relativity
      { name: 'Relativity', slug: 'relativity' },
      { name: 'Spacetime', slug: 'spacetime' },
      { name: 'Black Holes', slug: 'black-holes' },
      { name: 'Time Dilation', slug: 'time-dilation' },
      { name: 'Einstein', slug: 'einstein' },
      // Travel
      { name: 'CERN', slug: 'cern' },
      { name: 'Observatory', slug: 'observatory' },
      { name: 'Photography', slug: 'photography' },
      { name: 'Asia', slug: 'asia' },
      { name: 'Europe', slug: 'europe' },
      // Educational / Physics
      { name: 'Photoelectric Effect', slug: 'photoelectric-effect' },
      { name: 'Blackbody Radiation', slug: 'blackbody-radiation' },
      { name: 'Double Slit', slug: 'double-slit' },
      { name: 'Physics', slug: 'physics' },
      { name: 'Explainer', slug: 'explainer' },
      // History of Science
      { name: 'History of Science', slug: 'history-of-science' },
      { name: 'Planck', slug: 'planck' },
      { name: 'Bohr', slug: 'bohr' },
      // Keep some legacy ones used by existing posts
      { name: 'JavaScript', slug: 'javascript' },
      { name: 'NestJS', slug: 'nestjs' },
      { name: 'Docker', slug: 'docker' },
      { name: 'Space', slug: 'space' },
      { name: 'Food', slug: 'food' },
      { name: 'Adventure', slug: 'adventure' },
      { name: 'Web Dev', slug: 'web-dev' },
      { name: 'Ancient World', slug: 'ancient-world' },
      { name: 'Medieval', slug: 'medieval' },
      { name: 'Civilization', slug: 'civilization' },
    ]);

    const tagMap: Record<string, Tag> = Object.fromEntries(tags.map(t => [t.slug, t]));

    // Tech Blog Posts
    await this.postRepo.save([
      {
        title: 'The Rise of AI-Powered Development Tools in 2024',
        slug: 'rise-of-ai-powered-development-tools-2024',
        excerpt: 'Artificial intelligence is reshaping how we write, debug, and deploy code. From GitHub Copilot to Claude, discover how AI assistants are transforming the developer experience.',
        content: `<h2>The AI Revolution in Software Development</h2>
<p>The software development landscape has undergone a seismic shift in the past two years. AI-powered coding assistants have moved from novelty to necessity for millions of developers worldwide. Tools like GitHub Copilot, Amazon CodeWhisperer, and Anthropic's Claude are not just autocompleting code — they're fundamentally changing how we think about programming.</p>

<h2>What Makes Modern AI Dev Tools Different</h2>
<p>Earlier code completion tools worked with simple pattern matching and static analysis. Today's AI assistants understand context across entire codebases, can explain complex algorithms in plain English, and even write tests and documentation automatically.</p>

<blockquote>
<p>"The best developers of tomorrow won't be those who memorize syntax — they'll be those who can effectively collaborate with AI systems." — Tech Industry Analyst</p>
</blockquote>

<h2>Key AI Tools Reshaping Development</h2>
<ul>
<li><strong>GitHub Copilot X</strong> — Deep IDE integration with GPT-4, chat interface, pull request summaries</li>
<li><strong>Cursor IDE</strong> — A VS Code fork with AI baked into every layer of the editor</li>
<li><strong>Claude Code</strong> — Anthropic's agentic coding tool that can handle multi-file refactors</li>
<li><strong>Tabnine</strong> — Privacy-first AI completion that can run on-premise</li>
</ul>

<h2>The Productivity Gains Are Real</h2>
<p>A recent study by GitHub found that developers using Copilot completed tasks 55% faster than those without. More importantly, developers reported higher satisfaction — spending less time on boilerplate and more time on creative problem-solving.</p>

<h2>The Skills That Still Matter</h2>
<p>AI tools excel at generating routine code, but they struggle with novel architectural decisions, performance optimization in critical paths, and security-sensitive code. The developer who understands <em>why</em> code works, not just how to write it, will always have an edge.</p>

<h2>Looking Ahead</h2>
<p>We're moving toward a world where natural language becomes a primary programming interface. The line between "describing what you want" and "writing code" is blurring rapidly. The developers who embrace this shift while deepening their foundational knowledge will define the next era of software.</p>`,
        featuredImage: 'https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=1200&q=80',
        status: PostStatus.PUBLISHED,
        authorId: 1,
        authorName: 'Site Admin',
        readTime: 5,
        views: 1247,
        category: aiml,
        tags: [tagMap['ai'], tagMap['web-dev'], tagMap['javascript']],
      },
      {
        title: 'Building Microservices with NestJS: A Complete Guide',
        slug: 'building-microservices-nestjs-complete-guide',
        excerpt: 'Learn how to architect scalable microservices using NestJS, explore service communication patterns, and deploy with Docker. A hands-on guide for modern backend development.',
        content: `<h2>Why Microservices?</h2>
<p>Monolithic applications are easy to start with but become difficult to scale and maintain as teams and complexity grow. Microservices offer independent deployability, technology flexibility, and clear team ownership — but they come with their own distributed systems challenges.</p>

<h2>Why NestJS for Microservices?</h2>
<p>NestJS is a progressive Node.js framework built on TypeScript that provides first-class support for microservice architectures. It ships with built-in transport layers supporting TCP, Redis, NATS, RabbitMQ, and Kafka — all with a unified API.</p>

<pre><code>// Creating a microservice in NestJS
const app = await NestFactory.createMicroservice(AppModule, {
  transport: Transport.TCP,
  options: { port: 3001 },
});
await app.listen();</code></pre>

<h2>Core Concepts</h2>
<h3>Service Discovery</h3>
<p>In a microservices architecture, services need to find each other dynamically. This can be achieved through service registries like Consul or Kubernetes DNS, or through an API Gateway pattern.</p>

<h3>API Gateway Pattern</h3>
<p>The API Gateway acts as the single entry point for all clients. It handles routing, authentication, rate limiting, and response aggregation — keeping the microservices focused on their domain logic.</p>

<h3>Database Per Service</h3>
<p>Each microservice should own its data. This means separate databases (even if they're on the same server initially) to prevent tight coupling at the data layer.</p>

<h2>Communication Patterns</h2>
<ul>
<li><strong>Synchronous (Request/Response)</strong> — HTTP REST or gRPC, great for reads and simple commands</li>
<li><strong>Asynchronous (Events)</strong> — Message queues (RabbitMQ, Kafka), great for writes and eventual consistency</li>
</ul>

<h2>Containerization with Docker</h2>
<p>Each microservice should be packaged as a Docker container. A <code>docker-compose.yml</code> file ties them together during development, while Kubernetes handles production orchestration.</p>

<h2>Conclusion</h2>
<p>NestJS provides excellent tooling for building microservices. Start small — you don't need all the complexity on day one. Extract services from your monolith as natural boundaries emerge.</p>`,
        featuredImage: 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&q=80',
        status: PostStatus.PUBLISHED,
        authorId: 1,
        authorName: 'Site Admin',
        readTime: 8,
        views: 892,
        category: aiml,
        tags: [tagMap['nestjs'], tagMap['ai'], tagMap['docker']],
      },
      {
        title: 'Vue 3 Composition API: Why It Changes Everything',
        slug: 'vue-3-composition-api-changes-everything',
        excerpt: 'The Composition API in Vue 3 represents a fundamental shift in how we organize and reuse component logic. Explore how composables replace mixins and make your code more maintainable.',
        content: `<h2>The Problem with Vue 2's Options API</h2>
<p>Vue 2's Options API organized code by type — data here, methods there, computed properties in another section. As components grew complex, related logic was scattered across multiple options blocks, making it hard to extract and reuse.</p>

<h2>Enter the Composition API</h2>
<p>Vue 3's Composition API lets you organize code by <em>feature</em> instead of by type. All the logic for a particular concern lives together in a composable function.</p>

<pre><code>// useCounter.js — a simple composable
import { ref, computed } from 'vue'

export function useCounter(initialValue = 0) {
  const count = ref(initialValue)
  const doubled = computed(() => count.value * 2)

  function increment() { count.value++ }
  function decrement() { count.value-- }

  return { count, doubled, increment, decrement }
}</code></pre>

<h2>Composables vs Mixins</h2>
<p>Mixins were Vue 2's mechanism for sharing logic, but they had significant drawbacks: unclear source of properties, namespace conflicts, and implicit dependencies. Composables solve all of these because they're just functions — the source is explicit, naming conflicts are handled by the caller, and dependencies are passed as arguments.</p>

<h2>script setup: The Sugar on Top</h2>
<p>The <code>&lt;script setup&gt;</code> syntax is compile-time sugar for the Composition API that results in more concise and performant code:</p>

<pre><code>&lt;script setup&gt;
import { useCounter } from './useCounter'
const { count, increment } = useCounter(10)
&lt;/script&gt;

&lt;template&gt;
  &lt;button @click="increment"&gt;Count: {{ count }}&lt;/button&gt;
&lt;/template&gt;</code></pre>

<h2>Real-World Benefits</h2>
<p>Teams adopting Vue 3's Composition API report significantly better TypeScript integration, easier unit testing of logic (just test the composable function), and better IDE support with proper type inference.</p>

<h2>Should You Migrate?</h2>
<p>Vue 3 is backward-compatible — the Options API still works fine. But for new projects and complex components, the Composition API is the way forward. Start by extracting complex computed/watcher logic into composables and you'll immediately feel the difference.</p>`,
        featuredImage: 'https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=1200&q=80',
        status: PostStatus.PUBLISHED,
        authorId: 1,
        authorName: 'Site Admin',
        readTime: 6,
        views: 654,
        category: aiml,
        tags: [tagMap['javascript'], tagMap['web-dev'], tagMap['ai']],
      },
    ]);

    // Travel Blog Posts
    await this.postRepo.save([
      {
        title: 'Two Weeks in Japan: A Journey Through Ancient and Modern',
        slug: 'two-weeks-in-japan-ancient-and-modern',
        excerpt: 'From the neon-lit streets of Tokyo to the serene bamboo groves of Kyoto, Japan offers a breathtaking contrast of ancient tradition and cutting-edge modernity. Here\'s my complete two-week itinerary.',
        content: `<h2>Why Japan Should Be Your Next Destination</h2>
<p>Japan is unlike anywhere else on Earth. It's a country where a thousand-year-old Buddhist temple sits next to a gleaming robot restaurant, where you can eat the world's finest sushi for breakfast and then watch cherry blossoms fall in a feudal castle garden. After two weeks exploring this extraordinary country, I can confidently say it exceeded every expectation.</p>

<h2>Tokyo: The City That Never Stops</h2>
<p>Landing at Narita and taking the Narita Express into the city, the first thing that strikes you is the sheer scale of Tokyo. With 37 million people in the greater metropolitan area, it's the world's largest city — yet it feels surprisingly calm and navigable.</p>

<p>Spend your first days in neighborhoods that each feel like their own city:</p>
<ul>
<li><strong>Shibuya</strong> — Home of the famous scramble crossing, youth fashion, and the loyal Hachiko statue</li>
<li><strong>Harajuku</strong> — Takeshita Street's vibrant street fashion meets the tranquil Meiji Shrine</li>
<li><strong>Shinjuku</strong> — By day, the world's busiest train station; by night, Golden Gai's tiny jazz bars</li>
<li><strong>Akihabara</strong> — Electronics and anime culture at its most intense</li>
</ul>

<h2>Kyoto: Where Japan Keeps Its Soul</h2>
<p>The bullet train from Tokyo to Kyoto takes just over two hours — a journey that crosses all of Honshu island. Kyoto is Japan's former imperial capital and still its cultural heart. With over 1,600 temples and 400 shrines, the challenge is choosing where to focus.</p>

<blockquote>
<p>"Kyoto is not a museum — it's a living city where people still practice traditions their ancestors began centuries ago."</p>
</blockquote>

<p>Don't miss the Fushimi Inari Shrine — an otherworldly tunnel of thousands of orange torii gates stretching up a mountain. Go early (before 7am) to experience it without crowds.</p>

<h2>Hiroshima and Miyajima</h2>
<p>The Peace Memorial Museum in Hiroshima is one of the most important — and emotionally difficult — places I've ever visited. The personal stories of survivors make history viscerally real. The adjacent Peace Park, with its iconic A-Bomb Dome, is a space for reflection on humanity's capacity for both destruction and resilience.</p>

<p>A short ferry ride away, Miyajima Island is home to the famous floating torii gate of Itsukushima Shrine — one of Japan's most iconic images, even more beautiful in person.</p>

<h2>Practical Tips</h2>
<ul>
<li>Get a <strong>JR Pass</strong> before you arrive — it covers the Shinkansen and saves significant money</li>
<li>Download <strong>Google Maps offline</strong> for Tokyo — the train system is complex but Google navigates it perfectly</li>
<li>Cash is still king in Japan — many smaller establishments don't accept cards</li>
<li>Learn to say: <em>Sumimasen</em> (excuse me), <em>Arigatou gozaimasu</em> (thank you very much), <em>Eigo wo hanasemasu ka?</em> (Do you speak English?)</li>
</ul>

<h2>The Food</h2>
<p>Japanese food culture deserves its own post. From $3 bowls of ramen that would win Michelin stars elsewhere, to $300 omakase sushi experiences, the range and quality of Japanese cuisine is unmatched. Eat at convenience stores (7-Eleven in Japan is genuinely good), explore depachika (department store basement food halls), and let yourself get lost in izakayas.</p>`,
        featuredImage: 'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=1200&q=80',
        gallery: JSON.stringify([
          'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&q=80',
          'https://images.unsplash.com/photo-1528360983277-13d401cdc186?w=800&q=80',
          'https://images.unsplash.com/photo-1542051841857-5f90071e7989?w=800&q=80',
          'https://images.unsplash.com/photo-1513407030348-c983a97b98d8?w=800&q=80',
        ]),
        status: PostStatus.PUBLISHED,
        authorId: 1,
        authorName: 'Site Admin',
        readTime: 10,
        views: 2341,
        category: travel,
        tags: [tagMap['asia'], tagMap['photography'], tagMap['food']],
      },
      {
        title: 'Backpacking Southeast Asia on $50 a Day',
        slug: 'backpacking-southeast-asia-50-dollars-a-day',
        excerpt: 'Southeast Asia is one of the world\'s great budget travel destinations. Thailand, Vietnam, Cambodia, and Laos offer incredible experiences without breaking the bank. Here\'s how to do it right.',
        content: `<h2>The Southeast Asia Circuit</h2>
<p>The classic Southeast Asia backpacker route has evolved over decades into something well-worn but still magical. Most travelers enter through Bangkok and work their way through the region over one to three months. Here's what I learned during my 6-week journey.</p>

<h2>Thailand: The Perfect Starting Point</h2>
<p>Bangkok is chaotic, overwhelming, and utterly addictive. The Grand Palace, Wat Pho's giant reclining Buddha, and the street food scene on Khao San Road make it one of the world's great cities for first-time Asia travelers.</p>

<p>From Bangkok, head north to Chiang Mai for a completely different vibe — mountain temples, cooking classes, elephant sanctuaries (choose ethical ones!), and a thriving digital nomad scene. Or head south to the islands: Koh Tao for diving certification, Koh Phangan for full moon (or not), Koh Lanta for more laid-back vibes.</p>

<h2>Vietnam: The Long, Beautiful Country</h2>
<p>Vietnam rewards slow travel. The country stretches 1,650 km from north to south, and each region has its own character:</p>
<ul>
<li><strong>Hanoi</strong> — Old Quarter chaos, pho for breakfast, Hoan Kiem Lake at dawn</li>
<li><strong>Ha Long Bay</strong> — 1,969 limestone islands rising from emerald waters. Overrated? A little. Still magnificent? Absolutely.</li>
<li><strong>Hoi An</strong> — Ancient town, lanterns at night, the best tailor shops in the world</li>
<li><strong>Ho Chi Minh City</strong> — Frenetic energy, war history, rooftop bars, the best banh mi of your life</li>
</ul>

<h2>Cambodia: Beyond Angkor Wat</h2>
<p>Angkor Wat is one of humanity's greatest architectural achievements — and somehow even more impressive in person than in photos. But don't skip the rest of Cambodia. Phnom Penh's sobering history at S-21 and the Killing Fields is essential for understanding modern Southeast Asia. And the south coast islands like Koh Rong remain among the region's most beautiful, relatively unspoiled beaches.</p>

<h2>The $50/Day Budget Breakdown</h2>
<table>
<tr><th>Category</th><th>Average Daily Cost</th></tr>
<tr><td>Accommodation (dorm/guesthouse)</td><td>$8-15</td></tr>
<tr><td>Food (street food + one sit-down meal)</td><td>$10-15</td></tr>
<tr><td>Transport (local buses, tuk-tuks)</td><td>$5-10</td></tr>
<tr><td>Activities</td><td>$10-15</td></tr>
<tr><td>Total</td><td>$33-55</td></tr>
</table>

<h2>Money-Saving Tips</h2>
<ul>
<li>Always get a local SIM card — data is incredibly cheap across the region</li>
<li>Eat where locals eat — street food stalls are safer than they look and infinitely better than tourist restaurants</li>
<li>Take overnight buses/trains for longer journeys to save on accommodation</li>
<li>Book accommodations directly rather than through booking sites when possible</li>
<li>Travel slowly — moving every day is expensive and exhausting</li>
</ul>`,
        featuredImage: 'https://images.unsplash.com/photo-1552465011-b4e21bf6e79a?w=1200&q=80',
        gallery: JSON.stringify([
          'https://images.unsplash.com/photo-1506665531195-3566af2b4dfa?w=800&q=80',
          'https://images.unsplash.com/photo-1559592413-7cec4d0cae2b?w=800&q=80',
          'https://images.unsplash.com/photo-1528181304800-259b08848526?w=800&q=80',
        ]),
        status: PostStatus.PUBLISHED,
        authorId: 1,
        authorName: 'Site Admin',
        readTime: 12,
        views: 1876,
        category: travel,
        tags: [tagMap['asia'], tagMap['adventure'], tagMap['food'], tagMap['photography']],
      },
      {
        title: 'The Amalfi Coast: Italy\'s Most Dramatic Coastline',
        slug: 'amalfi-coast-italys-most-dramatic-coastline',
        excerpt: 'Cliffside villages painted in pastel, turquoise Mediterranean waters, and roads that cling impossibly to sheer rock faces — the Amalfi Coast is Italy at its most theatrical. A complete travel guide.',
        content: `<h2>First Impressions</h2>
<p>Nothing quite prepares you for your first glimpse of the Amalfi Coast. Whether you arrive by ferry from Naples or by road along the famous Costiera Amalfitana, the moment the coast comes into view feels like a film set — too beautiful to be real. Cliffside towns cascade down to the sea in an explosion of terracotta, lemon yellow, and bougainvillea pink.</p>

<h2>The Towns</h2>
<h3>Positano</h3>
<p>The most photographed town on the coast, Positano is draped on a steep hillside with its characteristic dome of the Church of Santa Maria Assunta at its heart. It's expensive and crowded, but the views from the beach looking back up at the town are worth every euro.</p>

<h3>Ravello</h3>
<p>Perched 350 meters above the sea, Ravello is the coast's cultural jewel. Villa Cimbrone's Terrace of Infinity — a balcony lined with busts overlooking nothing but sea and sky — is one of the most beautiful spots in Europe. Wagner, Greta Garbo, and Virginia Woolf all retreated here.</p>

<h3>Amalfi Town</h3>
<p>The coast's namesake town punches above its weight historically — once a major medieval maritime republic that rivaled Venice. The Arab-Norman cathedral with its black-and-white striped facade is extraordinary. The town square (Piazza Duomo) is perfect for an Aperol Spritz at sunset.</p>

<h2>Getting Around</h2>
<p>The SITA bus along the SS163 coastal road is the most adventurous — and often the only practical — way to travel between towns. Drivers navigate impossible switchbacks with the confidence born of doing it every day. Ferries connect the major towns from spring to October and offer the best views.</p>

<blockquote>
<p>Rent a scooter only if you're an experienced rider. The road is genuinely dangerous for novices.</p>
</blockquote>

<h2>Food and Drink</h2>
<p>The Amalfi Coast is lemon country. Everything — limoncello, pasta al limone, lemon granita, lemon-glazed ceramics — celebrates the sfusato amalfitano, the enormous, intensely flavored lemons that grow on terraces above the coast.</p>

<p>Eat fresh mozzarella di bufala from Campania every day. Order whatever fish was caught that morning. Drink the local Greco di Tufo white wine.</p>

<h2>When to Go</h2>
<p><strong>Best:</strong> May, June, September, early October — warm, manageable crowds, all ferries running.</p>
<p><strong>Avoid:</strong> July and August — suffocating heat, impossible crowds, triple prices.</p>
<p><strong>Shoulder:</strong> April and late October — cooler, quieter, beautiful light, but some businesses close.</p>`,
        featuredImage: 'https://images.unsplash.com/photo-1533104816931-20fa691ff6ca?w=1200&q=80',
        gallery: JSON.stringify([
          'https://images.unsplash.com/photo-1516483638261-f4dbaf036963?w=800&q=80',
          'https://images.unsplash.com/photo-1534308983496-4fabb1a015ee?w=800&q=80',
          'https://images.unsplash.com/photo-1523906834658-6e24ef2386f9?w=800&q=80',
        ]),
        status: PostStatus.PUBLISHED,
        authorId: 1,
        authorName: 'Site Admin',
        readTime: 8,
        views: 1543,
        category: travel,
        tags: [tagMap['europe'], tagMap['photography'], tagMap['food']],
      },
    ]);

    // History posts
    await this.postRepo.save([
      {
        title: 'The Fall of Constantinople: How 1453 Changed the World',
        slug: 'fall-of-constantinople-1453',
        excerpt: 'On 29 May 1453, Ottoman forces under Sultan Mehmed II breached the walls of Constantinople, ending the Byzantine Empire and opening a new chapter in world history.',
        content: `<h2>The Last Day of an Empire</h2><p>On the morning of 29 May 1453, the citizens of Constantinople awoke to the sound of Ottoman war drums. After fifty-three days of siege, the city that had stood as the capital of the Roman Empire for over a thousand years would not survive to see another dawn. Emperor Constantine XI Palaiologos, knowing the end had come, reportedly removed his imperial regalia and charged into the fighting as a soldier. His body was never definitively identified.</p><h2>Why Constantinople Mattered</h2><p>Founded by Emperor Constantine I in 330 AD on the strategic strait between Europe and Asia, Constantinople had served as the anchor of Eastern civilization for over eleven centuries. While Western Rome collapsed in 476 AD, Constantinople preserved Roman law, Greek philosophy, and Christian theology through the Dark Ages.</p><blockquote><p>For over a thousand years, Constantinople was the largest, wealthiest, and most sophisticated city in the Christian world — a repository of classical knowledge when Europe had largely forgotten it.</p></blockquote><h2>How Mehmed Did It</h2><p>The young Sultan Mehmed II, just 21 years old, brought several innovations that overwhelmed the Byzantine defenses:</p><ul><li><strong>The Basilica Cannon</strong> — A massive bombard 8 meters long that fired 600-pound stone balls</li><li><strong>Naval flanking</strong> — Ships dragged overland on greased logs to bypass a harbor chain</li><li><strong>Sheer numbers</strong> — An estimated 80,000–100,000 Ottoman troops against perhaps 7,000 Byzantine defenders</li></ul><h2>The World That Changed</h2><p>The fall had consequences that reverberated for centuries. Ottoman control of eastern trade routes accelerated European exploration westward, directly contributing to Columbus's 1492 voyage. Byzantine scholars in exile brought Greek texts to Italy, fueling the Renaissance. Moscow declared itself the "Third Rome," shaping Russian imperial identity for centuries.</p>`,
        featuredImage: 'https://images.unsplash.com/photo-1541432901042-2d8bd64b4a9b?w=1200&q=80',
        status: PostStatus.PUBLISHED, authorId: 1, authorName: 'Site Admin',
        readTime: 8, views: 1134, category: history,
        tags: [tagMap['ancient-world'], tagMap['medieval'], tagMap['civilization']],
      },
      {
        title: 'The Silk Road: Ancient Highways of Trade and Culture',
        slug: 'silk-road-ancient-trade-culture',
        excerpt: 'For over fifteen hundred years, a network of overland and maritime routes connected China to the Mediterranean, carrying not just goods but ideas, religions, diseases, and entire civilizations.',
        content: `<h2>Not One Road, But Many</h2><p>The term "Silk Road" was coined only in 1877 by the German geographer Ferdinand von Richthofen, and it was never a single road. It was a shifting, branching network of overland and sea routes stretching roughly 6,400 kilometers from Chang'an in China through Central Asia, Persia, and the Arabian Peninsula to the Mediterranean ports of Alexandria and Antioch.</p><blockquote><p>The Silk Road was less a highway and more a relay race — goods moving in stages through a chain of intermediaries, each extracting a profit, each adding a layer of cultural exchange.</p></blockquote><h2>What Really Traveled: Ideas</h2><p>The most consequential cargo was invisible. Buddhism traveled from India to China along Silk Road routes in the 1st century AD. Islam spread rapidly along trade networks after 632 AD. Paper and printing moved westward from China. The Black Death followed trade routes from Central Asia to Europe in 1346–1353. Mathematical notation, including the concept of zero, traveled from India through Persian and Arab intermediaries to Europe.</p><h2>The Golden Age</h2><p>The Silk Road reached its cultural peak between the 7th and 10th centuries, when Tang Dynasty China and the Abbasid Caliphate created two great poles of civilization linked by thriving commerce. Tang Chang'an, with perhaps a million inhabitants, was the most cosmopolitan city on Earth — home to Persian merchants, Japanese students, Korean diplomats, and Central Asian musicians.</p><h2>Decline and Legacy</h2><p>Portuguese navigators seeking a sea route to Asian spices opened the Cape of Good Hope route in 1497–1498. China's Belt and Road Initiative, launched in 2013, explicitly invokes the Silk Road metaphor for its trillion-dollar infrastructure investment program — one of the defining geopolitical questions of our century.</p>`,
        featuredImage: 'https://images.unsplash.com/photo-1548013146-72479768bada?w=1200&q=80',
        status: PostStatus.PUBLISHED, authorId: 1, authorName: 'Site Admin',
        readTime: 9, views: 876, category: history,
        tags: [tagMap['ancient-world'], tagMap['civilization'], tagMap['history-of-science']],
      },
      {
        title: 'The Black Death: How a Pandemic Reshaped Medieval Europe',
        slug: 'black-death-pandemic-medieval-europe',
        excerpt: 'Between 1347 and 1351, bubonic plague killed between 30 and 60 percent of Europe\'s population — and accidentally built the foundations of the modern world.',
        content: `<h2>The Ships from Caffa</h2><p>In October 1347, twelve Genoese trading ships docked at the Sicilian port of Messina. When port officials came to greet the sailors, they found most of them dead and the rest covered in black, pus-oozing boils. The Black Death had arrived in Western Europe.</p><h2>The Scale of Death</h2><p>Modern epidemiologists estimate that the Black Death killed between 75 and 200 million people across Eurasia between 1346 and 1353. In Europe, the death toll was 30–60% of the entire population. Florence went from 110,000 people to perhaps 50,000. England's population would not recover to pre-plague levels until the 16th century — almost 200 years later.</p><blockquote><p>"So many have died that everyone thinks it is the end of the world." — Agnolo di Tura of Siena, who buried five of his children with his own hands.</p></blockquote><h2>The Accidental Modernity</h2><p>The paradox of the Black Death: the catastrophe helped create the modern world. With one-third of the workforce dead, surviving peasants could demand higher wages. Serfdom declined. The Church's failure to explain or prevent the plague opened space for religious questioning that contributed to the Protestant Reformation. Boccaccio wrote the Decameron in Italian, not Latin. Venice established the first quarantine system in 1377 — the word "quarantine" comes from the Italian for forty days.</p>`,
        featuredImage: 'https://images.unsplash.com/photo-1578496480157-697fc14d2e55?w=1200&q=80',
        status: PostStatus.PUBLISHED, authorId: 1, authorName: 'Site Admin',
        readTime: 10, views: 1421, category: history,
        tags: [tagMap['medieval'], tagMap['civilization'], tagMap['history-of-science']],
      },
    ]);

    // Science posts
    await this.postRepo.save([
      {
        title: 'How Black Holes Work: Event Horizons, Singularities, and Hawking Radiation',
        slug: 'how-black-holes-work-event-horizons-hawking-radiation',
        excerpt: 'Black holes are regions of spacetime where gravity is so intense that nothing — not even light — can escape. But they\'re far stranger than that simple definition suggests.',
        content: `<h2>What Is a Black Hole?</h2><p>A black hole is a region of spacetime where gravity has become so extreme that the escape velocity exceeds the speed of light. This boundary is called the <strong>event horizon</strong>. But black holes are not vacuum cleaners — they don't suck in matter any more than any other massive object. If the Sun were replaced with a black hole of the same mass, Earth's orbit would be completely unchanged.</p><h2>The Anatomy of a Black Hole</h2><p>At the center exists a singularity — a point of infinite density where the curvature of spacetime becomes infinite. The Schwarzschild radius defines the event horizon for a non-rotating black hole:</p><pre><code>r_s = 2GM / c²

For Earth:  r_s ≈ 9 mm
For the Sun: r_s ≈ 3 km
For a 10 solar-mass black hole: r_s ≈ 30 km</code></pre><h2>Hawking Radiation</h2><p>In 1974, Stephen Hawking predicted that black holes slowly emit thermal radiation and lose mass over time. At the event horizon, one particle of a virtual pair can fall in while the other escapes — carrying energy away from the black hole. A stellar black hole of 10 solar masses would take roughly 2 × 10⁶⁷ years to evaporate, far longer than the current age of the universe.</p><blockquote><p>In April 2019, the Event Horizon Telescope released the first image of a black hole — the supermassive black hole at the center of galaxy M87. Einstein himself had doubted they could physically exist. The universe had other ideas.</p></blockquote>`,
        featuredImage: 'https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=1200&q=80',
        status: PostStatus.PUBLISHED, authorId: 1, authorName: 'Site Admin',
        readTime: 9, views: 2089, category: quantum,
        tags: [tagMap['physics'], tagMap['space'], tagMap['quantum-mechanics']],
      },
      {
        title: 'CRISPR Explained: The Gene Editing Revolution That Could Change Medicine',
        slug: 'crispr-gene-editing-revolution-explained',
        excerpt: 'CRISPR-Cas9 lets scientists edit DNA with unprecedented precision. It has already shown promise against sickle cell disease and some cancers — but raises profound ethical questions.',
        content: `<h2>From Bacterial Immunity to Nobel Prize</h2><p>In the 1980s and 1990s, microbiologists noticed strange repetitive sequences in bacterial DNA — Clustered Regularly Interspaced Short Palindromic Repeats, or CRISPR. It turned out they were bacterial memory: stored snippets of defeated viruses. In 2012, Jennifer Doudna and Emmanuelle Charpentier showed this system could be repurposed as a precise gene-editing tool. In 2020, they received the Nobel Prize in Chemistry.</p><h2>How It Works</h2><ol><li>A guide RNA is designed to match the target sequence in the genome</li><li>The gRNA-Cas9 complex searches the genome for a matching sequence</li><li>When found, Cas9 cuts both strands of the DNA double helix</li><li>The cell repairs the break — either deleting base pairs or accepting new genetic material</li></ol><blockquote><p>CRISPR edits DNA with the precision of a word processor's find-and-replace — but for the three billion base pairs of the human genome.</p></blockquote><h2>What It Has Already Achieved</h2><p>In December 2023, the FDA approved Casgevy — the first CRISPR-based medicine, treating sickle cell disease. Early trial results showed patients essentially cured: free from the severe pain crises that had defined their lives. CRISPR-edited crops are also on the market: disease-resistant wheat, higher-yield tomatoes, mushrooms that don't brown.</p><h2>The Ethical Frontier</h2><p>In 2018, Chinese scientist He Jiankui shocked the world by announcing births of twins whose embryonic DNA he had edited with CRISPR. He was sentenced to three years in prison. The questions CRISPR forces remain hard: where is the line between treating disease and enhancement? Who should access gene therapies priced at $2.2 million per patient?</p>`,
        featuredImage: 'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=1200&q=80',
        status: PostStatus.PUBLISHED, authorId: 1, authorName: 'Site Admin',
        readTime: 8, views: 1567, category: quantum,
        tags: [tagMap['physics'], tagMap['explainer'], tagMap['ai']],
      },
      {
        title: 'Quantum Entanglement: When Particles Share a Fate Across Any Distance',
        slug: 'quantum-entanglement-explained',
        excerpt: 'Quantum entanglement is one of the strangest verified facts in all of science: two particles can be correlated in ways that no classical explanation can account for, regardless of distance.',
        content: `<h2>Einstein Called It "Spooky Action at a Distance"</h2><p>In 1935, Einstein, Podolsky, and Rosen published a paper intended to show that quantum mechanics must be incomplete. They described particles whose quantum states are correlated regardless of distance. Einstein believed there must be "hidden variables" — pre-set properties that determined outcomes in advance. He was wrong. Experiment has proven it, definitively and repeatedly.</p><h2>What Entanglement Actually Is</h2><p>Two entangled photons, each in a superposition of vertical or horizontal polarization. When you measure one and find it vertically polarized, you instantly know its partner will be horizontally polarized — even if it's across the galaxy. Bell's theorem (1964) and subsequent experiments (the 2022 Nobel Prize-winning work of Alain Aspect, John Clauser, and Anton Zeilinger) proved that no hidden variable explanation can account for the observed correlations.</p><h2>Does This Allow Faster-Than-Light Communication?</h2><p>No. When you measure your entangled particle, you get a random result. You cannot control the outcome. The correlation is only visible after-the-fact comparison via a classical channel, limited to the speed of light. Special relativity remains intact.</p><h2>Real-World Applications</h2><p>Entanglement enables quantum key distribution — cryptographic methods where any eavesdropping attempt is physically detectable. Quantum computers use entangled qubits to perform certain calculations exponentially faster than classical computers. Shor's algorithm (1994) demonstrated a sufficiently large quantum computer could factor large numbers efficiently — breaking RSA encryption.</p><blockquote><p>Quantum mechanics is not only stranger than you suppose; it is stranger than you can suppose.</p></blockquote>`,
        featuredImage: 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=1200&q=80',
        status: PostStatus.PUBLISHED, authorId: 1, authorName: 'Site Admin',
        readTime: 10, views: 1892, category: quantum,
        tags: [tagMap['physics'], tagMap['quantum-mechanics'], tagMap['entanglement']],
      },
    ]);

    // Knowledge posts
    await this.postRepo.save([
      {
        title: 'The Feynman Technique: Learn Anything Faster by Teaching It',
        slug: 'feynman-technique-learn-faster-teaching',
        excerpt: 'Richard Feynman was one of the greatest physicists of the 20th century and also one of its greatest teachers. His approach to learning reveals a universal truth: if you can\'t explain it simply, you don\'t understand it yet.',
        content: `<h2>The Four Steps</h2><p>Richard Feynman won the Nobel Prize in Physics in 1965. Colleagues noted something unusual: he seemed to understand physics at an almost physical, intuitive level. His secret was a specific approach to learning that treats understanding as binary — either you can explain it simply, or you don't understand it yet.</p><h3>Step 1: Choose a Concept and Study It</h3><p>Study it using primary sources. Read the chapter, watch the lecture, work through the examples.</p><h3>Step 2: Teach It to a Child</h3><p>Write the concept's name at the top of a blank page. Explain it in plain language as if teaching someone with no background. No jargon allowed.</p><blockquote><p>"If you can't explain it simply, you don't understand it well enough."</p></blockquote><h3>Step 3: Identify Gaps and Go Back to Source</h3><p>Wherever your explanation broke down — wherever you wrote "and somehow this leads to..." — return to your source material. You've identified precisely what you don't understand.</p><h3>Step 4: Simplify and Use Analogies</h3><p>Once you can explain something clearly, make it more concise and vivid. Find analogies — comparisons to things your student already knows. Feynman was a master: electrical resistance as water flowing through a narrow pipe; quantum amplitude as a rotating arrow.</p><h2>Why This Works</h2><p>The Feynman Technique forces you to confront the difference between recognition and recall. Reading triggers recognition — things feel comprehensible. But genuine understanding requires recall — reconstructing the concept from scratch. Teaching forces recall. It also eliminates the "illusion of explanatory depth" — the well-documented bias where people systematically overestimate how well they understand complex systems.</p>`,
        featuredImage: 'https://images.unsplash.com/photo-1456406644174-8ddd4cd52a06?w=1200&q=80',
        status: PostStatus.PUBLISHED, authorId: 1, authorName: 'Site Admin',
        readTime: 7, views: 3241, category: educational,
        tags: [tagMap['explainer'], tagMap['physics'], tagMap['history-of-science']],
      },
      {
        title: "Charlie Munger's Mental Models: A Framework for Clearer Thinking",
        slug: 'mental-models-charlie-munger-framework',
        excerpt: 'Charlie Munger built one of the greatest investment records in history by thinking across disciplines. His latticework of mental models is the most practical framework for improving how you reason.',
        content: `<h2>The Idea</h2><p>Charlie Munger, Warren Buffett's partner at Berkshire Hathaway, believes most people think too narrowly — they apply one field's tools to every problem. He calls this the "man with a hammer" problem. His solution is a "latticework of mental models" — the most powerful ideas from across multiple disciplines, applied as the situation demands.</p><blockquote><p>"You must know the big ideas in the big disciplines and use them routinely. All the time. In combination." — Charlie Munger</p></blockquote><h2>The Most Powerful Models</h2><h3>Compound Interest (Mathematics)</h3><p>Compounding describes any situation where growth builds on prior growth: knowledge, relationships, skills. The implication: start earlier, be patient, never interrupt compounding unnecessarily.</p><h3>Critical Mass (Physics)</h3><p>The minimum amount needed for a self-sustaining reaction. Applies to: social network growth, skill acquisition, organizational culture. Effort below critical mass is often wasted; above it, things suddenly accelerate.</p><h3>Incentive-Caused Bias (Psychology)</h3><p>People reliably rationalize behaviors that serve their interests, largely unconsciously. As Munger puts it: "Never ask a barber if you need a haircut." Always ask: what are the incentives of the people involved?</p><h3>Regression to the Mean (Statistics)</h3><p>Extreme outcomes tend to be followed by less extreme outcomes, because extreme outcomes are partly caused by extreme luck. Failing to account for this causes systematic errors in evaluation and prediction.</p><h2>How to Build Your Latticework</h2><ol><li>Read broadly across disciplines — history, biology, physics, psychology, economics</li><li>Identify the core idea each field has discovered</li><li>Practice applying models outside their home domain</li><li>Build your list explicitly — write down the models and review them</li></ol>`,
        featuredImage: 'https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=1200&q=80',
        status: PostStatus.PUBLISHED, authorId: 1, authorName: 'Site Admin',
        readTime: 8, views: 2789, category: educational,
        tags: [tagMap['explainer'], tagMap['physics'], tagMap['ai']],
      },
      {
        title: 'Deep Work: Achieving Extraordinary Focus in a Distracted World',
        slug: 'deep-work-achieving-focus-distracted-world',
        excerpt: 'Cal Newport\'s concept of deep work — professional activities performed in a state of distraction-free concentration — may be the most valuable skill you can develop in the modern economy.',
        content: `<h2>The Problem</h2><p>Knowledge workers today face a paradox: we have access to more information and more powerful tools than any previous generation, yet it's harder than ever to produce work of genuine depth. Email, Slack, meetings, and social media have created an environment where sustained concentration is increasingly rare — and increasingly valuable.</p><h2>Deep Work vs Shallow Work</h2><p>Deep work: professional activities performed in distraction-free concentration that push your cognitive capabilities to their limit. Shallow work: non-cognitively demanding, logistical tasks often performed while distracted — email, scheduling, routine meetings.</p><blockquote><p>A deep work session for a programmer might produce an elegant algorithm that would take a week of shallow, interrupted work. A writer doing deep work for four hours might produce the same quality prose that would take three fragmented days otherwise.</p></blockquote><h2>The Four Philosophies</h2><ul><li><strong>Monastic</strong> — Eliminate all shallow obligations (Donald Knuth has no email address)</li><li><strong>Bimodal</strong> — Divide time into deep and shallow periods (Bill Gates's "Think Weeks")</li><li><strong>Rhythmic</strong> — Block the same hours every day for focused work (most practical for most people)</li><li><strong>Journalistic</strong> — Switch into deep work whenever a block of time appears (requires practice)</li></ul><h2>The 4-Hour Limit</h2><p>Deliberate practice research suggests experts rarely sustain more than four hours of intense focus per day. You don't need eight hours of deep work. You need four good hours, protected from distraction, done consistently. A person who produces four hours of genuinely focused work daily will, over months and years, compound their skills and output in ways not available to someone doing the same clock hours but fragmented across constant interruptions.</p>`,
        featuredImage: 'https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1200&q=80',
        status: PostStatus.PUBLISHED, authorId: 1, authorName: 'Site Admin',
        readTime: 9, views: 3890, category: educational,
        tags: [tagMap['explainer'], tagMap['ai'], tagMap['machine-learning']],
      },
    ]);

    console.log('Blog seeded with sample posts!');
  }
}
