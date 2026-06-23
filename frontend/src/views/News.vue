<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import api from '../api'
import { format, parseISO, isValid } from 'date-fns'
import { useWakeLock } from '../composables/useWakeLock'

const items       = ref([])
const lastUpdated = ref(null)
const loading     = ref(true)
const activeRegion = ref('all')

// ── TTS player — same server-side synthesis engine as the blog reader ─────────
const ttsState       = ref('idle')   // idle | loading | playing | paused | error
const ttsProgress    = ref(0)
const ttsChunkIdx    = ref(0)
const ttsTotalChunks = ref(0)
const ttsError       = ref('')
const playerOpen     = ref(false)
const activeIdx      = ref(-1)

const { acquireWakeLock, releaseWakeLock } = useWakeLock()
watch(ttsState, v => v === 'playing' ? acquireWakeLock() : releaseWakeLock())

let sessionId       = 0
let audioCtx        = null
let nextStartAt     = 0
let highlightTimers = []
let rafId           = null
let chunkStartTimes = []
let chunkDurations  = []
let chunkFetches    = []
let chunkData       = []   // { text, storyIdx }[]

function _splitText(text, maxLen = 200) {
  const parts = []
  let rem = text.trim()
  while (rem.length > 0) {
    if (rem.length <= maxLen) { parts.push(rem); break }
    let cut = rem.lastIndexOf('. ', maxLen)
    if (cut < maxLen * 0.4) cut = rem.lastIndexOf(' ', maxLen)
    if (cut < 0) cut = maxLen
    else cut += 1
    parts.push(rem.slice(0, cut).trim())
    rem = rem.slice(cut).trim()
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
    chunks.push({ text: `Story ${i + 1}. ${item.title}.`, storyIdx: i })
    _splitText(item.summary || '', 200).forEach(part =>
      chunks.push({ text: part, storyIdx: i })
    )
  })
  chunks.push({ text: 'That is all for now. Stay informed.', storyIdx: -1 })
  return chunks
}

function _fetchChunk(text) {
  return api.post('/tts', { text, style: 'news' }, { responseType: 'blob', timeout: 90_000 })
    .then(r => r.data)
    .catch(e => ({ _ttsError: e?.response?.data?.message || e?.message || 'TTS unavailable' }))
}

function _ensureAudioCtx() {
  if (!audioCtx || audioCtx.state === 'closed') {
    audioCtx = new AudioContext()
    nextStartAt = audioCtx.currentTime
  }
  return audioCtx
}

function _clearTimers() {
  highlightTimers.forEach(id => clearTimeout(id))
  highlightTimers = []
}

function _stopRaf() {
  if (rafId) { cancelAnimationFrame(rafId); rafId = null }
}

function _startRaf() {
  _stopRaf()
  function tick() {
    const ctx = audioCtx
    if (!ctx || ctx.state === 'closed') return
    const now = ctx.currentTime
    for (let j = 0; j < chunkStartTimes.length; j++) {
      const st  = chunkStartTimes[j]
      const dur = chunkDurations[j]
      if (st !== undefined && dur && now >= st && now < st + dur) {
        ttsProgress.value = (j + (now - st) / dur) / ttsTotalChunks.value
        break
      }
    }
    rafId = requestAnimationFrame(tick)
  }
  rafId = requestAnimationFrame(tick)
}

