<script setup>
import { onMounted, onUnmounted, ref, nextTick } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import api from '../api'
import { format } from 'date-fns'

const route = useRoute()
const story = ref(null)
const error = ref(null)

const GENRE_ICONS = {
  Adventure: '🏕️', Fantasy: '🧙', Mystery: '🔍', Fable: '🦁',
  'Science Fiction': '🚀', 'Historical Fiction': '🏛️', Mythology: '⚡',
}

// ── TTS player ────────────────────────────────────────────────────────────────
const ttsState       = ref('idle')   // idle | loading | playing | paused | error
const ttsProgress    = ref(0)        // 0–1 across all chunks
const ttsChunkIdx    = ref(0)
const ttsTotalChunks = ref(0)
const playerOpen     = ref(false)
const ttsError       = ref('')

let sessionId      = 0
let audioEl        = null
let currentBlobUrl = null
let resolveChunk   = null
let chunkFetches   = []
let chunkBlobs     = []     // populated once each fetch resolves; index presence = resolved
let chunkItems     = []     // { text, element: DOMElement | null }[]

// Build chunks from rendered DOM elements so we can highlight them while reading.
// Split text only when it exceeds maxLen, always cutting at a sentence boundary.
function splitAtSentences(text, el, items, maxLen = 1000) {
  if (text.length <= maxLen) { items.push({ text, element: el }); return }
  // Collect positions just after each sentence-ending punctuation + whitespace
  const ends = []
  for (const m of text.matchAll(/[.!?]+\s+/g)) ends.push(m.index + m[0].length)
  let start = 0
  while (start < text.length) {
    const remaining = text.slice(start)
    if (remaining.length <= maxLen) { items.push({ text: remaining.trim(), element: el }); break }
    // Find the last sentence boundary at or before start + maxLen
    const cutPos = ends.filter(e => e > start && e <= start + maxLen).at(-1)
    const cut = cutPos ?? (start + maxLen)
    items.push({ text: text.slice(start, cut).trim(), element: el })
    start = cut
  }
}

