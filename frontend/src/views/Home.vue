<script setup>
import { onMounted, computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useBlogStore } from '../stores/blog'
import { useLayoutStore } from '../stores/layout'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import PostCard from '../components/PostCard.vue'
import WeatherWidget from '../components/WeatherWidget.vue'
import api from '../api'
import { format } from 'date-fns'

const blog = useBlogStore()
const layout = useLayoutStore()

const newsItems   = ref([])
const latestStory = ref(null)

onMounted(async () => {
  await Promise.all([blog.fetchRecent(), blog.fetchFeatured(), blog.fetchCategories()])

  try {
    const { data } = await api.get('/news')
    newsItems.value = (data.items || []).slice(0, 4)
  } catch {}

  try {
    const { data } = await api.get('/stories?limit=1')
    latestStory.value = (data.stories || data)[0] || null
  } catch {}
})

// Latest posts — recent takes priority over featured
const latestPosts = computed(() => blog.recent.length ? blog.recent : blog.featured)
const hero        = computed(() => latestPosts.value[0] || null)
const sidePanel   = computed(() => latestPosts.value.slice(1, 4))
const gridPosts   = computed(() => latestPosts.value.slice(1, 9))
const listPosts   = computed(() => latestPosts.value.slice(1, 5))
const morePosts   = computed(() => latestPosts.value.slice(5, 11))

const regionLabel = { world: '🌍 World', usa: '🇺🇸 USA', india: '🇮🇳 India', odisha: '🏛️ Odisha' }

function ago(d) {
  const diff = Date.now() - new Date(d).getTime()
  const h = Math.floor(diff / 3_600_000)
  if (h < 1) return 'just now'
  if (h < 24) return `${h}h ago`
  const days = Math.floor(h / 24)
  return days === 1 ? 'yesterday' : `${days}d ago`
}
</script>

<template>
  <!-- ══════════════════════════════════════════════════════════════════════ -->
  <!--  LAYOUT A — Editorial Light                                           -->
  <!-- ══════════════════════════════════════════════════════════════════════ -->
  <div v-if="layout.variant === 'a'" class="min-h-screen bg-white">
    <Navbar />

    <main id="main-content" tabindex="-1" class="outline-none">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 text-center">
      <!-- HOLIDAY-HERO-START -->
