<script setup>
import { ref, computed, onMounted } from 'vue'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import api from '../api'
import { format, parseISO, isValid } from 'date-fns'

const items = ref([])
const lastUpdated = ref(null)
const loading = ref(true)
const activeRegion = ref('all')

const REGIONS = [
  { key: 'all',    label: 'All News',  flag: '🗞️' },
  { key: 'world',  label: 'World',     flag: '🌍' },
  { key: 'usa',    label: 'USA',       flag: '🇺🇸' },
  { key: 'india',  label: 'India',     flag: '🇮🇳' },
  { key: 'odisha', label: 'Odisha',    flag: '🏛️' },
]

const REGION_COLORS = {
  world:  'bg-blue-100 text-blue-700',
  usa:    'bg-red-100 text-red-700',
  india:  'bg-orange-100 text-orange-700',
  odisha: 'bg-purple-100 text-purple-700',
}

const REGION_FLAGS = { world: '🌍', usa: '🇺🇸', india: '🇮🇳', odisha: '🏛️' }

const FALLBACK_IMAGES = {
  world:  'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=400&q=80',
  usa:    'https://images.unsplash.com/photo-1485738422979-f5c462d49f74?w=400&q=80',
  india:  'https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=400&q=80',
  odisha: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&q=80',
}

const filtered = computed(() =>
  activeRegion.value === 'all'
    ? items.value
    : items.value.filter(i => i.region === activeRegion.value)
)

function formatDate(str) {
  if (!str) return ''
  try {
    const d = parseISO(str)
    return isValid(d) ? format(d, 'MMM d, yyyy · h:mm a') : str
  } catch { return str }
}

function imgSrc(item) {
  return item.imageUrl || FALLBACK_IMAGES[item.region] || FALLBACK_IMAGES.world
}

async function load() {
  loading.value = true
  try {
    const res = await api.get('/news')
    items.value = res.data.items || []
    lastUpdated.value = res.data.lastUpdated
  } catch { items.value = [] }
  finally { loading.value = false }
}

onMounted(load)
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <Navbar />

    <!-- Hero -->
    <div class="bg-gradient-to-r from-slate-800 to-slate-900 text-white py-10">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between flex-wrap gap-4">
          <div>
            <div class="flex items-center gap-3 mb-1">
              <span class="text-3xl">🗞️</span>
              <h1 class="text-3xl font-bold tracking-tight">Today's Top News</h1>
            </div>
            <p class="text-slate-400 text-sm">
              AI-curated headlines from around the world · Updated every morning
            </p>
          </div>
          <div v-if="lastUpdated" class="text-xs text-slate-400 flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Last refreshed {{ format(new Date(lastUpdated), 'MMM d · h:mm a') }}
          </div>
        </div>

        <!-- Region tabs -->
        <div class="flex flex-wrap gap-2 mt-6">
          <button
            v-for="r in REGIONS" :key="r.key"
            @click="activeRegion = r.key"
            class="px-4 py-1.5 rounded-full text-sm font-medium transition-all"
            :class="activeRegion === r.key
              ? 'bg-white text-slate-900 shadow'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'"
          >
            {{ r.flag }} {{ r.label }}
          </button>
        </div>
      </div>
    </div>

    <main class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-4">
        <div v-for="i in 5" :key="i" class="bg-white rounded-2xl p-4 flex gap-4 animate-pulse shadow-sm">
          <div class="w-36 h-24 rounded-xl bg-gray-200 flex-shrink-0"></div>
          <div class="flex-1 space-y-2 py-1">
            <div class="h-3 bg-gray-200 rounded w-24"></div>
            <div class="h-5 bg-gray-200 rounded w-3/4"></div>
            <div class="h-3 bg-gray-100 rounded w-full"></div>
            <div class="h-3 bg-gray-100 rounded w-5/6"></div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else-if="!filtered.length" class="text-center py-24">
        <div class="text-5xl mb-4">📭</div>
        <p class="text-gray-500 text-lg font-medium">No news yet</p>
        <p class="text-gray-400 text-sm mt-1">The agent runs every morning at 6 AM and will populate this page.</p>
      </div>

      <!-- News list -->
      <div v-else class="space-y-4">
        <article
          v-for="(item, idx) in filtered" :key="item.id"
          class="bg-white rounded-2xl shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col sm:flex-row gap-0"
        >
          <!-- Thumbnail -->
          <div class="sm:w-48 sm:flex-shrink-0 relative overflow-hidden bg-gray-100">
            <img
              :src="imgSrc(item)"
              :alt="item.title"
              class="w-full h-44 sm:h-full object-cover"
              loading="lazy"
              @error="e => e.target.src = FALLBACK_IMAGES[item.region] || FALLBACK_IMAGES.world"
            />
            <!-- Number badge -->
            <span class="absolute top-2 left-2 w-7 h-7 flex items-center justify-center rounded-full bg-slate-900/80 text-white text-xs font-bold">
              {{ idx + 1 }}
            </span>
          </div>

          <!-- Content -->
          <div class="flex flex-col justify-between p-5 flex-1 min-w-0">
            <div>
              <!-- Region + source + date -->
              <div class="flex flex-wrap items-center gap-2 mb-2">
                <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold"
                  :class="REGION_COLORS[item.region] || 'bg-gray-100 text-gray-600'">
                  {{ REGION_FLAGS[item.region] || '📰' }} {{ item.region?.charAt(0).toUpperCase() + item.region?.slice(1) }}
                </span>
                <span v-if="item.sourceName" class="text-xs text-gray-500 font-medium">{{ item.sourceName }}</span>
                <span v-if="item.publishedAt" class="text-xs text-gray-400">· {{ formatDate(item.publishedAt) }}</span>
              </div>

              <!-- Title -->
              <h2 class="text-base sm:text-lg font-bold text-gray-900 leading-snug mb-2 line-clamp-2">
                {{ item.title }}
              </h2>

              <!-- Summary -->
              <p class="text-sm text-gray-600 leading-relaxed line-clamp-3">
                {{ item.summary }}
              </p>
            </div>

            <!-- CTA -->
            <div class="mt-4">
              <a
                :href="item.sourceUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 text-white text-xs font-semibold rounded-lg hover:bg-slate-700 transition-colors group"
              >
                Read full story
                <svg class="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                </svg>
              </a>
            </div>
          </div>
        </article>
      </div>
    </main>

    <Footer />
  </div>
</template>
