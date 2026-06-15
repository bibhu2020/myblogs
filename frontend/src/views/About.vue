<script setup>
import { RouterLink } from 'vue-router'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import { useLayoutStore } from '../stores/layout'

const layout = useLayoutStore()

const mcpCapabilities = [
  { label: 'Publish & manage posts', desc: 'create, update, delete, and query blog articles with full metadata' },
  { label: 'User management', desc: 'create guest authors, update profiles, and manage roles programmatically' },
  { label: 'Content discovery', desc: 'list posts, search by keyword or tag, filter by category or date range' },
  { label: 'Taxonomy control', desc: 'create and assign categories and tags to organise the content graph' },
  { label: 'Media operations', desc: 'upload images and retrieve media records tied to any post' },
]

const maintenanceItems = [
  {
    icon: '🔒',
    title: 'Security Patching',
    desc: 'AI agents periodically audit dependencies and application code for known vulnerabilities, apply patches, and verify fixes before redeployment.',
  },
  {
    icon: '🔍',
    title: 'SEO Compliance',
    desc: 'Automated checks ensure every post carries correct meta tags, structured data, canonical URLs, and sitemap entries to maximise search visibility.',
  },
  {
    icon: '♿',
    title: 'ADA / WCAG Compliance',
    desc: 'Accessibility scans flag missing alt text, low-contrast elements, and keyboard-navigation gaps — then AI applies the corrections automatically.',
  },
]

const rebrandAgents = [
  { name: 'IdeationAgent', icon: '💡', desc: 'Researches world events, picks a cultural theme, and generates a complete color palette and banner copy.' },
  { name: 'CodingAgent', icon: '⌨️', desc: 'Applies the plan to CSS variables, Navbar, Home, Footer, and index.html — no human commits.' },
  { name: 'ReviewerAgent', icon: '🔎', desc: 'Enforces WCAG AA contrast (≥ 4.5:1), checks alt text, ARIA labels, focus styles, and SEO tags. Routes failures back upstream.' },
  { name: 'TesterAgent', icon: '🧪', desc: 'Runs the Vite production build and seven structural checks. Sends build failures back to CodingAgent.' },
  { name: 'PublisherAgent', icon: '🚀', desc: 'Stages, commits, rebases, and pushes to GitHub only after all checks pass.' },
]

const approvalSteps = [
  { step: '1', label: 'Research & Write', desc: 'Agent discovers a trending topic, deep-researches it, writes a 2 000+ word post, and sources a featured image.' },
  { step: '2', label: 'Save as Pending', desc: 'The finished post is stored with status "pending" — invisible to readers until an admin acts.' },
  { step: '3', label: 'Admin Reviews', desc: 'The Pending Approval tab in the admin panel shows the full post with Approve and Reject buttons.' },
  { step: '4', label: 'Publish or Discard', desc: 'Approve promotes the post to "published". Reject deletes it permanently. Either action can also be taken from the CLI.' },
]

const recentFeatures = [
  { icon: '📰', label: 'AI News Agent', desc: 'Daily headlines from 20+ RSS feeds across 4 regions, curated and summarised by Gemini.' },
  { icon: '✨', label: 'Gemini Image Enhancement', desc: 'All news thumbnails are sharpened and upscaled by Gemini before being stored locally.' },
  { icon: '📖', label: 'Story Corner', desc: 'Weekly AI-written children\'s stories for ages 8–15 with AI-generated illustrated thumbnails.' },
  { icon: '🔊', label: 'Text-to-Speech', desc: 'Every post and news story streams as audio via a progressive built-in TTS player.' },
]

const newsRegions = [
  { flag: '🌍', label: 'World', sources: 'BBC World, CNN, The Guardian, Al Jazeera' },
  { flag: '🇺🇸', label: 'USA', sources: 'BBC US & Canada, CNN US, NPR' },
  { flag: '🇮🇳', label: 'India', sources: 'NDTV, Times of India, The Hindu' },
  { flag: '🏛️', label: 'Odisha', sources: 'OTV, Pragativadi, The Hindu Odisha' },
]
</script>

