<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import api from '../api'
import { format, parseISO, isValid } from 'date-fns'

const items       = ref([])
const lastUpdated = ref(null)
const loading     = ref(true)
const activeRegion = ref('all')

// ── TTS player — same server-side synthesis engine as the blog reader ─────────
const ttsState       = ref('idle')   // idle | loading | playing | paused
const ttsProgress    = ref(0)
const ttsChunkIdx    = ref(0)
const ttsTotalChunks = ref(0)
const playerOpen     = ref(false)
const activeIdx      = ref(-1)

let sessionId      = 0
let audioEl        = null
let currentBlobUrl = null
let resolveChunk   = null
let chunkFetches   = []
let chunkBlobs     = []     // populated once each fetch resolves; index presence = resolved
let chunkData      = []     // { text, storyIdx }[]

function _splitText(text, maxLen = 1000) {
  const parts = []
  const t = text.trim()
  if (!t) return parts
  if (t.length <= maxLen) { parts.push(t); return parts }
  // Split only at sentence boundaries
  const ends = []
  for (const m of t.matchAll(/[.!?]+\s+/g)) ends.push(m.index + m[0].length)
  let start = 0
  while (start < t.length) {
    const remaining = t.slice(start)
    if (remaining.length <= maxLen) { parts.push(remaining.trim()); break }
    const cutPos = ends.filter(e => e > start && e <= start + maxLen).at(-1)
    const cut = cutPos ?? (start + maxLen)
    parts.push(t.slice(start, cut).trim())
    start = cut
  }
  return parts.filter(Boolean)
}

function _buildChunks(newsList, regionLabel) {
  const chunks = []
  chunks.push({
    text: `Good day. Here are today's top${regionLabel} news stories.`,
    storyIdx: -1,
  })
  newsList.forEach((item, i) => {
    // Title + summary in one chunk — avoids jarring mid-summary break
    const fullText = `Story ${i + 1}. ${item.title}. ${item.summary || ''}`.trim()
    _splitText(fullText).forEach(part =>
      chunks.push({ text: part, storyIdx: i })
    )
  })
  chunks.push({ text: 'That is all for now. Stay informed.', storyIdx: -1 })
  return chunks
}

// Fetch one chunk and cache the resolved blob so _runFrom can skip the loading state.
function _fetchChunk(idx) {
  if (!chunkFetches[idx]) {
    chunkFetches[idx] = api
      .post('/tts', { text: chunkData[idx].text }, { responseType: 'blob', timeout: 90_000 })
      .then(r => { chunkBlobs[idx] = r.data; return r.data })
      .catch(() => { chunkBlobs[idx] = null; return null })
  }
}

function _ensureAudio() {
  if (!audioEl) {
    audioEl = new Audio()
    // silent WAV activates element under Safari autoplay policy
    audioEl.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA='
    const p = audioEl.play(); if (p) p.catch(() => {})
    audioEl.pause()
    audioEl.src = ''
  }
  return audioEl
}

function _playBlob(blob, idx) {
  return new Promise(resolve => {
    resolveChunk = resolve
    const el = _ensureAudio()
    const url = URL.createObjectURL(blob)
    currentBlobUrl = url
    el.src = url
    el.ontimeupdate = () => {
      if (!el.duration) return
      ttsProgress.value = (idx + el.currentTime / el.duration) / ttsTotalChunks.value
    }
    const done = () => {
      URL.revokeObjectURL(url)
      if (currentBlobUrl === url) currentBlobUrl = null
      el.ontimeupdate = el.onended = el.onerror = null
      resolveChunk = null
      resolve()
    }
    el.onended = done
    el.onerror = done
    el.play().catch(done)
  })
}

function _cancelCurrent() {
  if (audioEl) { audioEl.pause(); audioEl.src = '' }
  if (currentBlobUrl) { URL.revokeObjectURL(currentBlobUrl); currentBlobUrl = null }
  if (resolveChunk) { resolveChunk(); resolveChunk = null }
}