<div class="holiday-badge bg-primary-50 text-primary-800 border border-primary-200 rounded-full px-4 py-1 text-sm inline-block mb-4" aria-label="Sporting triumphs and national pride">Let's Celebrate!</div>
<!-- HOLIDAY-HERO-END -->
    </div>

    <!-- ── Hero: latest blog post dominates ── -->
    <section v-if="hero" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-16">
      <div class="flex items-center gap-2 mb-6">
        <span class="w-2 h-2 rounded-full bg-primary-500 animate-pulse"></span>
        <span class="text-xs font-bold uppercase tracking-widest text-primary-600">Latest</span>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <!-- Main hero post -->
        <RouterLink :to="`/blog/${hero.slug}`" class="lg:col-span-7 group">
          <div class="relative overflow-hidden rounded-3xl aspect-[4/3] lg:aspect-[16/10]">
            <img v-if="hero.featuredImage" :src="hero.featuredImage" :alt="hero.title"
              class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
            <div v-else class="w-full h-full bg-gradient-to-br from-primary-200 to-purple-200 flex items-center justify-center">
              <span class="text-6xl">{{ hero.category?.icon || '📝' }}</span>
            </div>
            <div class="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent" />
            <div class="absolute top-4 left-4">
              <span class="bg-primary-600 text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">New</span>
            </div>
            <div class="absolute bottom-0 left-0 right-0 p-8">
              <div v-if="hero.category" class="mb-3">
                <span class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold text-white"
                  :style="{ background: hero.category.color || '#3B82F6' }">
                  {{ hero.category.icon }} {{ hero.category.name }}
                </span>
              </div>
              <h1 class="text-2xl lg:text-4xl font-bold text-white leading-tight mb-3" style="font-family:'Playfair Display',serif">{{ hero.title }}</h1>
              <p class="text-gray-300 text-sm line-clamp-2 mb-4">{{ hero.excerpt }}</p>
              <div class="flex items-center gap-3 text-gray-300 text-xs">
                <div class="w-7 h-7 bg-primary-500 rounded-full flex items-center justify-center">
                  <span class="text-white font-bold">{{ (hero.authorName || 'A').charAt(0) }}</span>
                </div>
                <span>{{ hero.authorName }}</span>
                <span>·</span>
                <span>{{ ago(hero.createdAt) }}</span>
                <span>·</span>
                <span>{{ hero.readTime }} min read</span>
              </div>
            </div>
          </div>
        </RouterLink>

        <!-- Side panel: next 3 recent posts -->
        <div class="lg:col-span-5 flex flex-col gap-4">
          <h2 class="sr-only">Recent Posts</h2>
          <RouterLink v-for="post in sidePanel" :key="post.id" :to="`/blog/${post.slug}`"
            class="group flex gap-4 bg-gray-50 rounded-2xl p-4 hover:bg-primary-50 transition-colors">
            <div class="w-24 h-24 rounded-xl overflow-hidden flex-shrink-0 bg-gray-200">
              <img v-if="post.featuredImage" :src="post.featuredImage" :alt="post.title"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
              <div v-else class="w-full h-full flex items-center justify-center">
                <span class="text-2xl">{{ post.category?.icon || '📝' }}</span>
              </div>
            </div>
            <div class="flex-1 min-w-0">
              <div v-if="post.category" class="text-xs font-semibold mb-1" :style="{ color: post.category.color || '#3B82F6' }">
                {{ post.category.icon }} {{ post.category.name }}
              </div>
              <h3 class="font-bold text-gray-900 text-sm line-clamp-2 group-hover:text-primary-600 transition-colors"
                style="font-family:'Playfair Display',serif">{{ post.title }}</h3>
              <div class="text-xs text-gray-400 mt-1">{{ ago(post.createdAt) }} · {{ post.readTime }} min read</div>
            </div>
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- ── Latest Blog Posts grid ── -->
    <section v-if="gridPosts.length" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
      <div class="flex items-center justify-between mb-8">
        <div>
          <h2 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Latest Posts</h2>
          <p class="text-gray-500 text-sm mt-1">Fresh from every corner of knowledge</p>
        </div>
        <RouterLink to="/blog" class="text-primary-600 text-sm font-semibold hover:underline flex items-center gap-1">
          All posts <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
        </RouterLink>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <PostCard v-for="post in gridPosts.slice(0, 4)" :key="post.id" :post="post" />
      </div>
    </section>

    <!-- ── Discover More: News + Story Corner ── -->
    <section v-if="newsItems.length || latestStory" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
      <div class="border-t border-gray-100 pt-10 mb-8 flex items-center justify-between">
        <h2 class="text-xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Discover More</h2>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-5 gap-8">

        <!-- News column: 3/5 width -->
        <div v-if="newsItems.length" class="lg:col-span-3">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
              <span class="text-xs font-bold uppercase tracking-widest text-rose-600">Today's News</span>
            </div>
            <RouterLink to="/news" class="text-xs text-gray-400 hover:text-primary-600 font-medium transition-colors flex items-center gap-1">
              All news <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
            </RouterLink>
          </div>
          <div class="divide-y divide-gray-100">
            <a v-for="item in newsItems" :key="item.id" :href="item.sourceUrl" target="_blank" rel="noopener"
              class="group flex gap-3 py-4 hover:bg-gray-50 rounded-xl px-2 -mx-2 transition-colors">
              <div class="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100">
                <img :src="item.imageUrl || 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=128&q=80'" :alt="item.title" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" @error="e => e.target.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=128&q=80'" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">{{ regionLabel[item.region] || item.region }}</span>
                  <span class="text-xs text-gray-400">{{ item.sourceName }}</span>
                </div>
                <p class="text-sm font-semibold text-gray-800 line-clamp-2 group-hover:text-primary-600 transition-colors leading-snug">{{ item.title }}</p>
              </div>
            </a>
          </div>
        </div>

        <!-- Story Corner: 2/5 width -->
        <div v-if="latestStory" class="lg:col-span-2">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
              <span class="text-xs font-bold uppercase tracking-widest text-indigo-600">Story Corner</span>
            </div>
            <RouterLink to="/story" class="text-xs text-gray-400 hover:text-indigo-600 font-medium transition-colors flex items-center gap-1">
              All stories <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
            </RouterLink>
          </div>
          <RouterLink :to="`/story/${latestStory.slug}`" class="group block rounded-2xl overflow-hidden border border-gray-100 hover:border-indigo-200 hover:shadow-lg transition-all duration-300">
            <div v-if="latestStory.featuredImage" class="aspect-[16/9] overflow-hidden">
              <img :src="latestStory.featuredImage" :alt="latestStory.title"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
            </div>
            <div v-else class="aspect-[16/9] bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center">
              <span class="text-4xl">📖</span>
            </div>
            <div class="p-4">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-600">{{ latestStory.genre }}</span>
                <span class="text-xs text-gray-400">Ages 8–15</span>
              </div>
              <h3 class="font-bold text-gray-900 text-sm leading-snug mb-2 group-hover:text-indigo-600 transition-colors"
                style="font-family:'Playfair Display',serif">{{ latestStory.title }}</h3>
              <p class="text-xs text-gray-500 line-clamp-2">{{ latestStory.excerpt }}</p>
              <div class="mt-3 text-xs font-semibold text-indigo-600 flex items-center gap-1">
                Read story <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
              </div>
            </div>
          </RouterLink>
        </div>

      </div>
    </section>

    <!-- ── Weather + Newsletter ── -->
    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 items-stretch">
        <WeatherWidget variant="light" />
        <div class="bg-gradient-to-br from-primary-600 to-primary-800 rounded-2xl p-6 text-white flex flex-col justify-between">
          <div>
            <h2 class="font-bold text-lg mb-2" style="font-family:'Playfair Display',serif">Stay in the Loop</h2>
            <p class="text-primary-100 text-sm mb-4">Get the latest stories delivered to your inbox.</p>
          </div>
          <div class="flex gap-2">
            <input type="email" placeholder="your@email.com" aria-label="Email address for newsletter"
              class="flex-1 px-3 py-2 rounded-lg bg-white/20 text-white placeholder-primary-200 text-sm border border-white/30 focus:outline-none focus:border-white" />
            <button class="bg-white text-primary-600 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-primary-50 transition-colors">Subscribe</button>
          </div>
        </div>
      </div>
    </section>

    <!-- ── More blog posts ── -->
    <section v-if="gridPosts.length > 4" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
      <div class="border-t border-gray-100 pt-12">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <PostCard v-for="post in gridPosts.slice(4)" :key="post.id" :post="post" />
        </div>
      </div>
    </section>

    </main>
    <Footer />
  </div>

  <!-- ══════════════════════════════════════════════════════════════════════ -->
  <!--  LAYOUT B — Dark Magazine                                             -->
  <!-- ══════════════════════════════════════════════════════════════════════ -->
  <div v-else class="min-h-screen bg-[#0f172a] text-slate-200">
    <Navbar />

    <main id="main-content" tabindex="-1" class="outline-none">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4 text-center">
      <!-- HOLIDAY-HERO-B-START -->