function buildDOMChunks() {
  const items = []

  if (story.value?.title) {
    items.push({ text: story.value.title, element: null })
  }

  // Excerpt block (has class story-excerpt added in template)
  const excerptEl = document.querySelector('.story-excerpt')
  if (excerptEl && story.value?.excerpt) {
    items.push({ text: story.value.excerpt, element: excerptEl })
  }

  // Story body – every block-level text element; keep full paragraphs as one chunk
  const contentEl = document.querySelector('.story-content')
  if (contentEl) {
    const blocks = Array.from(contentEl.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li'))
    blocks.forEach(el => {
      const text = (el.textContent || '').trim()
      if (text.length < 5) return
      splitAtSentences(text, el, items)
    })
  }

  return items
}

// Fetch one chunk with one automatic retry (500 ms delay) on transient failures.
function fetchChunkCached(idx) {
  if (!chunkFetches[idx]) {
    const doFetch = () =>
      api.post('/tts', { text: chunkItems[idx].text, type: 'story' }, { responseType: 'blob', timeout: 90_000 })
         .then(r => { chunkBlobs[idx] = r.data; return r.data })
    chunkFetches[idx] = doFetch()
      .catch(() => new Promise(res => setTimeout(res, 500)).then(doFetch))
      .catch(() => { chunkBlobs[idx] = null; return null })
  }
}

// Add highlight class to the paragraph being read; auto-scroll if off-screen.
function highlightChunk(idx) {
  document.querySelectorAll('.tts-reading').forEach(el => el.classList.remove('tts-reading'))
  const item = chunkItems[idx]
  if (!item?.element) return
  item.element.classList.add('tts-reading')
  const rect = item.element.getBoundingClientRect()
  const navH = 80  // sticky navbar (~64px) + margin
  if (rect.top < navH || rect.bottom > window.innerHeight - 80) {
    item.element.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function clearHighlight() {
  document.querySelectorAll('.tts-reading').forEach(el => el.classList.remove('tts-reading'))
}

function ensureAudioEl() {
  if (!audioEl) {
    audioEl = new Audio()
    audioEl.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA='
    const p = audioEl.play(); if (p) p.catch(() => {})
    audioEl.pause()
    audioEl.src = ''
  }
  return audioEl
}

function playChunk(blob, chunkIdx) {
  return new Promise(resolve => {
    resolveChunk = resolve
    const el = ensureAudioEl()
    const url = URL.createObjectURL(blob)
    currentBlobUrl = url
    el.src = url
    el.ontimeupdate = () => {
      if (!el.duration) return
      ttsProgress.value = (chunkIdx + el.currentTime / el.duration) / ttsTotalChunks.value
    }
    const cleanup = (reason) => {
      URL.revokeObjectURL(url)
      if (currentBlobUrl === url) currentBlobUrl = null
      el.ontimeupdate = null; el.onended = null; el.onerror = null
      resolveChunk = null
      resolve(reason)
    }
    el.onended = () => cleanup('ended')
    el.onerror = () => cleanup('error')
    el.play().catch(() => cleanup('error'))
  })
}

async function runFrom(startIdx, session) {
  let failures = 0
  for (let i = startIdx; i < ttsTotalChunks.value; i++) {
    if (session !== sessionId) return
    ttsChunkIdx.value = i

    // Fetch this chunk + 5 ahead so audio is always buffered well in advance
    fetchChunkCached(i)
    for (let p = 1; p <= 5; p++) {
      if (i + p < ttsTotalChunks.value) fetchChunkCached(i + p)
    }

    // Only show the loading spinner if the blob isn't already cached
    if (!(i in chunkBlobs)) {
      ttsState.value = 'loading'
      await chunkFetches[i]
    }
    if (session !== sessionId) return

    const blob = chunkBlobs[i]
    if (!blob) {
      failures++
      console.warn(`[TTS] chunk ${i} failed (${failures} consecutive)`)
      if (failures >= 3) {
        clearHighlight()
        ttsState.value = 'idle'
        ttsProgress.value = 0
        ttsError.value = 'Audio unavailable — please try again later.'
        return
      }
      continue
    }
    failures = 0

    // Only highlight and scroll once we know audio is ready to play
    highlightChunk(i)
    ttsState.value = 'playing'
    await playChunk(blob, i)
    if (session !== sessionId) return
  }
  clearHighlight()
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
}

function cancelCurrentChunk() {
  if (audioEl) { audioEl.pause(); audioEl.src = '' }
  if (currentBlobUrl) { URL.revokeObjectURL(currentBlobUrl); currentBlobUrl = null }
  if (resolveChunk) { resolveChunk('cancelled'); resolveChunk = null }
}

async function openPlayer() {
  playerOpen.value = true
  ttsError.value = ''
  if (ttsState.value !== 'idle') return

  chunkItems = buildDOMChunks()
  if (!chunkItems.length) return

  ttsTotalChunks.value = chunkItems.length
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
  chunkFetches = []
  chunkBlobs = []

  ensureAudioEl()
  // Pre-warm first 5 chunks immediately so playback never has to wait
  for (let k = 0; k < Math.min(5, chunkItems.length); k++) fetchChunkCached(k)

  ttsState.value = 'loading'
  const session = ++sessionId
  await runFrom(0, session)
}

function togglePlayPause() {
  if (!audioEl) return
  if (ttsState.value === 'playing') { audioEl.pause(); ttsState.value = 'paused' }
  else if (ttsState.value === 'paused') { audioEl.play(); ttsState.value = 'playing' }
}

function stopPlayback() {
  sessionId++
  cancelCurrentChunk()
  clearHighlight()
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
}

async function seekTo(fraction) {
  if (!ttsTotalChunks.value || !chunkItems.length) return
  const target = Math.max(0, Math.min(Math.floor(fraction * ttsTotalChunks.value), ttsTotalChunks.value - 1))
  const session = ++sessionId
  cancelCurrentChunk()
  clearHighlight()
  ttsProgress.value = target / ttsTotalChunks.value
  ttsChunkIdx.value = target
  ttsState.value = 'loading'
  await new Promise(r => setTimeout(r, 0))
  if (session !== sessionId) return
  await runFrom(target, session)
}

function closePlayer() {
  sessionId++
  cancelCurrentChunk()
  clearHighlight()
  if (audioEl) { audioEl.src = ''; audioEl = null }
  chunkFetches = []
  chunkBlobs = []
  chunkItems = []
  ttsTotalChunks.value = 0
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
  playerOpen.value = false
}
// ── end TTS ───────────────────────────────────────────────────────────────────

onUnmounted(() => {
  sessionId++
  cancelCurrentChunk()
  clearHighlight()
  if (audioEl) { audioEl.src = ''; audioEl = null }
})

onMounted(async () => {
  try {
    const res = await api.get(`/stories/${route.params.slug}`)
    story.value = res.data
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
  <div class="min-h-screen bg-gradient-to-b from-indigo-50/30 to-white" :class="playerOpen ? 'pb-20 sm:pb-0' : ''">
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

    <article v-else class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">

      <!-- Breadcrumb -->
      <nav class="flex items-center gap-2 text-sm text-gray-400 mb-6">
        <RouterLink to="/" class="hover:text-indigo-600 transition-colors">Home</RouterLink>
        <span>›</span>
        <RouterLink to="/story" class="hover:text-indigo-600 transition-colors">Stories</RouterLink>
        <span>›</span>
        <span class="text-gray-600 truncate max-w-xs">{{ story.title }}</span>
      </nav>

      <!-- Genre + age + read-time badges -->
      <div class="flex items-center gap-3 mb-4 flex-wrap">
        <span v-if="story.genre" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-indigo-100 text-indigo-700">
          {{ GENRE_ICONS[story.genre] || '📖' }} {{ story.genre }}
        </span>
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-pink-100 text-pink-700">
          👦👧 Ages {{ story.ageGroup || '8–15' }}
        </span>
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-amber-100 text-amber-700">
          ⏱ {{ story.readTime || '20' }} min read
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

      <!-- Mobile: Listen button (only when player is closed; fixed bottom bar takes over when open) -->
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
      <div v-if="story.excerpt" class="story-excerpt bg-indigo-50 border-l-4 border-indigo-400 rounded-r-xl px-5 py-4 mb-8 text-indigo-800 text-lg italic leading-relaxed">
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

            <p v-if="ttsError" class="text-xs text-center text-red-500">{{ ttsError }}</p>
            <p v-else class="text-xs text-center text-gray-400">Powered by local AI</p>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Mobile: fixed bottom player bar (replaces the inline player card) -->
    <Teleport to="body">
      <div v-if="playerOpen && story" class="sm:hidden fixed bottom-0 inset-x-0 z-50 bg-white/95 backdrop-blur-sm border-t border-gray-200 shadow-2xl">
        <div class="px-4 py-3 flex items-center gap-3">
          <!-- Waveform -->
          <div class="flex items-end gap-0.5 h-5 flex-shrink-0" aria-hidden="true">
            <span v-for="i in 4" :key="i" class="w-1 rounded-full bg-indigo-500"
              :class="ttsState === 'playing' ? 'tts-bar' : 'h-1 opacity-40'"
              :style="ttsState === 'playing' ? `animation-delay:${i * 80}ms` : ''"></span>
          </div>
          <!-- Progress bar (tappable) -->
          <div class="flex-1 relative h-2 bg-gray-200 rounded-full cursor-pointer"
            @click="e => { const r = e.currentTarget.getBoundingClientRect(); seekTo((e.clientX - r.left) / r.width) }">
            <div class="h-full bg-indigo-500 rounded-full transition-all duration-200"
              :style="`width:${Math.round(ttsProgress * 100)}%`"></div>
          </div>
          <!-- Counter -->
          <span class="text-xs text-gray-500 flex-shrink-0 tabular-nums">{{ ttsChunkIdx + 1 }}/{{ ttsTotalChunks }}</span>
          <!-- Play/Pause -->
          <button @click="ttsState === 'loading' ? null : togglePlayPause()"
            class="w-9 h-9 rounded-full flex items-center justify-center text-white transition-colors flex-shrink-0"
            :class="ttsState === 'loading' ? 'bg-gray-200 cursor-wait' : 'bg-indigo-600 hover:bg-indigo-700'">
            <svg v-if="ttsState === 'loading'" class="w-4 h-4 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            <svg v-else-if="ttsState === 'playing'" class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
            </svg>
            <svg v-else class="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z"/>
            </svg>
          </button>
          <!-- Close -->
          <button @click="closePlayer" class="w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 flex-shrink-0">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
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

/* Highlight paragraphs inside v-html while they're being read */
:deep(.tts-reading) {
  background-color: rgba(79, 70, 229, 0.1);
  border-radius: 6px;
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.12);
  transition: background-color 0.3s ease, box-shadow 0.3s ease;
}

/* Highlight the excerpt block when it's being read */
.story-excerpt.tts-reading {
  background-color: rgba(79, 70, 229, 0.15) !important;
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.2);
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