async function _runFrom(start, session) {
  for (let i = start; i < ttsTotalChunks.value; i++) {
    if (session !== sessionId) return
    ttsChunkIdx.value = i
    const si = chunkData[i]?.storyIdx ?? -1
    if (si >= 0) {
      activeIdx.value = si
      const el = document.getElementById(`news-item-${si}`)
      if (el) {
        const rect = el.getBoundingClientRect()
        if (rect.top < 80 || rect.bottom > window.innerHeight - 80) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
      }
    } else {
      activeIdx.value = -1
    }

    // Kick off this chunk + 5 ahead so the pipeline is always full
    _fetchChunk(i)
    for (let p = 1; p <= 5; p++) {
      if (i + p < ttsTotalChunks.value) _fetchChunk(i + p)
    }

    // Only show the loading spinner if the blob isn't already cached
    if (!(i in chunkBlobs)) {
      ttsState.value = 'loading'
      await chunkFetches[i]
    }
    if (session !== sessionId) return
    const blob = chunkBlobs[i]
    if (!blob) continue
    ttsState.value = 'playing'
    await _playBlob(blob, i)
    if (session !== sessionId) return
  }
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
  activeIdx.value = -1
  playerOpen.value = false
}

async function openPlayer() {
  playerOpen.value = true
  if (ttsState.value !== 'idle') return
  const list = filtered.value
  const regionLabel = activeRegion.value === 'all' ? '' : ` ${activeRegion.value}`
  chunkData = _buildChunks(list, regionLabel)
  ttsTotalChunks.value = chunkData.length
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
  chunkFetches = []
  chunkBlobs = []
  _ensureAudio()
  // Pre-warm the first 5 chunks immediately
  for (let k = 0; k < Math.min(5, chunkData.length); k++) _fetchChunk(k)
  ttsState.value = 'loading'
  const session = ++sessionId
  await _runFrom(0, session)
}

function togglePlayPause() {
  if (!audioEl) return
  if (ttsState.value === 'playing') { audioEl.pause(); ttsState.value = 'paused' }
  else if (ttsState.value === 'paused') { audioEl.play(); ttsState.value = 'playing' }
}

function stopPlayback() {
  sessionId++
  _cancelCurrent()
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
  activeIdx.value = -1
  playerOpen.value = false
}

watch(activeRegion, () => { if (playerOpen.value) stopPlayback() })
onUnmounted(() => { sessionId++; _cancelCurrent(); if (audioEl) { audioEl.src = ''; audioEl = null } })