<template>
  <!-- ═══════════════════════════ LAYOUT A — Light ═══════════════════════════ -->
  <div v-if="layout.variant === 'a'" class="min-h-screen bg-white">
    <Navbar />

    <!-- Hero -->
    <section class="bg-gradient-to-br from-primary-50 via-white to-purple-50 border-b border-gray-100">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        <span class="inline-block bg-primary-100 text-primary-700 text-xs font-bold uppercase tracking-widest px-4 py-1.5 rounded-full mb-6">About Meridian</span>
        <h1 class="text-4xl sm:text-5xl font-black text-gray-900 leading-tight mb-6" style="font-family:'Playfair Display',serif">
          A Blog Fully Conceived,<br class="hidden sm:block" /> Run, and Maintained by AI
        </h1>
        <p class="text-lg text-gray-600 leading-relaxed max-w-2xl mx-auto">
          Meridian is not a typical blog. From the first line of code to the latest published post, every layer of this platform is designed, operated, and evolved by artificial intelligence — with a human visionary behind the idea.
        </p>
      </div>
    </section>

    <!-- Recent Additions strip -->
    <div class="bg-gradient-to-r from-primary-600 to-violet-600 text-white">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <p class="text-xs font-bold uppercase tracking-widest text-white/70 mb-4">Recent Additions</p>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div v-for="f in recentFeatures" :key="f.label" class="flex gap-3 items-start">
            <span class="text-2xl flex-shrink-0">{{ f.icon }}</span>
            <div>
              <div class="font-bold text-sm leading-snug">{{ f.label }}</div>
              <div class="text-white/70 text-xs leading-snug mt-0.5">{{ f.desc }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-20">

      <!-- AI-Created & AI-Managed -->
      <section>
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-primary-600 flex items-center justify-center text-white text-xl">🤖</div>
          <h2 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">AI-Created &amp; AI-Managed</h2>
        </div>
        <div class="prose prose-gray max-w-none text-gray-600 leading-relaxed space-y-4">
          <p>
            Meridian was designed and built entirely by AI — from architecture decisions to component code, database schema to deployment pipeline. No human wrote a line of application code. The stack (Vue 3 frontend, four NestJS microservices, SQLite databases) was specified, scaffolded, and wired together through an AI-driven development session guided by the platform's ideator.
          </p>
          <p>
            Day-to-day operation is equally autonomous. AI agents handle the full content lifecycle: researching trending topics, writing articles grounded in live web data, selecting featured images, assigning categories and tags, and saving posts for human review before they go live — blending autonomous generation with intentional editorial oversight.
          </p>
        </div>
      </section>

      <!-- MCP Endpoints -->
      <section>
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center text-white text-xl">🔌</div>
          <h2 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">MCP-Enabled for External Agents</h2>
        </div>
        <div class="prose prose-gray max-w-none text-gray-600 leading-relaxed space-y-4">
          <p>
            Meridian exposes a full suite of <strong>Model Context Protocol (MCP) endpoints</strong> — a standard interface that lets external AI agents interact with the platform programmatically. Any MCP-compatible agent can connect and perform actions such as:
          </p>
          <ul class="list-none space-y-3 mt-4">
            <li v-for="cap in mcpCapabilities" :key="cap.label" class="flex items-start gap-3">
              <span class="mt-0.5 w-6 h-6 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-bold flex-shrink-0">✓</span>
              <div>
                <span class="font-semibold text-gray-800">{{ cap.label }}</span>
                <span class="text-gray-500"> — {{ cap.desc }}</span>
              </div>
            </li>
          </ul>
          <p class="mt-4">
            This open-agent architecture means Meridian can be extended, contributed to, and supervised by any AI system that speaks MCP — making it a living node in a broader agentic ecosystem.
          </p>
        </div>
      </section>

      <!-- AI Maintenance -->
      <section>
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-green-600 flex items-center justify-center text-white text-xl">🛡️</div>
          <h2 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">AI-Driven Maintenance</h2>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div v-for="item in maintenanceItems" :key="item.title" class="bg-gray-50 rounded-2xl p-6 border border-gray-100">
            <div class="text-3xl mb-3">{{ item.icon }}</div>
            <h3 class="font-bold text-gray-900 mb-2">{{ item.title }}</h3>
            <p class="text-gray-500 text-sm leading-relaxed">{{ item.desc }}</p>
          </div>
        </div>
      </section>

      <!-- Human-in-the-Loop Post Approval -->
      <section>
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-teal-600 flex items-center justify-center text-white text-xl">⏸️</div>
          <h2 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Human-in-the-Loop Post Approval</h2>
        </div>
        <div class="prose prose-gray max-w-none text-gray-600 leading-relaxed mb-8">
          <p>
            AI-generated posts don't go live automatically. Every article the Post Agent produces lands in a <strong>Pending Approval</strong> queue first, giving the admin full editorial control over what reaches readers — without slowing down the generation pipeline.
          </p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div v-for="s in approvalSteps" :key="s.step" class="flex gap-4 bg-teal-50 border border-teal-100 rounded-2xl p-5">
            <div class="w-8 h-8 rounded-full bg-teal-600 text-white text-sm font-bold flex items-center justify-center flex-shrink-0">{{ s.step }}</div>
            <div>
              <div class="font-semibold text-gray-900 mb-1">{{ s.label }}</div>
              <p class="text-gray-500 text-sm leading-relaxed">{{ s.desc }}</p>
            </div>
          </div>
        </div>
        <p class="text-gray-500 text-sm mt-5 leading-relaxed">
          The same approve / reject actions are available in the admin panel at <RouterLink to="/admin/posts" class="text-primary-600 hover:underline font-medium">/admin/posts</RouterLink> (Pending Approval tab) or via the CLI: <code class="bg-gray-100 px-2 py-0.5 rounded text-xs font-mono">python3 -m meridian_agents.post_agent approve &lt;id&gt;</code>.
        </p>
      </section>

      <!-- Multi-Agent Rebranding Pipeline -->
      <section>
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 rounded-xl bg-amber-500 flex items-center justify-center text-white text-xl">🎨</div>
          <h2 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Monthly AI Rebranding</h2>
        </div>
        <p class="text-gray-500 text-sm mb-6 ml-13">Five specialized agents collaborate every month to keep Meridian visually in step with the world.</p>
        <div class="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-100 rounded-2xl p-8 mb-8">
          <p class="text-gray-700 leading-relaxed mb-4">
            Every month, an AI agent surveys the global landscape — major sporting events, cultural milestones, scientific breakthroughs, seasonal celebrations — and rebrands Meridian to reflect the moment. Color themes, hero banners, holiday badges, and editorial tone shift to stay culturally resonant and visually fresh.
          </p>
          <p class="text-gray-600 text-sm leading-relaxed">
            This month, for example, the platform wears the colors of <strong>FIFA World Cup 2026</strong>. Next month it will wear something new. The world changes; Meridian keeps up — automatically.
          </p>
        </div>

        <!-- Agent pipeline cards -->
        <h3 class="font-bold text-gray-800 mb-4 text-sm uppercase tracking-widest">The Five-Agent Pipeline</h3>
        <div class="space-y-3">
          <div v-for="(agent, i) in rebrandAgents" :key="agent.name" class="flex gap-4 items-start">
            <div class="flex flex-col items-center flex-shrink-0">
              <div class="w-9 h-9 rounded-xl bg-white border-2 border-amber-200 flex items-center justify-center text-lg">{{ agent.icon }}</div>
              <div v-if="i < rebrandAgents.length - 1" class="w-0.5 h-5 bg-amber-200 mt-1"></div>
            </div>
            <div class="pb-2">
              <span class="font-bold text-gray-900 text-sm">{{ agent.name }}</span>
              <p class="text-gray-500 text-sm leading-relaxed mt-0.5">{{ agent.desc }}</p>
            </div>
          </div>
        </div>
        <div class="mt-6 bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-gray-600 leading-relaxed">
          <strong class="text-amber-700">Self-correcting loops:</strong> If ReviewerAgent finds a WCAG AA contrast failure (ratio &lt; 4.5:1), it hands back to IdeationAgent for a palette revision. Markup or ARIA issues route to CodingAgent. Build failures send TesterAgent back to CodingAgent. The pipeline allows up to three revision cycles before committing.
        </div>
      </section>

      <!-- AI News Agent -->
      <section>
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-slate-700 flex items-center justify-center text-white text-xl">📰</div>
          <h2 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">AI News Agent</h2>
        </div>
        <div class="prose prose-gray max-w-none text-gray-600 leading-relaxed space-y-4 mb-8">
          <p>
            Meridian's <strong>News Agent</strong> runs every 12 hours and autonomously aggregates, curates, and publishes the day's top stories — no human editor required. Powered by <strong>Gemini 2.5 Flash</strong>, it pulls from over 20 live RSS feeds, selects 10 stories across four regions, writes a crisp 100-word neutral summary for each, and saves them directly to the platform.
          </p>
          <p>
            Before saving, every thumbnail is downloaded, sent to <strong>Gemini's image-enhancement model</strong> to sharpen focus and improve clarity, and then uploaded to Meridian's own media service — replacing low-resolution news thumbnails with locally-hosted, high-quality images. The News page also features a built-in <strong>text-to-speech player</strong> that can read all stories aloud in sequence.
          </p>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <div v-for="r in newsRegions" :key="r.label" class="bg-gray-50 border border-gray-100 rounded-2xl p-4">
            <div class="text-2xl mb-2">{{ r.flag }}</div>
            <div class="font-bold text-gray-900 text-sm mb-1">{{ r.label }}</div>
            <div class="text-gray-400 text-xs leading-snug">{{ r.sources }}</div>
          </div>
        </div>
        <div class="bg-slate-50 border border-slate-100 rounded-xl p-4 text-sm text-gray-600 leading-relaxed">
          <strong class="text-slate-800">How it works:</strong> RSS feeds → Gemini curates 10 stories + writes summaries → og:image fallback scraping for articles missing thumbnails → Gemini image enhancement → upload to media service → published to the News page. Schedule: <code class="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono">0 6,18 * * *</code> UTC.
        </div>
      </section>

      <!-- Story Corner -->
      <section>
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-rose-500 flex items-center justify-center text-white text-xl">📖</div>
          <h2 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Story Corner</h2>
        </div>
        <div class="prose prose-gray max-w-none text-gray-600 leading-relaxed space-y-4 mb-6">
          <p>
            Every week, the <strong>Story Agent</strong> writes an original children's story for readers aged 8–15. Each story is crafted by Gemini to be imaginative, age-appropriate, and engaging — with a distinct narrative arc, memorable characters, and a gentle moral. A matching illustrated thumbnail is generated via AI image synthesis (Imagen 4 / FLUX.1) and uploaded alongside the story.
          </p>
          <p>
            Stories live in their own <strong>Story Corner</strong> section, separate from the main blog feed. Like blog posts, they can be listened to with the built-in TTS player — making them accessible even for younger readers who prefer to hear rather than read.
          </p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="bg-rose-50 border border-rose-100 rounded-2xl p-5">
            <div class="text-2xl mb-2">🎯</div>
            <div class="font-bold text-gray-900 text-sm mb-1">Audience</div>
            <p class="text-gray-500 text-xs leading-relaxed">Written for ages 8–15 with vocabulary and themes calibrated to the target age group.</p>
          </div>
          <div class="bg-rose-50 border border-rose-100 rounded-2xl p-5">
            <div class="text-2xl mb-2">🖼️</div>
            <div class="font-bold text-gray-900 text-sm mb-1">AI Illustrations</div>
            <p class="text-gray-500 text-xs leading-relaxed">Each story gets a unique cover image generated by Imagen 4 or FLUX.1 and stored in the media service.</p>
          </div>
          <div class="bg-rose-50 border border-rose-100 rounded-2xl p-5">
            <div class="text-2xl mb-2">🔊</div>
            <div class="font-bold text-gray-900 text-sm mb-1">Listen Mode</div>
            <p class="text-gray-500 text-xs leading-relaxed">Every story streams as audio via the same TTS engine used for blog posts and news.</p>
          </div>
        </div>
      </section>

      <!-- System Design Download -->
      <section>
        <div class="bg-gradient-to-r from-primary-50 to-violet-50 border border-primary-100 rounded-2xl p-8 flex flex-col sm:flex-row items-center gap-6">
          <div class="w-14 h-14 rounded-2xl bg-primary-600 flex items-center justify-center text-white text-2xl flex-shrink-0">📊</div>
          <div class="flex-1 text-center sm:text-left">
            <h3 class="text-lg font-bold text-gray-900 mb-1" style="font-family:'Playfair Display',serif">System Design Document</h3>
            <p class="text-gray-500 text-sm leading-relaxed">22-slide deep dive into Meridian's architecture — service topology, 14 annotated sequence diagrams covering every major user flow, technology stack, and future roadmap.</p>
          </div>
          <a href="/myblogs.pdf" download="myblogs.pdf"
             class="flex-shrink-0 inline-flex items-center gap-2 bg-primary-600 text-white px-6 py-3 rounded-full text-sm font-semibold hover:bg-primary-700 transition-colors shadow-sm">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            Download PDF
          </a>
        </div>
      </section>

      <!-- Divider -->
      <div class="border-t border-gray-200"></div>

      <!-- Ideator -->
      <section id="ideator">
        <div class="text-center mb-10">
          <span class="inline-block bg-gray-100 text-gray-600 text-xs font-bold uppercase tracking-widest px-4 py-1.5 rounded-full mb-4">The Human Behind the Vision</span>
          <h2 class="text-3xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Meet the Ideator</h2>
        </div>
        <div class="bg-gray-50 rounded-3xl border border-gray-100 p-8 sm:p-12 flex flex-col sm:flex-row gap-8 items-start">
          <div class="flex-shrink-0">
            <img :src="'/bibhu.jpg'" alt="Bibhu Mishra" class="w-24 h-24 rounded-2xl object-cover object-top shadow-md" />
          </div>
          <div class="flex-1">
            <h3 class="text-2xl font-bold text-gray-900 mb-1" style="font-family:'Playfair Display',serif">Bibhu Mishra</h3>
            <p class="text-primary-600 font-semibold mb-1">Principal Cloud / DevOps Architect</p>
            <p class="text-gray-500 text-sm mb-5">Azure &amp; Kubernetes · MLOps · DevOps &amp; Cloud Transformation · LTIMindtree</p>

            <div class="prose prose-gray max-w-none text-gray-600 text-sm leading-relaxed space-y-3">
              <p>
                Bibhu is a seasoned technology leader with over 18 years of experience at the intersection of cloud infrastructure, DevOps, and applied AI. He specializes in Azure cloud architecture and Kubernetes-based platforms, and has led large-scale migrations of major web properties — including Microsoft.com news and blogging products — to Azure Kubernetes Services.
              </p>
              <p>
                Meridian was born from Bibhu's conviction that AI should not just assist developers — it should <em>be</em> the developer. This platform is his proof of concept: a fully autonomous, AI-built, AI-operated publication that demonstrates what is possible when you put an agent in the driver's seat from day one.
              </p>
              <p>
                Beyond architecture, Bibhu is a practitioner of MLOps and cloud-native transformation, driving innovation and operational efficiency for enterprise clients. His work sits at the frontier of AI-enabled infrastructure.
              </p>
            </div>

            <div class="mt-6 flex flex-wrap gap-3">
              <a
                href="https://www.linkedin.com/in/mishrab"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-2 bg-[#0A66C2] text-white px-5 py-2.5 rounded-full text-sm font-semibold hover:bg-[#004182] transition-colors"
              >
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                LinkedIn Profile
              </a>
              <span class="inline-flex items-center gap-2 bg-gray-100 text-gray-700 px-5 py-2.5 rounded-full text-sm font-medium">
                🔧 Azure · Kubernetes · MLOps · DevOps
              </span>
            </div>
          </div>
        </div>
      </section>

    </div>

    <Footer />
  </div>

  <!-- ═══════════════════════════ LAYOUT B — Dark ════════════════════════════ -->
  <div v-else class="min-h-screen bg-[#0f172a] text-slate-200">
    <Navbar />

    <!-- Hero -->
    <section class="border-b border-[#2d3f5f]">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        <span class="inline-block bg-violet-950 text-violet-400 text-xs font-bold uppercase tracking-widest px-4 py-1.5 rounded-full border border-violet-900 mb-6">About Meridian</span>
        <h1 class="text-4xl sm:text-5xl font-black text-white leading-tight mb-6" style="font-family:'Playfair Display',serif">
          A Blog Fully Conceived,<br class="hidden sm:block" /> Run, and Maintained by AI
        </h1>
        <p class="text-lg text-slate-400 leading-relaxed max-w-2xl mx-auto">
          Meridian is not a typical blog. From the first line of code to the latest published post, every layer of this platform is designed, operated, and evolved by artificial intelligence — with a human visionary behind the idea.
        </p>
      </div>
    </section>

    <!-- Recent Additions strip -->
    <div class="bg-gradient-to-r from-violet-900/60 to-primary-900/60 border-b border-violet-900/40">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <p class="text-xs font-bold uppercase tracking-widest text-slate-500 mb-4">Recent Additions</p>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div v-for="f in recentFeatures" :key="f.label" class="flex gap-3 items-start">
            <span class="text-2xl flex-shrink-0">{{ f.icon }}</span>
            <div>
              <div class="font-bold text-slate-200 text-sm leading-snug">{{ f.label }}</div>
              <div class="text-slate-500 text-xs leading-snug mt-0.5">{{ f.desc }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-20">

      <!-- AI-Created & AI-Managed -->
      <section>
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-violet-700 flex items-center justify-center text-white text-xl">🤖</div>
          <h2 class="text-2xl font-bold text-white" style="font-family:'Playfair Display',serif">AI-Created &amp; AI-Managed</h2>
        </div>
        <div class="text-slate-400 leading-relaxed space-y-4">
          <p>
            Meridian was designed and built entirely by AI — from architecture decisions to component code, database schema to deployment pipeline. No human wrote a line of application code. The stack (Vue 3 frontend, four NestJS microservices, SQLite databases) was specified, scaffolded, and wired together through an AI-driven development session guided by the platform's ideator.
          </p>
          <p>
            Day-to-day operation is equally autonomous. AI agents handle the full content lifecycle: researching trending topics, writing articles grounded in live web data, selecting featured images, assigning categories and tags, and saving posts for human review before they go live — blending autonomous generation with intentional editorial oversight.
          </p>
        </div>
      </section>

      <!-- MCP Endpoints -->
      <section>
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center text-white text-xl">🔌</div>
          <h2 class="text-2xl font-bold text-white" style="font-family:'Playfair Display',serif">MCP-Enabled for External Agents</h2>
        </div>
        <div class="text-slate-400 leading-relaxed space-y-4">
          <p>
            Meridian exposes a full suite of <span class="text-violet-300 font-semibold">Model Context Protocol (MCP) endpoints</span> — a standard interface that lets external AI agents interact with the platform programmatically. Any MCP-compatible agent can connect and perform actions such as:
          </p>
          <ul class="space-y-3 mt-4">
            <li v-for="cap in mcpCapabilities" :key="cap.label" class="flex items-start gap-3">
              <span class="mt-0.5 w-6 h-6 rounded-full bg-violet-950 border border-violet-800 text-violet-400 flex items-center justify-center text-xs font-bold flex-shrink-0">✓</span>
              <div>
                <span class="font-semibold text-slate-200">{{ cap.label }}</span>
                <span class="text-slate-400"> — {{ cap.desc }}</span>
              </div>
            </li>
          </ul>
          <p class="mt-4">
            This open-agent architecture means Meridian can be extended, contributed to, and supervised by any AI system that speaks MCP — making it a living node in a broader agentic ecosystem.
          </p>
        </div>
      </section>

      <!-- AI Maintenance -->
      <section>
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-emerald-700 flex items-center justify-center text-white text-xl">🛡️</div>
          <h2 class="text-2xl font-bold text-white" style="font-family:'Playfair Display',serif">AI-Driven Maintenance</h2>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div v-for="item in maintenanceItems" :key="item.title" class="bg-[#162236] rounded-2xl p-6 border border-[#2d3f5f]">
            <div class="text-3xl mb-3">{{ item.icon }}</div>
            <h3 class="font-bold text-slate-100 mb-2">{{ item.title }}</h3>
            <p class="text-slate-400 text-sm leading-relaxed">{{ item.desc }}</p>
          </div>
        </div>
      </section>

      <!-- Human-in-the-Loop Post Approval -->
      <section>
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-teal-700 flex items-center justify-center text-white text-xl">⏸️</div>
          <h2 class="text-2xl font-bold text-white" style="font-family:'Playfair Display',serif">Human-in-the-Loop Post Approval</h2>
        </div>
        <div class="text-slate-400 leading-relaxed mb-8">
          <p>
            AI-generated posts don't go live automatically. Every article the Post Agent produces lands in a <span class="text-teal-400 font-semibold">Pending Approval</span> queue first, giving the admin full editorial control over what reaches readers — without slowing down the generation pipeline.
          </p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div v-for="s in approvalSteps" :key="s.step" class="flex gap-4 bg-[#0d2a28] border border-teal-900/50 rounded-2xl p-5">
            <div class="w-8 h-8 rounded-full bg-teal-700 text-white text-sm font-bold flex items-center justify-center flex-shrink-0">{{ s.step }}</div>
            <div>
              <div class="font-semibold text-slate-200 mb-1">{{ s.label }}</div>
              <p class="text-slate-400 text-sm leading-relaxed">{{ s.desc }}</p>
            </div>
          </div>
        </div>
        <p class="text-slate-500 text-sm mt-5 leading-relaxed">
          The same approve / reject actions are available in the admin panel (Pending Approval tab) or via the CLI: <code class="bg-slate-800 px-2 py-0.5 rounded text-xs font-mono text-teal-400">python3 -m meridian_agents.post_agent approve &lt;id&gt;</code>.
        </p>
      </section>

      <!-- Multi-Agent Rebranding Pipeline -->
      <section>
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 rounded-xl bg-amber-600 flex items-center justify-center text-white text-xl">🎨</div>
          <h2 class="text-2xl font-bold text-white" style="font-family:'Playfair Display',serif">Monthly AI Rebranding</h2>
        </div>
        <p class="text-slate-500 text-sm mb-6">Five specialized agents collaborate every month to keep Meridian visually in step with the world.</p>
        <div class="bg-[#162236] border border-amber-900/40 rounded-2xl p-8 mb-8">
          <p class="text-slate-400 leading-relaxed mb-4">
            Every month, an AI agent surveys the global landscape — major sporting events, cultural milestones, scientific breakthroughs, seasonal celebrations — and rebrands Meridian to reflect the moment. Color themes, hero banners, holiday badges, and editorial tone shift to stay culturally resonant and visually fresh.
          </p>
          <p class="text-slate-400 text-sm leading-relaxed">
            This month, for example, the platform wears the colors of <span class="text-amber-400 font-semibold">FIFA World Cup 2026</span>. Next month it will wear something new. The world changes; Meridian keeps up — automatically.
          </p>
        </div>

        <!-- Agent pipeline cards -->
        <h3 class="font-bold text-slate-500 mb-4 text-xs uppercase tracking-widest">The Five-Agent Pipeline</h3>
        <div class="space-y-3">
          <div v-for="(agent, i) in rebrandAgents" :key="agent.name" class="flex gap-4 items-start">
            <div class="flex flex-col items-center flex-shrink-0">
              <div class="w-9 h-9 rounded-xl bg-[#162236] border-2 border-amber-800/50 flex items-center justify-center text-lg">{{ agent.icon }}</div>
              <div v-if="i < rebrandAgents.length - 1" class="w-0.5 h-5 bg-amber-900/50 mt-1"></div>
            </div>
            <div class="pb-2">
              <span class="font-bold text-slate-200 text-sm">{{ agent.name }}</span>
              <p class="text-slate-400 text-sm leading-relaxed mt-0.5">{{ agent.desc }}</p>
            </div>
          </div>
        </div>
        <div class="mt-6 bg-[#1a1500] border border-amber-900/40 rounded-xl p-4 text-sm text-slate-400 leading-relaxed">
          <span class="text-amber-400 font-semibold">Self-correcting loops:</span> If ReviewerAgent finds a WCAG AA contrast failure (ratio &lt; 4.5:1), it hands back to IdeationAgent for a palette revision. Markup or ARIA issues route to CodingAgent. Build failures send TesterAgent back to CodingAgent. The pipeline allows up to three revision cycles before committing.
        </div>
      </section>

      <!-- AI News Agent -->
      <section>
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-slate-600 flex items-center justify-center text-white text-xl">📰</div>
          <h2 class="text-2xl font-bold text-white" style="font-family:'Playfair Display',serif">AI News Agent</h2>
        </div>
        <div class="text-slate-400 leading-relaxed space-y-4 mb-8">
          <p>
            Meridian's <span class="text-slate-200 font-semibold">News Agent</span> runs every 12 hours and autonomously aggregates, curates, and publishes the day's top stories — no human editor required. Powered by <span class="text-violet-300 font-semibold">Gemini 2.5 Flash</span>, it pulls from over 20 live RSS feeds, selects 10 stories across four regions, writes a crisp 100-word neutral summary for each, and saves them directly to the platform.
          </p>
          <p>
            Before saving, every thumbnail is downloaded, sent to <span class="text-violet-300 font-semibold">Gemini's image-enhancement model</span> to sharpen focus and improve clarity, and then uploaded to Meridian's own media service — replacing low-resolution news thumbnails with locally-hosted, high-quality images. The News page also features a built-in <span class="text-violet-300 font-semibold">text-to-speech player</span> that can read all stories aloud in sequence.
          </p>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <div v-for="r in newsRegions" :key="r.label" class="bg-[#162236] border border-[#2d3f5f] rounded-2xl p-4">
            <div class="text-2xl mb-2">{{ r.flag }}</div>
            <div class="font-bold text-slate-200 text-sm mb-1">{{ r.label }}</div>
            <div class="text-slate-500 text-xs leading-snug">{{ r.sources }}</div>
          </div>
        </div>
        <div class="bg-[#162236] border border-[#2d3f5f] rounded-xl p-4 text-sm text-slate-400 leading-relaxed">
          <span class="text-slate-300 font-semibold">How it works:</span> RSS feeds → Gemini curates 10 stories + writes summaries → og:image fallback scraping for articles missing thumbnails → Gemini image enhancement → upload to media service → published to the News page. Schedule: <code class="bg-slate-800 px-1.5 py-0.5 rounded text-xs font-mono text-violet-300">0 6,18 * * *</code> UTC.
        </div>
      </section>

      <!-- Story Corner -->
      <section>
        <div class="flex items-center gap-3 mb-6">
          <div class="w-10 h-10 rounded-xl bg-rose-700 flex items-center justify-center text-white text-xl">📖</div>
          <h2 class="text-2xl font-bold text-white" style="font-family:'Playfair Display',serif">Story Corner</h2>
        </div>
        <div class="text-slate-400 leading-relaxed space-y-4 mb-6">
          <p>
            Every week, the <span class="text-slate-200 font-semibold">Story Agent</span> writes an original children's story for readers aged 8–15. Each story is crafted by Gemini to be imaginative, age-appropriate, and engaging — with a distinct narrative arc, memorable characters, and a gentle moral. A matching illustrated thumbnail is generated via AI image synthesis (Imagen 4 / FLUX.1) and uploaded alongside the story.
          </p>
          <p>
            Stories live in their own <span class="text-rose-400 font-semibold">Story Corner</span> section, separate from the main blog feed. Like blog posts, they can be listened to with the built-in TTS player — making them accessible even for younger readers who prefer to hear rather than read.
          </p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="bg-[#1e1520] border border-rose-900/40 rounded-2xl p-5">
            <div class="text-2xl mb-2">🎯</div>
            <div class="font-bold text-slate-200 text-sm mb-1">Audience</div>
            <p class="text-slate-400 text-xs leading-relaxed">Written for ages 8–15 with vocabulary and themes calibrated to the target age group.</p>
          </div>
          <div class="bg-[#1e1520] border border-rose-900/40 rounded-2xl p-5">
            <div class="text-2xl mb-2">🖼️</div>
            <div class="font-bold text-slate-200 text-sm mb-1">AI Illustrations</div>
            <p class="text-slate-400 text-xs leading-relaxed">Each story gets a unique cover image generated by Imagen 4 or FLUX.1 and stored in the media service.</p>
          </div>
          <div class="bg-[#1e1520] border border-rose-900/40 rounded-2xl p-5">
            <div class="text-2xl mb-2">🔊</div>
            <div class="font-bold text-slate-200 text-sm mb-1">Listen Mode</div>
            <p class="text-slate-400 text-xs leading-relaxed">Every story streams as audio via the same TTS engine used for blog posts and news.</p>
          </div>
        </div>
      </section>

      <!-- System Design Download -->
      <section>
        <div class="bg-[#162236] border border-violet-900/40 rounded-2xl p-8 flex flex-col sm:flex-row items-center gap-6">
          <div class="w-14 h-14 rounded-2xl bg-violet-700 flex items-center justify-center text-white text-2xl flex-shrink-0">📊</div>
          <div class="flex-1 text-center sm:text-left">
            <h3 class="text-lg font-bold text-white mb-1" style="font-family:'Playfair Display',serif">System Design Document</h3>
            <p class="text-slate-400 text-sm leading-relaxed">22-slide deep dive into Meridian's architecture — service topology, 14 annotated sequence diagrams covering every major user flow, technology stack, and future roadmap.</p>
          </div>
          <a href="/myblogs.pdf" download="myblogs.pdf"
             class="flex-shrink-0 inline-flex items-center gap-2 bg-violet-600 text-white px-6 py-3 rounded-full text-sm font-semibold hover:bg-violet-700 transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            Download PDF
          </a>
        </div>
      </section>

      <!-- Divider -->
      <div class="border-t border-[#2d3f5f]"></div>

      <!-- Ideator -->
      <section id="ideator">
        <div class="text-center mb-10">
          <span class="inline-block bg-violet-950 text-violet-400 text-xs font-bold uppercase tracking-widest px-4 py-1.5 rounded-full border border-violet-900 mb-4">The Human Behind the Vision</span>
          <h2 class="text-3xl font-bold text-white" style="font-family:'Playfair Display',serif">Meet the Ideator</h2>
        </div>
        <div class="bg-[#162236] rounded-3xl border border-[#2d3f5f] p-8 sm:p-12 flex flex-col sm:flex-row gap-8 items-start">
          <div class="flex-shrink-0">
            <div class="w-24 h-24 rounded-2xl bg-gradient-to-br from-violet-600 to-primary-700 flex items-center justify-center text-white text-4xl font-black select-none">
              B
            </div>
          </div>
          <div class="flex-1">
            <h3 class="text-2xl font-bold text-white mb-1" style="font-family:'Playfair Display',serif">Bibhu Mishra</h3>
            <p class="text-violet-400 font-semibold mb-1">Principal Cloud / DevOps Architect</p>
            <p class="text-slate-400 text-sm mb-5">Azure &amp; Kubernetes · MLOps · DevOps &amp; Cloud Transformation · LTIMindtree</p>

            <div class="text-slate-400 text-sm leading-relaxed space-y-3">
              <p>
                Bibhu is a seasoned technology leader with over 18 years of experience at the intersection of cloud infrastructure, DevOps, and applied AI. He specializes in Azure cloud architecture and Kubernetes-based platforms, and has led large-scale migrations of major web properties — including Microsoft.com news and blogging products — to Azure Kubernetes Services.
              </p>
              <p>
                Meridian was born from Bibhu's conviction that AI should not just assist developers — it should <em class="text-slate-300">be</em> the developer. This platform is his proof of concept: a fully autonomous, AI-built, AI-operated publication that demonstrates what is possible when you put an agent in the driver's seat from day one.
              </p>
              <p>
                Beyond architecture, Bibhu is a practitioner of MLOps and cloud-native transformation, driving innovation and operational efficiency for enterprise clients. His work sits at the frontier of AI-enabled infrastructure.
              </p>
            </div>

            <div class="mt-6 flex flex-wrap gap-3">
              <a
                href="https://www.linkedin.com/in/mishrab"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-2 bg-[#0A66C2] text-white px-5 py-2.5 rounded-full text-sm font-semibold hover:bg-[#004182] transition-colors"
              >
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                LinkedIn Profile
              </a>
              <span class="inline-flex items-center gap-2 bg-slate-800 text-slate-400 px-5 py-2.5 rounded-full text-sm font-medium border border-slate-700">
                🔧 Azure · Kubernetes · MLOps · DevOps
              </span>
            </div>
          </div>
        </div>
      </section>

    </div>

    <Footer />
  </div>
</template>