async function _decodeAndSchedule(blob, i) {
  const ctx = audioCtx
  try {
    const arrayBuf = await blob.arrayBuffer()
    const audioBuf = await ctx.decodeAudioData(arrayBuf)
    const source = ctx.createBufferSource()
    source.buffer = audioBuf
    source.connect(ctx.destination)
    const startAt = Math.max(ctx.currentTime + 0.02, nextStartAt)
    source.start(startAt)
    nextStartAt = startAt + audioBuf.duration
    chunkStartTimes[i] = startAt
    chunkDurations[i]  = audioBuf.duration
    // Scroll news item into view when this chunk starts playing
    const si = chunkData[i]?.storyIdx ?? -1
    const ms = Math.max(0, (startAt - ctx.currentTime) * 1000)
    highlightTimers.push(setTimeout(() => {
      if (si >= 0) {
        activeIdx.value = si
        document.getElementById(`news-item-${si}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      } else {
        activeIdx.value = -1
      }
    }, ms))
    return source
  } catch { return null }
}

async function _runFrom(start, session) {
  for (let i = start; i < ttsTotalChunks.value; i++) {
    if (session !== sessionId) return
    ttsChunkIdx.value = i
    if (i === start) ttsState.value = 'loading'

    if (!chunkFetches[i]) chunkFetches[i] = _fetchChunk(chunkData[i].text)
    for (let p = 1; p <= 4; p++) {
      const ahead = i + p
      if (ahead < ttsTotalChunks.value && !chunkFetches[ahead])
        chunkFetches[ahead] = _fetchChunk(chunkData[ahead].text)
    }
    const result = await chunkFetches[i]
    if (session !== sessionId) return
    if (!result || result._ttsError) {
      ttsState.value = 'error'
      ttsError.value = result?._ttsError || 'TTS unavailable'
      return
    }
    const source = await _decodeAndSchedule(result, i)
    if (session !== sessionId) return
    if (!source) {
      ttsState.value = 'error'
      ttsError.value = 'Audio decode failed'
      return
    }
    if (i === start) { ttsState.value = 'playing'; _startRaf() }
    await new Promise(resolve => {
      source.onended = resolve
      const watchdog = setInterval(() => {
        if (session !== sessionId || !audioCtx || audioCtx.state === 'closed') {
          clearInterval(watchdog)
          resolve(null)
        }
      }, 200)
      source.addEventListener('ended', () => clearInterval(watchdog), { once: true })
    })
    if (session !== sessionId) return
  }
  _stopRaf()
  _clearTimers()
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
  activeIdx.value = -1
  playerOpen.value = false
}

async function openPlayer() {
  playerOpen.value = true
  ttsError.value = ''
  if (ttsState.value !== 'idle' && ttsState.value !== 'error') return
  ttsState.value = 'idle'
  _ensureAudioCtx()
  const list = filtered.value
  const regionLabel = activeRegion.value === 'all' ? '' : ` ${activeRegion.value}`
  chunkData = _buildChunks(list, regionLabel)
  ttsTotalChunks.value = chunkData.length
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
  chunkFetches = new Array(chunkData.length).fill(null)
  nextStartAt = audioCtx.currentTime + 0.05
  chunkStartTimes = []
  chunkDurations = []
  _clearTimers()
  for (let k = 0; k < Math.min(4, chunkData.length); k++)
    chunkFetches[k] = _fetchChunk(chunkData[k].text)
  ttsState.value = 'loading'
  const session = ++sessionId
  await _runFrom(0, session)
}

function togglePlayPause() {
  if (!audioCtx) return
  if (ttsState.value === 'playing') { audioCtx.suspend(); ttsState.value = 'paused' }
  else if (ttsState.value === 'paused') { audioCtx.resume(); ttsState.value = 'playing' }
}

function stopPlayback() {
  sessionId++
  _clearTimers()
  _stopRaf()
  if (audioCtx) { audioCtx.close(); audioCtx = null }
  nextStartAt = 0; chunkStartTimes = []; chunkDurations = []
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
  activeIdx.value = -1
  playerOpen.value = false
}

watch(activeRegion, () => { if (playerOpen.value) stopPlayback() })
onUnmounted(() => {
  sessionId++
  _clearTimers()
  _stopRaf()
  if (audioCtx) { audioCtx.close(); audioCtx = null }
})

// ── Regions / colours ────────────────────────────────────────────────────────
const REGIONS = [
  { key: 'all',     label: 'All News',  flag: '🗞️' },
  { key: 'world',   label: 'World',     flag: '🌍' },
  { key: 'usa',     label: 'USA',       flag: '🇺🇸' },
  { key: 'india',   label: 'India',     flag: '🇮🇳' },
  { key: 'odisha',  label: 'Odisha',    flag: '🏛️' },
  { key: 'ai',      label: 'AI',        flag: '🤖' },
  { key: 'finance', label: 'Finance',   flag: '💹' },
  { key: 'sports',  label: 'Sports',    flag: '🏆' },
]

const REGION_COLORS = {
  world:   'bg-blue-100 text-blue-700',
  usa:     'bg-red-100 text-red-700',
  india:   'bg-orange-100 text-orange-700',
  odisha:  'bg-purple-100 text-purple-700',
  ai:      'bg-violet-100 text-violet-700',
  finance: 'bg-emerald-100 text-emerald-700',
  sports:  'bg-yellow-100 text-yellow-700',
}
const REGION_FLAGS = { world: '🌍', usa: '🇺🇸', india: '🇮🇳', odisha: '🏛️', ai: '🤖', finance: '💹', sports: '🏆' }

const FALLBACK_IMAGES = {
  world:   'https://images.unsplash.com/photo-1521295121783-8a321d551ad2?w=400&q=80', // desk globe
  usa:     'https://images.unsplash.com/photo-1485738422979-f5c462d49f74?w=400&q=80', // Statue of Liberty
  india:   'https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=400&q=80', // Taj Mahal
  odisha:  'https://images.unsplash.com/photo-1597505686823-233a95175f40?w=400&q=80', // Odishan temple
  ai:      'https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=400&q=80', // circuit-board brain
  finance: 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=400&q=80', // candlestick chart
  sports:  'https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=400&q=80', // packed stadium
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
        <!-- Title block — full width on all screens -->
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

          <!-- Listen button — only shown when player is closed -->
          <button v-if="!playerOpen && filtered.length"
            @click="openPlayer"
            class="ml-auto flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold bg-white/10 hover:bg-white/20 text-white border border-white/20 transition-all"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
            </svg>
            Listen to all
          </button>
        </div>

        <!-- Player bar — shown while TTS is active (desktop only; mobile uses fixed bottom bar) -->
        <div v-if="playerOpen" class="mt-3 hidden sm:flex items-center gap-3 bg-white/10 rounded-xl px-4 py-2.5 border border-white/10">
          <!-- Error state -->
          <template v-if="ttsState === 'error'">
            <span class="flex-1 text-xs text-red-300">{{ ttsError }}</span>
            <button @click="openPlayer" class="text-xs text-white/80 underline flex-shrink-0">Retry</button>
            <button @click="stopPlayback" class="flex items-center justify-center w-7 h-7 rounded-lg bg-white/10 hover:bg-rose-500/80 text-white transition-colors flex-shrink-0" title="Close">
              <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
            </button>
          </template>
          <template v-else>
          <!-- Animated waveform bars -->
          <div class="flex items-end gap-0.5 h-4 flex-shrink-0" aria-hidden="true">
            <span v-for="(h, i) in [60,100,70,40]" :key="i"
              class="w-0.5 rounded-full transition-all"
              :class="ttsState === 'playing' ? 'bg-white animate-[bounce_0.6s_ease-in-out_infinite]' : 'bg-white/40'"
              :style="ttsState === 'playing' ? `height:${h}%; animation-delay:${i * 0.15}s` : 'height:4px'">
            </span>
          </div>
          <!-- Progress bar -->
          <div class="flex-1 h-1 bg-white/20 rounded-full overflow-hidden">
            <div class="h-full bg-white rounded-full transition-all duration-200"
              :style="`width:${Math.round(ttsProgress * 100)}%`"></div>
          </div>
          <!-- Chunk counter -->
          <span class="text-xs text-white/60 flex-shrink-0 tabular-nums">
            {{ ttsChunkIdx + 1 }}/{{ ttsTotalChunks }}
          </span>
          <!-- Pause / Resume -->
          <button @click="ttsState === 'loading' ? null : togglePlayPause()"
            class="flex items-center justify-center w-7 h-7 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors flex-shrink-0"
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
            class="flex items-center justify-center w-7 h-7 rounded-lg bg-white/10 hover:bg-rose-500/80 text-white transition-colors flex-shrink-0"
            title="Stop">
            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <rect x="4" y="4" width="16" height="16" rx="2"/>
            </svg>
          </button>
          </template>
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

              <!-- Title -->
              <h2 class="text-base sm:text-lg font-bold text-gray-900 leading-snug mb-3">
                {{ item.title }}
              </h2>

              <!-- Full summary — no clamp -->
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

    <Footer />

    <!-- Mobile fixed bottom bar — stays visible when news items auto-scroll the page -->
    <Teleport to="body">
      <div v-if="playerOpen" class="sm:hidden fixed bottom-0 left-0 right-0 z-50 shadow-2xl bg-slate-900 border-t border-slate-700">
        <div class="px-4 pt-2 pb-4">
          <!-- Header row -->
          <div class="flex items-center gap-2 mb-2">
            <div class="flex items-end gap-0.5 h-4 flex-shrink-0" aria-hidden="true">
              <span v-for="(h, i) in [60,100,70,40]" :key="i"
                class="w-0.5 rounded-full transition-all"
                :class="ttsState === 'playing' ? 'bg-white animate-[bounce_0.6s_ease-in-out_infinite]' : 'bg-white/40'"
                :style="ttsState === 'playing' ? `height:${h}%; animation-delay:${i * 0.15}s` : 'height:4px'">
              </span>
            </div>
            <span class="text-xs font-semibold text-white truncate flex-1">
              {{ ttsState === 'loading' ? 'Loading…' : ttsState === 'error' ? 'Error' : 'Now playing news' }}
            </span>
            <span class="text-xs text-white/60 flex-shrink-0 tabular-nums">{{ ttsChunkIdx + 1 }}/{{ ttsTotalChunks }}</span>
            <button @click="stopPlayback" class="flex-shrink-0 ml-2 text-white/60 hover:text-white" title="Stop">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <!-- Error state -->
          <div v-if="ttsState === 'error'" class="flex items-center gap-2">
            <span class="text-xs text-red-400 flex-1">{{ ttsError }}</span>
            <button @click="openPlayer" class="text-xs text-white/80 underline flex-shrink-0">Retry</button>
          </div>
          <template v-else>
            <!-- Progress bar -->
            <div class="h-1 bg-white/20 rounded-full overflow-hidden mb-2">
              <div class="h-full bg-white rounded-full transition-all duration-200" :style="`width:${Math.round(ttsProgress * 100)}%`"></div>
            </div>
            <!-- Controls -->
            <div class="flex items-center gap-2">
              <button @click="stopPlayback"
                class="flex items-center justify-center w-8 h-8 rounded-lg bg-white/10 hover:bg-rose-500/80 text-white transition-colors"
                title="Stop">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
              </button>
              <button @click="ttsState === 'loading' ? null : togglePlayPause()"
                class="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-colors flex-1 justify-center bg-white/10 hover:bg-white/20 text-white"
                :class="ttsState === 'loading' ? 'cursor-wait opacity-50' : ''">
                <svg v-if="ttsState === 'loading'" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
                <svg v-else-if="ttsState === 'playing'" class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/></svg>
                <svg v-else class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                {{ ttsState === 'loading' ? 'Loading…' : ttsState === 'playing' ? 'Pause' : 'Resume' }}
              </button>
            </div>
          </template>
        </div>
      </div>
    </Teleport>
  </div>
</template>