// ── Regions / colours ────────────────────────────────────────────────────────
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
  <div class="min-h-screen bg-gray-50" :class="playerOpen ? 'pb-20' : ''">
    <Navbar />

    <!-- Hero -->
    <div class="bg-gradient-to-r from-slate-800 to-slate-900 text-white py-10">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <!-- Title block -->
        <div class="flex items-center gap-3 mb-1">
          <span class="text-3xl">🗞️</span>
          <h1 class="text-3xl font-bold tracking-tight">Today's Top News</h1>
        </div>
        <p class="text-slate-400 text-sm">
          AI-curated headlines from around the world · Updated every 12 hours
          <span v-if="lastUpdated" class="ml-2 inline-flex items-center gap-1">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            {{ format(new Date(lastUpdated), 'MMM d · h:mm a') }}
          </span>
        </p>

        <!-- Region tabs + Listen button -->
        <div class="flex flex-wrap items-center gap-2 mt-6">
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

          <!-- Listen button — shown when player is closed -->
          <button v-if="!playerOpen && filtered.length"
            @click="openPlayer"
            class="ml-auto flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold bg-white/10 hover:bg-white/20 text-white border border-white/20 transition-all"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
            </svg>
            Listen to all
          </button>

          <!-- "Now playing" badge when player is active (tapping stops) -->
          <button v-else-if="playerOpen"
            @click="stopPlayback"
            class="ml-auto flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold bg-rose-500/80 hover:bg-rose-600 text-white border border-rose-400/30 transition-all"
          >
            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <rect x="4" y="4" width="16" height="16" rx="2"/>
            </svg>
            Stop reading
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
        <p class="text-gray-400 text-sm mt-1">The agent runs every 12 hours and will populate this page.</p>
      </div>

      <!-- News list -->
      <div v-else class="space-y-4">
        <article
          v-for="(item, idx) in filtered" :key="item.id"
          :id="`news-item-${idx}`"
          class="bg-white rounded-2xl shadow-sm hover:shadow-md transition-all overflow-hidden flex flex-col sm:flex-row gap-0"
          :class="activeIdx === idx ? 'ring-2 ring-rose-400 shadow-md shadow-rose-100' : ''"
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
            <span class="absolute top-2 left-2 w-7 h-7 flex items-center justify-center rounded-full text-white text-xs font-bold transition-colors"
              :class="activeIdx === idx ? 'bg-rose-500' : 'bg-slate-900/80'">
              {{ idx + 1 }}
            </span>
            <!-- Speaking indicator -->
            <div v-if="activeIdx === idx"
              class="absolute bottom-2 left-2 flex items-end gap-0.5 h-5 bg-rose-500/90 rounded-full px-1.5 py-1">
              <span class="w-0.5 bg-white rounded-full animate-[bounce_0.6s_ease-in-out_infinite]" style="height:50%"></span>
              <span class="w-0.5 bg-white rounded-full animate-[bounce_0.6s_ease-in-out_0.2s_infinite]" style="height:100%"></span>
              <span class="w-0.5 bg-white rounded-full animate-[bounce_0.6s_ease-in-out_0.1s_infinite]" style="height:70%"></span>
            </div>
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

              <!-- Title — highlighted when this story is active -->
              <h2 class="text-base sm:text-lg font-bold leading-snug mb-3 transition-colors"
                :class="activeIdx === idx ? 'text-rose-700' : 'text-gray-900'">
                {{ item.title }}
              </h2>

              <!-- Summary -->
              <p class="text-sm text-gray-600 leading-relaxed">
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

    <!-- Fixed bottom player bar — visible anywhere on the page while TTS is active -->
    <Teleport to="body">
      <div v-if="playerOpen" class="fixed bottom-0 inset-x-0 z-50 bg-slate-900/95 backdrop-blur-sm border-t border-slate-700 shadow-2xl">
        <div class="max-w-6xl mx-auto px-4 py-3 flex items-center gap-3">
          <!-- Animated waveform bars -->
          <div class="flex items-end gap-0.5 h-5 flex-shrink-0" aria-hidden="true">
            <span v-for="(h, i) in [60,100,70,40]" :key="i"
              class="w-0.5 rounded-full transition-all bg-white"
              :class="ttsState === 'playing' ? 'animate-[bounce_0.6s_ease-in-out_infinite]' : 'opacity-40'"
              :style="ttsState === 'playing' ? `height:${h}%; animation-delay:${i * 0.15}s` : 'height:4px'">
            </span>
          </div>
          <!-- Story counter -->
          <span class="text-xs text-white/60 flex-shrink-0 tabular-nums hidden sm:inline">
            Story {{ activeIdx >= 0 ? activeIdx + 1 : '—' }} / {{ filtered.length }}
          </span>
          <!-- Progress bar -->
          <div class="flex-1 h-1.5 bg-white/20 rounded-full overflow-hidden">
            <div class="h-full bg-white rounded-full transition-all duration-200"
              :style="`width:${Math.round(ttsProgress * 100)}%`"></div>
          </div>
          <!-- Chunk counter -->
          <span class="text-xs text-white/60 flex-shrink-0 tabular-nums">
            {{ ttsChunkIdx + 1 }}/{{ ttsTotalChunks }}
          </span>
          <!-- Pause / Resume -->
          <button @click="ttsState === 'loading' ? null : togglePlayPause()"
            class="flex items-center justify-center w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors flex-shrink-0"
            :class="ttsState === 'loading' ? 'cursor-wait opacity-50' : ''"
            :title="ttsState === 'playing' ? 'Pause' : 'Resume'">
            <svg v-if="ttsState === 'loading'" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            <svg v-else-if="ttsState === 'playing'" class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
            </svg>
            <svg v-else class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z"/>
            </svg>
          </button>
          <!-- Stop -->
          <button @click="stopPlayback"
            class="flex items-center justify-center w-8 h-8 rounded-lg bg-white/10 hover:bg-rose-500/80 text-white transition-colors flex-shrink-0"
            title="Stop">
            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <rect x="4" y="4" width="16" height="16" rx="2"/>
            </svg>
          </button>
        </div>
      </div>
    </Teleport>

    <Footer />
  </div>
</template>
