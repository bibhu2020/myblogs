<script setup>
import { onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import api from '../api'
import { format } from 'date-fns'
import { useWakeLock } from '../composables/useWakeLock'
// highlight.js is loaded lazily only when code blocks are present in the story

const route = useRoute()
const story = ref(null)
const error = ref(null)

const CATEGORY_ICONS = { AI: '🤖', Robotics: '🦾', Quantum: '⚛️' }
const GENRE_ICONS = { Horror: '🕯️', 'Sci-Fi': '🚀', Thriller: '🔪' }

// ── TTS player ────────────────────────────────────────────────────────────────
const ttsState       = ref('idle')   // idle | loading | playing | paused | error
const ttsProgress    = ref(0)        // 0–1 across all chunks
const ttsChunkIdx    = ref(0)
const ttsTotalChunks = ref(0)
const ttsError       = ref('')
const playerOpen     = ref(false)

const { acquireWakeLock, releaseWakeLock } = useWakeLock()
watch(ttsState, v => v === 'playing' ? acquireWakeLock() : releaseWakeLock())

let sessionId             = 0
let audioCtx              = null
let nextStartAt           = 0
let highlightTimers       = []
let rafId                 = null
let chunkStartTimes       = []
let chunkDurations        = []
let chunkFetches          = []
let chunkTexts            = []
let chunkElements         = []
let lastHighlightedEl     = null
let speculativeTitleFetch = null

function buildChunksWithDOM(contentSelector, title, maxLen = 300) {
  const chunks = []
  const elements = []

  if (title) { chunks.push(title); elements.push(null) }

  const contentEl = document.querySelector(contentSelector)
  if (!contentEl) return { chunks, elements }

  const nodes = contentEl.querySelectorAll('p, h2, h3, h4, blockquote, li')
  let accText = ''
  let accEl = null

  function flush() {
    if (accText) { chunks.push(accText); elements.push(accEl); accText = ''; accEl = null }
  }
  function addSplit(text, el) {
    let rem = text
    while (rem.length > 0) {
      if (rem.length <= maxLen) { chunks.push(rem); elements.push(el); break }
      let cut = rem.lastIndexOf('. ', maxLen)
      if (cut < maxLen * 0.4) cut = rem.lastIndexOf(' ', maxLen)
      if (cut < 0) cut = maxLen; else cut += 1
      chunks.push(rem.slice(0, cut).trim()); elements.push(el)
      rem = rem.slice(cut).trim()
    }
  }

  for (const node of nodes) {
    const text = (node.textContent || '').trim()
    if (!text) continue
    if (!accText) {
      if (text.length > maxLen) { addSplit(text, node) }
      else { accText = text; accEl = node }
    } else if (accText.length + 1 + text.length <= maxLen) {
      accText += ' ' + text
    } else {
      flush()
      if (text.length > maxLen) { addSplit(text, node) }
      else { accText = text; accEl = node }
    }
  }
  flush()
  return { chunks, elements }
}

function clearHighlight() {
  if (lastHighlightedEl) {
    lastHighlightedEl.style.removeProperty('background-color')
    lastHighlightedEl.style.removeProperty('border-radius')
    lastHighlightedEl.style.removeProperty('transition')
    lastHighlightedEl = null
  }
}

function highlightChunk(i) {
  clearHighlight()
  const el = chunkElements[i]
  if (!el) return
  el.style.backgroundColor = 'rgba(79, 70, 229, 0.10)'
  el.style.borderRadius = '4px'
  el.style.transition = 'background-color 0.35s ease'
  lastHighlightedEl = el
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function fetchOneChunk(text) {
  return api.post('/tts', { text, style: 'story' }, { responseType: 'blob', timeout: 90_000 })
    .then(r => r.data)
    .catch(e => ({ _ttsError: e?.response?.data?.message || e?.message || 'TTS unavailable' }))
}

function ensureAudioCtx() {
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
    const ms = Math.max(0, (startAt - ctx.currentTime) * 1000)
    highlightTimers.push(setTimeout(() => highlightChunk(i), ms))
    return source
  } catch { return null }
}

async function runFrom(startIdx, session) {
  for (let i = startIdx; i < ttsTotalChunks.value; i++) {
    if (session !== sessionId) return
    ttsChunkIdx.value = i
    if (i === startIdx) ttsState.value = 'loading'

    if (!chunkFetches[i]) chunkFetches[i] = fetchOneChunk(chunkTexts[i])
    for (let p = 1; p <= 4; p++) {
      const ahead = i + p
      if (ahead < ttsTotalChunks.value && !chunkFetches[ahead])
        chunkFetches[ahead] = fetchOneChunk(chunkTexts[ahead])
    }
    const result = await chunkFetches[i]
    if (session !== sessionId) return
    if (!result || result._ttsError) {
      clearHighlight()
      ttsState.value = 'error'
      ttsError.value = result?._ttsError || 'TTS unavailable'
      return
    }
    const source = await _decodeAndSchedule(result, i)
    if (session !== sessionId) return
    if (!source) {
      clearHighlight()
      ttsState.value = 'error'
      ttsError.value = 'Audio decode failed'
      return
    }
    if (i === startIdx) { ttsState.value = 'playing'; _startRaf() }
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
  clearHighlight()
  _stopRaf()
  _clearTimers()
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
}

async function openPlayer() {
  playerOpen.value = true
  ttsError.value = ''
  if (ttsState.value !== 'idle' && ttsState.value !== 'error') return
  ttsState.value = 'idle'
  ensureAudioCtx()

  await nextTick()
  const { chunks, elements } = buildChunksWithDOM('.story-content', story.value.title, 200)
  if (!chunks.length) return

  chunkTexts = chunks
  chunkElements = elements
  ttsTotalChunks.value = chunks.length
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
  chunkFetches = new Array(chunks.length).fill(null)
  nextStartAt = audioCtx.currentTime + 0.05
  chunkStartTimes = []
  chunkDurations = []
  _clearTimers()

  if (speculativeTitleFetch && chunks[0] === story.value.title) {
    chunkFetches[0] = speculativeTitleFetch
  }
  speculativeTitleFetch = null
  for (let k = 0; k < Math.min(4, chunks.length); k++)
    if (!chunkFetches[k]) chunkFetches[k] = fetchOneChunk(chunkTexts[k])

  ttsState.value = 'loading'
  const session = ++sessionId
  await runFrom(0, session)
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
  clearHighlight()
  if (audioCtx) { audioCtx.close(); audioCtx = null }
  nextStartAt = 0; chunkStartTimes = []; chunkDurations = []
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
}

async function seekTo(fraction) {
  if (!ttsTotalChunks.value || !chunkTexts.length) return
  const target = Math.max(0, Math.min(Math.floor(fraction * ttsTotalChunks.value), ttsTotalChunks.value - 1))
  _clearTimers()
  _stopRaf()
  clearHighlight()
  if (audioCtx) { audioCtx.close(); audioCtx = null }
  nextStartAt = 0; chunkStartTimes = []; chunkDurations = []
  ttsProgress.value = target / ttsTotalChunks.value
  ttsChunkIdx.value = target
  ttsState.value = 'loading'
  ensureAudioCtx()
  const session = ++sessionId
  await new Promise(r => setTimeout(r, 0))
  if (session !== sessionId) return
  await runFrom(target, session)
}

function closePlayer() {
  sessionId++
  _clearTimers()
  _stopRaf()
  clearHighlight()
  if (audioCtx) { audioCtx.close(); audioCtx = null }
  nextStartAt = 0
  chunkFetches = []; chunkTexts = []; chunkElements = []
  chunkStartTimes = []; chunkDurations = []
  ttsTotalChunks.value = 0
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
  playerOpen.value = false
}
// ── end TTS ───────────────────────────────────────────────────────────────────

onUnmounted(() => {
  sessionId++
  _clearTimers()
  _stopRaf()
  if (audioCtx) { audioCtx.close(); audioCtx = null }
  speculativeTitleFetch = null
})

onMounted(async () => {
  try {
    const res = await api.get(`/stories/${route.params.slug}`)
    story.value = res.data
    if (story.value?.title) speculativeTitleFetch = fetchOneChunk(story.value.title)
    await nextTick()
    const codeBlocks = document.querySelectorAll('.story-content pre code')
    if (codeBlocks.length) {
      const { default: hljs } = await import('highlight.js')
      codeBlocks.forEach(el => hljs.highlightElement(el))
    }
  } catch {
    error.value = 'Story not found.'
  }
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-b from-indigo-50/30 to-white">
    <Navbar />

    <div v-if="error" class="max-w-2xl mx-auto px-4 py-24 text-center">
      <div class="text-5xl mb-4">😔</div>
      <h1 class="text-2xl font-bold text-gray-700 mb-2">Story Not Found</h1>
      <p class="text-gray-400 mb-8">{{ error }}</p>
      <RouterLink to="/story" class="inline-flex items-center gap-2 bg-indigo-600 text-white px-6 py-3 rounded-full font-medium hover:bg-indigo-700 transition-colors">
        ← Back to Stories
      </RouterLink>
    </div>

    <div v-else-if="!story" class="max-w-3xl mx-auto px-4 py-16 animate-pulse">
      <div class="h-8 bg-gray-200 rounded w-3/4 mx-auto mb-4"></div>
      <div class="aspect-[16/7] rounded-2xl bg-gray-200 mb-8"></div>
      <div class="space-y-3">
        <div class="h-4 bg-gray-100 rounded w-full"></div>
        <div class="h-4 bg-gray-100 rounded w-5/6"></div>
        <div class="h-4 bg-gray-100 rounded w-4/6"></div>
      </div>
    </div>

    <article v-else class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10" :class="playerOpen ? 'pb-28 sm:pb-10' : ''">

      <!-- Breadcrumb -->
      <nav class="flex items-center gap-2 text-sm text-gray-400 mb-6">
        <RouterLink to="/" class="hover:text-indigo-600 transition-colors">Home</RouterLink>
        <span>›</span>
        <RouterLink to="/story" class="hover:text-indigo-600 transition-colors">Stories</RouterLink>
        <span>›</span>
        <span class="text-gray-600 truncate max-w-xs">{{ story.title }}</span>
      </nav>

      <!-- Category + genre + age + read-time badges -->
      <div class="flex items-center gap-3 mb-4 flex-wrap">
        <span v-if="story.category" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-indigo-100 text-indigo-700">
          {{ CATEGORY_ICONS[story.category] || '📖' }} {{ story.category }}
        </span>
        <span v-if="story.genre" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-violet-100 text-violet-700">
          {{ GENRE_ICONS[story.genre] || '📖' }} {{ story.genre }}
        </span>
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-pink-100 text-pink-700">
          🎓 {{ story.ageGroup || 'High School+' }}
        </span>
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-amber-100 text-amber-700">
          ⏱ {{ story.readTime || '7' }} min read
        </span>
      </div>

      <!-- Title -->
      <h1 class="text-3xl sm:text-4xl font-bold text-gray-900 mb-3 leading-tight" style="font-family:'Playfair Display',serif">
        {{ story.title }}
      </h1>

      <!-- Meta -->
      <div class="flex items-center gap-3 text-sm text-gray-400 mb-6 pb-6 border-b border-gray-100">
        <span>By <strong class="text-gray-600">{{ story.authorName || 'Meridian Storyteller' }}</strong></span>
        <span>·</span>
        <span>{{ format(new Date(story.createdAt), 'MMMM d, yyyy') }}</span>
        <span>·</span>
        <span>{{ story.views }} readers</span>
      </div>

      <!-- Mobile TTS trigger button — sm:hidden; player itself is Teleported to bottom -->
      <div v-if="!playerOpen" class="sm:hidden mb-6">
        <button @click="openPlayer"
          class="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold transition-colors w-full justify-center">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0014 7.97v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
          </svg>
          Listen to this story
        </button>
      </div>

      <!-- Featured image -->
      <div v-if="story.featuredImage" class="mb-8 rounded-2xl overflow-hidden shadow-md">
        <img :src="story.featuredImage" :alt="story.title" class="w-full object-cover max-h-[480px]" />
      </div>

      <!-- Excerpt / hook -->
      <div v-if="story.excerpt" class="bg-indigo-50 border-l-4 border-indigo-400 rounded-r-xl px-5 py-4 mb-8 text-indigo-800 text-lg italic leading-relaxed">
        {{ story.excerpt }}
      </div>

      <!-- Story content -->
      <div
        class="story-content prose prose-lg max-w-none
               prose-headings:font-bold prose-headings:text-gray-900
               prose-p:text-gray-700 prose-p:leading-[1.9]
               prose-blockquote:border-indigo-400 prose-blockquote:bg-indigo-50/50 prose-blockquote:rounded-r-lg
               prose-img:rounded-xl prose-img:shadow-md
               prose-figure:my-8"
        style="font-size: 1.125rem; font-family: Georgia, 'Times New Roman', serif"
        v-html="story.content"
      ></div>

      <!-- Moral lesson -->
      <div v-if="story.moralLesson" class="mt-10 bg-gradient-to-r from-amber-50 to-yellow-50 border border-amber-200 rounded-2xl px-6 py-5">
        <div class="text-amber-600 font-bold text-sm uppercase tracking-wider mb-2">✨ The Lesson</div>
        <p class="text-amber-900 text-base leading-relaxed italic">{{ story.moralLesson }}</p>
      </div>

      <!-- Footer nav -->
      <div class="mt-12 pt-8 border-t border-gray-100 flex items-center justify-between">
        <RouterLink to="/story" class="inline-flex items-center gap-2 text-indigo-600 font-medium hover:text-indigo-800 transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
          All Stories
        </RouterLink>
        <span class="text-gray-400 text-sm">{{ story.views }} readers</span>
      </div>
    </article>

    <!-- Mobile TTS fixed bottom bar -->
    <Teleport to="body">
      <div v-if="playerOpen && story" class="sm:hidden fixed bottom-0 left-0 right-0 z-50 shadow-2xl bg-white border-t border-indigo-100">
        <div class="px-4 pt-2 pb-4">
          <div class="flex items-center gap-2 mb-2">
            <div class="flex items-end gap-0.5 h-4 flex-shrink-0" aria-hidden="true">
              <span v-for="i in 4" :key="i" class="w-1 rounded-full bg-indigo-500"
                :class="ttsState === 'playing' ? 'tts-bar' : 'h-1 opacity-40'"
                :style="ttsState === 'playing' ? `animation-delay:${i * 80}ms` : ''"></span>
            </div>
            <p class="text-xs font-semibold text-gray-800 truncate flex-1">{{ story.title }}</p>
            <span v-if="ttsTotalChunks" class="text-xs text-gray-500 flex-shrink-0">{{ ttsChunkIdx + 1 }}/{{ ttsTotalChunks }}</span>
            <button @click="closePlayer" class="flex-shrink-0 ml-2 text-gray-400 hover:text-gray-600" title="Close">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <div v-if="ttsState === 'error'" class="flex items-center gap-2 mt-1">
            <span class="text-xs text-red-600 flex-1">Audio unavailable — {{ ttsError }}</span>
            <button @click="openPlayer" class="text-xs text-indigo-600 underline flex-shrink-0">Retry</button>
          </div>
          <template v-else>
            <input type="range" min="0" max="100"
              :value="Math.round(ttsProgress * 100)"
              :disabled="ttsState === 'loading'"
              class="tts-slider w-full mb-2"
              @change="seekTo($event.target.value / 100)" />
            <div class="flex items-center gap-2">
              <button @click="stopPlayback" :disabled="ttsState === 'idle' || ttsState === 'loading'"
                class="flex items-center justify-center w-8 h-8 rounded-lg transition-colors"
                :class="ttsState === 'idle' || ttsState === 'loading' ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100'"
                title="Stop">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
              </button>
              <button @click="ttsState === 'loading' ? null : togglePlayPause()"
                class="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-colors flex-1 justify-center"
                :class="ttsState === 'loading' ? 'bg-gray-100 text-gray-400 cursor-wait' : 'bg-indigo-600 text-white hover:bg-indigo-700'">
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

    <!-- Desktop TTS sliding panel — fixed right side, hidden on mobile -->
    <Teleport to="body">
      <div v-if="story" class="hidden sm:flex fixed right-0 top-1/2 -translate-y-1/2 z-50 items-stretch drop-shadow-2xl">
        <!-- Always-visible tab -->
        <button @click="playerOpen ? closePlayer() : openPlayer()"
          class="flex flex-col items-center justify-center gap-2 w-10 rounded-l-2xl py-5 transition-colors text-white"
          :class="playerOpen ? 'bg-indigo-700' : 'bg-indigo-600 hover:bg-indigo-700'">
          <svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0014 7.97v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
          </svg>
          <span class="text-[10px] font-bold tracking-wider" style="writing-mode:vertical-lr;transform:rotate(180deg)">
            {{ playerOpen ? 'CLOSE' : 'LISTEN' }}
          </span>
        </button>

        <!-- Sliding player panel -->
        <div class="overflow-hidden transition-all duration-300 ease-in-out"
          :style="playerOpen ? 'width:288px' : 'width:0'">
          <div class="w-[288px] h-full flex flex-col p-5 gap-4 bg-white border-l border-indigo-100">

            <!-- Header -->
            <div class="flex items-start justify-between gap-2">
              <div>
                <p class="text-xs font-semibold uppercase tracking-wider mb-0.5 text-indigo-500">Now reading</p>
                <p class="text-sm font-bold leading-snug line-clamp-2 text-gray-900">{{ story.title }}</p>
              </div>
              <button @click="closePlayer" class="flex-shrink-0 mt-0.5 text-gray-300 hover:text-gray-600" title="Close">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>

            <!-- Waveform animation -->
            <div class="flex items-end justify-center gap-1 h-10" aria-hidden="true">
              <span v-for="i in 12" :key="i"
                class="w-1.5 rounded-full bg-indigo-400"
                :class="ttsState === 'playing' ? 'tts-bar' : 'h-1.5 opacity-30'"
                :style="ttsState === 'playing' ? `animation-delay:${i * 60}ms` : ''"></span>
            </div>

            <!-- Error state -->
            <div v-if="ttsState === 'error'" class="text-center">
              <p class="text-xs text-red-500 mb-2">{{ ttsError }}</p>
              <button @click="openPlayer" class="text-xs text-indigo-600 underline">Retry</button>
            </div>

            <!-- Seek slider -->
            <div>
              <input type="range" min="0" max="100"
                :value="Math.round(ttsProgress * 100)"
                :disabled="ttsState === 'loading' || ttsState === 'idle'"
                class="tts-slider w-full"
                @change="seekTo($event.target.value / 100)" />
              <div class="flex justify-between mt-1.5 text-xs text-gray-500">
                <span v-if="ttsTotalChunks">Segment {{ ttsChunkIdx + 1 }} / {{ ttsTotalChunks }}</span>
                <span v-else>—</span>
                <span>{{ Math.round(ttsProgress * 100) }}%</span>
              </div>
            </div>

            <!-- Controls -->
            <div class="flex items-center justify-center gap-3">
              <button @click="stopPlayback"
                :disabled="ttsState === 'idle' || ttsState === 'loading'"
                class="flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all"
                :class="ttsState === 'idle' || ttsState === 'loading'
                  ? 'border-gray-200 text-gray-300 cursor-not-allowed'
                  : 'border-gray-300 text-gray-600 hover:border-gray-500 hover:text-gray-800'"
                title="Stop">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
              </button>

              <button @click="ttsState === 'loading' ? null : togglePlayPause()"
                class="flex items-center justify-center w-14 h-14 rounded-full transition-all"
                :class="ttsState === 'loading'
                  ? 'bg-gray-100 text-gray-400 cursor-wait'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700 hover:scale-105 active:scale-95'">
                <svg v-if="ttsState === 'loading'" class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                <svg v-else-if="ttsState === 'playing'" class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
                </svg>
                <svg v-else class="w-6 h-6 ml-1" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
              </button>
            </div>

            <p class="text-xs text-center text-gray-400">Powered by local AI</p>
          </div>
        </div>
      </div>
    </Teleport>

    <Footer />
  </div>
</template>

<style scoped>
@keyframes tts-wave {
  0%, 100% { height: 4px; }
  50%       { height: 24px; }
}
.tts-bar {
  animation: tts-wave 0.8s ease-in-out infinite;
}

.tts-slider {
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 9999px;
  background: #e5e7eb;
  outline: none;
  cursor: pointer;
  background-image: linear-gradient(#4f46e5, #4f46e5);
  background-size: v-bind("Math.round(ttsProgress * 100) + '% 100%'");
  background-repeat: no-repeat;
}
.tts-slider:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.tts-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #4338ca;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0,0,0,.3);
  transition: transform 0.1s;
}
.tts-slider:not(:disabled)::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}
.tts-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #4338ca;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0,0,0,.3);
}
.tts-slider::-moz-range-progress {
  background: #4f46e5;
  height: 6px;
  border-radius: 9999px;
}
</style>