<div class="holiday-badge-b bg-[#13132a] border border-[#39c0ed]/30 text-[#39c0ed] rounded-full px-4 py-1 text-sm inline-block mb-4" aria-label="Sporting triumphs and national pride">Game On!</div>
<!-- HOLIDAY-HERO-B-END -->
    </div>

    <!-- ── Full-bleed blog hero ── -->
    <section v-if="hero" class="relative">
      <div class="relative h-[60vw] min-h-[340px] max-h-[680px]">
        <img v-if="hero.featuredImage" :src="hero.featuredImage" :alt="hero.title"
          class="w-full h-full object-cover" />
        <div v-else class="w-full h-full bg-gradient-to-br from-violet-950 to-slate-950 flex items-center justify-center">
          <span class="text-8xl opacity-20">{{ hero.category?.icon || '📝' }}</span>
        </div>
        <div class="absolute inset-0 bg-gradient-to-t from-[#0f172a] via-[#0f172a]/50 to-transparent" />
        <div class="absolute inset-0 bg-gradient-to-r from-[#0f172a]/60 to-transparent" />
        <div class="absolute top-6 left-6 md:left-10">
          <span class="bg-violet-600 text-white text-xs font-bold px-3 py-1.5 rounded-full uppercase tracking-widest">Latest</span>
        </div>
      </div>
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="-mt-32 relative z-10 max-w-3xl">
          <div v-if="hero.category" class="mb-4">
            <span class="text-xs font-bold uppercase tracking-widest text-violet-400">
              {{ hero.category.icon }} {{ hero.category.name }}
            </span>
          </div>
          <RouterLink :to="`/blog/${hero.slug}`" class="group">
            <h1 class="text-3xl sm:text-4xl lg:text-5xl font-black text-white leading-tight mb-4 group-hover:text-violet-200 transition-colors"
              style="font-family:'Playfair Display',serif">{{ hero.title }}</h1>
          </RouterLink>
          <p class="text-slate-300 text-base lg:text-lg leading-relaxed mb-6 max-w-2xl">{{ hero.excerpt }}</p>
          <div class="flex items-center gap-4 text-sm text-slate-400">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 bg-violet-700 rounded-full flex items-center justify-center">
                <span class="text-white text-xs font-bold">{{ (hero.authorName || 'A').charAt(0) }}</span>
              </div>
              <span class="text-slate-300 font-medium">{{ hero.authorName }}</span>
            </div>
            <span class="text-violet-600">·</span>
            <span>{{ ago(hero.createdAt) }}</span>
            <span class="text-violet-600">·</span>
            <span>{{ hero.readTime }} min read</span>
            <RouterLink :to="`/blog/${hero.slug}`"
              class="ml-4 inline-flex items-center gap-2 bg-violet-600 hover:bg-violet-700 text-white px-5 py-2 rounded-full text-sm font-semibold transition-colors">
              Read story
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
            </RouterLink>
          </div>
        </div>
      </div>
    </section>

    <!-- ── Numbered latest list + sidebar ── -->
    <section v-if="listPosts.length" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-10">

        <!-- Numbered latest list -->
        <div class="lg:col-span-7">
          <div class="flex items-center gap-3 mb-8">
            <span class="w-2 h-2 rounded-full bg-violet-500 animate-pulse"></span>
            <h2 class="text-xs font-bold uppercase tracking-widest text-violet-400">Latest Posts</h2>
          </div>
          <div class="space-y-0 divide-y divide-[#2d3f5f]">
            <RouterLink v-for="(post, i) in listPosts" :key="post.id" :to="`/blog/${post.slug}`"
              class="group flex gap-5 py-6 hover:bg-[#162236] transition-colors rounded-xl px-2 -mx-2">
              <span class="text-4xl font-black text-[#2d3f5f] group-hover:text-violet-800 transition-colors tabular-nums leading-none mt-1 w-8 flex-shrink-0">
                {{ String(i + 2).padStart(2, '0') }}
              </span>
              <div class="flex-1 min-w-0">
                <div v-if="post.category" class="text-xs font-bold uppercase tracking-wider text-violet-400 mb-2">
                  {{ post.category.icon }} {{ post.category.name }}
                </div>
                <h3 class="font-bold text-slate-100 group-hover:text-violet-300 transition-colors text-lg leading-snug mb-2"
                  style="font-family:'Playfair Display',serif">{{ post.title }}</h3>
                <p class="text-slate-400 text-sm line-clamp-2 mb-3">{{ post.excerpt }}</p>
                <div class="flex items-center gap-3 text-xs text-slate-400">
                  <span>{{ post.authorName }}</span>
                  <span>·</span>
                  <span>{{ ago(post.createdAt) }}</span>
                  <span>·</span>
                  <span>{{ post.readTime }} min</span>
                </div>
              </div>
              <div v-if="post.featuredImage" class="w-24 h-24 rounded-lg overflow-hidden flex-shrink-0 hidden sm:block">
                <img :src="post.featuredImage" :alt="post.title"
                  class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" />
              </div>
            </RouterLink>
          </div>
          <RouterLink to="/blog"
            class="mt-8 inline-flex items-center gap-2 border border-[#2d3f5f] hover:border-violet-500 text-slate-400 hover:text-violet-400 px-6 py-3 rounded-full text-sm font-medium transition-all">
            View all posts
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
          </RouterLink>
        </div>

        <!-- Sidebar: more blog post cards -->
        <div class="lg:col-span-5 space-y-4">
          <div class="flex items-center gap-3 mb-8">
            <span class="w-2 h-2 rounded-full bg-slate-600"></span>
            <h2 class="text-xs font-bold uppercase tracking-widest text-slate-400">More Posts</h2>
          </div>
          <PostCard v-for="post in morePosts.slice(0, 4)" :key="post.id" :post="post" />
        </div>
      </div>
    </section>

    <!-- ── Discover More: News + Story Corner (dark) ── -->
    <section v-if="newsItems.length || latestStory" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
      <div class="border-t border-[#2d3f5f] pt-10 mb-8 flex items-center justify-between">
        <h2 class="text-base font-bold uppercase tracking-widest text-slate-400">Discover More</h2>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-5 gap-8">

        <!-- News column -->
        <div v-if="newsItems.length" class="lg:col-span-3">
          <div class="flex items-center justify-between mb-5">
            <div class="flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
              <span class="text-xs font-bold uppercase tracking-widest text-rose-400">Today's News</span>
            </div>
            <RouterLink to="/news" class="text-xs text-slate-500 hover:text-rose-400 font-medium transition-colors flex items-center gap-1">
              All news <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
            </RouterLink>
          </div>
          <div class="divide-y divide-[#1e2d44]">
            <a v-for="item in newsItems" :key="item.id" :href="item.sourceUrl" target="_blank" rel="noopener"
              class="group flex gap-3 py-4 hover:bg-[#162236] rounded-xl px-2 -mx-2 transition-colors">
              <div class="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0 bg-slate-800">
                <img :src="item.imageUrl || 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=128&q=80'" :alt="item.title" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" @error="e => e.target.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=128&q=80'" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-[#1e2d44] text-slate-400">{{ regionLabel[item.region] || item.region }}</span>
                  <span class="text-xs text-slate-600">{{ item.sourceName }}</span>
                </div>
                <p class="text-sm font-semibold text-slate-200 line-clamp-2 group-hover:text-rose-300 transition-colors leading-snug">{{ item.title }}</p>
              </div>
            </a>
          </div>
        </div>

        <!-- Story Corner -->
        <div v-if="latestStory" class="lg:col-span-2">
          <div class="flex items-center justify-between mb-5">
            <div class="flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
              <span class="text-xs font-bold uppercase tracking-widest text-indigo-400">Story Corner</span>
            </div>
            <RouterLink to="/story" class="text-xs text-slate-500 hover:text-indigo-400 font-medium transition-colors flex items-center gap-1">
              All stories <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
            </RouterLink>
          </div>
          <RouterLink :to="`/story/${latestStory.slug}`"
            class="group block rounded-2xl overflow-hidden border border-[#1e2d44] hover:border-indigo-700/60 hover:shadow-xl hover:shadow-indigo-950/40 transition-all duration-300">
            <div v-if="latestStory.featuredImage" class="aspect-[16/9] overflow-hidden">
              <img :src="latestStory.featuredImage" :alt="latestStory.title"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
            </div>
            <div v-else class="aspect-[16/9] bg-gradient-to-br from-indigo-950 to-[#0f172a] flex items-center justify-center">
              <span class="text-4xl opacity-40">📖</span>
            </div>
            <div class="p-4 bg-[#162236]">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-400 border border-indigo-800/50">{{ latestStory.genre }}</span>
                <span class="text-xs text-slate-500">Ages 8–15</span>
              </div>
              <h3 class="font-bold text-slate-100 text-sm leading-snug mb-2 group-hover:text-indigo-300 transition-colors"
                style="font-family:'Playfair Display',serif">{{ latestStory.title }}</h3>
              <p class="text-xs text-slate-500 line-clamp-2">{{ latestStory.excerpt }}</p>
              <div class="mt-3 text-xs font-semibold text-indigo-400 flex items-center gap-1">
                Read story <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
              </div>
            </div>
          </RouterLink>
        </div>

      </div>
    </section>

    <!-- ── Weather + Newsletter ── -->
    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 items-stretch">
        <WeatherWidget variant="dark" />
        <div class="bg-[#162236] border border-violet-700/40 rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div class="text-violet-400 text-xs font-bold uppercase tracking-widest mb-2">Newsletter</div>
            <h3 class="font-bold text-white text-lg mb-2" style="font-family:'Playfair Display',serif">Stay Ahead</h3>
            <p class="text-slate-400 text-sm mb-4">Daily dispatches from AI, science, and beyond.</p>
          </div>
          <div class="flex gap-2">
            <input type="email" placeholder="your@email.com" aria-label="Email address for newsletter"
              class="flex-1 px-3 py-2 rounded-lg bg-slate-900 text-slate-200 placeholder-slate-600 text-sm border border-slate-700 focus:outline-none focus:border-violet-500" />
            <button class="bg-violet-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-violet-700 transition-colors">Go</button>
          </div>
        </div>
      </div>
    </section>

    <!-- ── More blog posts archive ── -->
    <section v-if="morePosts.length > 4" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
      <div class="border-t border-[#2d3f5f] pt-12 mb-8">
        <h2 class="text-xs font-bold uppercase tracking-widest text-slate-400">Archive</h2>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <PostCard v-for="post in morePosts.slice(4)" :key="post.id" :post="post" />
      </div>
    </section>

    <!-- Footer (dark) -->
    </main>
    <footer class="bg-[#090f1d] border-t border-[#1e2d44] text-slate-400 mt-8">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-12">
          <div class="md:col-span-2">
            <div class="flex items-center gap-2.5 mb-4">
              <span class="text-2xl font-bold text-white tracking-tight" style="font-family:'Playfair Display',serif">Meridian</span>
            </div>
            <p class="text-slate-400 leading-relaxed text-sm max-w-xs">Where ideas converge. Thoughtful writing on technology, science, history, and the ideas that shape our world.</p>
          </div>
          <div>
            <h3 class="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Topics</h3>
            <ul class="space-y-2">
              <li v-for="cat in blog.categories" :key="cat.id">
                <RouterLink :to="`/category/${cat.slug}`" class="text-slate-400 hover:text-violet-400 text-sm transition-colors flex items-center gap-2">
                  <span>{{ cat.icon }}</span> {{ cat.name }}
                </RouterLink>
              </li>
            </ul>
          </div>
          <div>
            <h3 class="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Quick Links</h3>
            <ul class="space-y-2">
              <li><RouterLink to="/" class="text-slate-400 hover:text-violet-400 text-sm transition-colors">Home</RouterLink></li>
              <li><RouterLink to="/blog" class="text-slate-400 hover:text-violet-400 text-sm transition-colors">All Posts</RouterLink></li>
              <li><RouterLink to="/news" class="text-slate-400 hover:text-violet-400 text-sm transition-colors">News</RouterLink></li>
              <li><RouterLink to="/story" class="text-slate-400 hover:text-violet-400 text-sm transition-colors">Stories</RouterLink></li>
              <li><RouterLink to="/search" class="text-slate-400 hover:text-violet-400 text-sm transition-colors">Search</RouterLink></li>
              <li><RouterLink to="/about" class="text-slate-400 hover:text-violet-400 text-sm transition-colors">About</RouterLink></li>
            </ul>
          </div>
        </div>
        <div class="border-t border-[#1e2d44] mt-12 pt-8 text-center text-sm text-slate-400">
          <p>&copy; {{ new Date().getFullYear() }} Meridian. Built with Vue.js &amp; NestJS.</p>
        </div>
      </div>
    </footer>
  </div>
</template>
