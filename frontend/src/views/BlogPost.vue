<script setup>
import { onMounted, ref, nextTick, computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useBlogStore } from '../stores/blog'
import { useLayoutStore } from '../stores/layout'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import PostCard from '../components/PostCard.vue'
import api from '../api'
import { format } from 'date-fns'
import hljs from 'highlight.js'

const blog = useBlogStore()
const layout = useLayoutStore()
const ttsTrackColor = computed(() => layout.variant === 'b' ? '#7c3aed' : '#3b82f6')
const ttsThumbColor = computed(() => layout.variant === 'b' ? '#7c3aed' : '#2563eb')
const route = useRoute()
const post = ref(null)
const relatedPosts = ref([])
const comments = ref([])
const commentForm = ref({ authorName: '', authorEmail: '', content: '' })
const commentSubmitted = ref(false)
const galleryOpen = ref(false)
const galleryIndex = ref(0)

// ── TTS player ────────────────────────────────────────────────────────────────
const ttsState       = ref('idle')   // idle | loading | playing | paused
const ttsProgress    = ref(0)        // 0–1 across all chunks
const ttsChunkIdx    = ref(0)        // current chunk index (0-based)
const ttsTotalChunks = ref(0)
const playerOpen     = ref(false)

// Non-reactive internal state
let sessionId     = 0         // incremented on each new playback/seek to invalidate old loops
let currentAudio  = null      // currently playing Audio instance
let currentBlobUrl = null     // blob URL to revoke on cleanup
let resolveChunk  = null      // exposes the current playChunk resolver for instant cancellation
let chunkFetches  = []        // pre-fetch promises — survive seeks so already-fetched chunks are reused

function splitChunks(html, maxLen = 500) {
  const div = document.createElement('div')
  div.innerHTML = html
  const full = (div.textContent || div.innerText || '').trim()
  const chunks = []
  let remaining = full
  while (remaining.length > 0) {
    if (remaining.length <= maxLen) { chunks.push(remaining); break }
    let cut = remaining.lastIndexOf('. ', maxLen)
    if (cut < maxLen * 0.4) cut = remaining.lastIndexOf(' ', maxLen)
    if (cut < 0) cut = maxLen
    else cut += 1
    chunks.push(remaining.slice(0, cut).trim())
    remaining = remaining.slice(cut).trim()
  }
  return chunks.filter(Boolean)
}

// Plays one blob; resolves when the chunk ends, errors, or is externally cancelled
// via resolveChunk('cancelled').
function playChunk(blob, chunkIdx) {
  return new Promise(resolve => {
    resolveChunk = resolve
    const url = URL.createObjectURL(blob)
    currentBlobUrl = url
    const audio = new Audio(url)
    currentAudio = audio

    audio.ontimeupdate = () => {
      if (!audio.duration) return
      ttsProgress.value = (chunkIdx + audio.currentTime / audio.duration) / ttsTotalChunks.value
    }
    const cleanup = (reason) => {
      URL.revokeObjectURL(url)
      if (currentBlobUrl === url) currentBlobUrl = null
      resolveChunk = null
      resolve(reason)
    }
    audio.onended = () => cleanup('ended')
    audio.onerror = () => cleanup('error')
    audio.play().catch(() => cleanup('error'))
  })
}

// Core loop — runs from startIdx to end of chunks for the given session.
async function runFrom(startIdx, session) {
  for (let i = startIdx; i < ttsTotalChunks.value; i++) {
    if (session !== sessionId) return   // a newer session (seek/stop) took over
    ttsChunkIdx.value = i

    const blob = await chunkFetches[i]
    if (session !== sessionId) return
    if (!blob) break

    ttsState.value = 'playing'
    await playChunk(blob, i)
    if (session !== sessionId) return
  }
  // Natural end — reset to idle
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
}

// Cancels the current chunk immediately (unblocks the loop so it can check sessionId)
function cancelCurrentChunk() {
  currentAudio?.pause()
  if (currentBlobUrl) { URL.revokeObjectURL(currentBlobUrl); currentBlobUrl = null }
  currentAudio = null
  if (resolveChunk) { resolveChunk('cancelled'); resolveChunk = null }
}

// Limits concurrent promises to `concurrency` at a time.
function pLimit(concurrency) {
  let active = 0
  const queue = []
  function next() {
    if (active >= concurrency || !queue.length) return
    active++
    const { fn, resolve, reject } = queue.shift()
    fn().then(resolve, reject).finally(() => { active--; next() })
  }
  return fn => new Promise((resolve, reject) => { queue.push({ fn, resolve, reject }); next() })
}

async function openPlayer() {
  playerOpen.value = true
  if (ttsState.value !== 'idle') return

  const bodyChunks = splitChunks(post.value.content)
  // Prepend the post title so TTS reads it first
  const chunks = post.value.title ? [post.value.title, ...bodyChunks] : bodyChunks
  if (!chunks.length) return

  ttsTotalChunks.value = chunks.length
  ttsProgress.value = 0
  ttsChunkIdx.value = 0

  // 3 concurrent requests: 1 synthesizing + 2 queued at the server lock.
  // Keeps the server pipeline full so there's no idle gap between chunks
  // while the next HTTP request is still in-flight from the browser.
  const limit = pLimit(3)
  chunkFetches = chunks.map(text =>
    limit(() =>
      api.post('/tts', { text }, { responseType: 'blob', timeout: 120_000 })
        .then(r => r.data)
        .catch(() => null)
    )
  )

  ttsState.value = 'loading'
  const session = ++sessionId
  await runFrom(0, session)
}

function togglePlayPause() {
  if (!currentAudio) return
  if (ttsState.value === 'playing') { currentAudio.pause(); ttsState.value = 'paused' }
  else if (ttsState.value === 'paused') { currentAudio.play(); ttsState.value = 'playing' }
}

// Stop: halt playback and reset to beginning — player stays open
function stopPlayback() {
  sessionId++             // invalidate running loop
  cancelCurrentChunk()
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
}

// Seek: jump to any position (0–1) using already-prefetched blobs
async function seekTo(fraction) {
  if (!ttsTotalChunks.value || !chunkFetches.length) return
  const target = Math.max(0, Math.min(Math.floor(fraction * ttsTotalChunks.value), ttsTotalChunks.value - 1))

  const session = ++sessionId   // invalidate current loop
  cancelCurrentChunk()

  ttsProgress.value = target / ttsTotalChunks.value
  ttsChunkIdx.value = target
  ttsState.value = 'loading'

  // Small yield so the old loop sees the new sessionId before we start the new one
  await new Promise(r => setTimeout(r, 0))
  if (session !== sessionId) return  // another seek happened in the meantime

  await runFrom(target, session)
}

function closePlayer() {
  sessionId++
  cancelCurrentChunk()
  chunkFetches = []
  ttsTotalChunks.value = 0
  ttsState.value = 'idle'
  ttsProgress.value = 0
  ttsChunkIdx.value = 0
  playerOpen.value = false
}

function applyHighlighting() {
  nextTick(() => {
    document.querySelectorAll('.post-content pre code').forEach(block => {
      hljs.highlightElement(block)
    })
    // also handle bare <pre> without inner <code>
    document.querySelectorAll('.post-content pre:not(:has(code))').forEach(block => {
      const code = document.createElement('code')
      code.innerHTML = block.innerHTML
      block.innerHTML = ''
      block.appendChild(code)
      hljs.highlightElement(code)
    })
  })
}

onMounted(async () => {
  try {
    post.value = await blog.fetchPost(route.params.slug)
    applyHighlighting()
    if (post.value.category) {
      const res = await blog.fetchPosts({ category: post.value.category.slug, limit: 3 })
      relatedPosts.value = res.posts.filter(p => p.id !== post.value.id).slice(0, 3)
    }
    const commRes = await api.get(`/comments/post/${post.value.id}`)
    comments.value = commRes.data
  } catch (e) { console.error(e) }
})

async function submitComment() {
  await api.post(`/comments/post/${post.value.id}`, commentForm.value)
  commentForm.value = { authorName: '', authorEmail: '', content: '' }
  commentSubmitted.value = true
}

function getGallery() {
  if (!post.value?.gallery) return []
  try { return JSON.parse(post.value.gallery) } catch { return [] }
}

function formatDate(d) { return format(new Date(d), 'MMMM d, yyyy') }
</script>

<template>
  <div :class="layout.variant === 'b' ? 'min-h-screen bg-[#080810]' : 'min-h-screen bg-white'">
    <Navbar />

    <div v-if="blog.loading" class="max-w-4xl mx-auto px-4 py-12 animate-pulse">
      <div class="h-8 rounded mb-4 w-3/4" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
      <div class="rounded-2xl aspect-[16/7] mb-8" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
    </div>

    <article v-else-if="post" class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <!-- Category & meta -->
      <div class="mb-6">
        <RouterLink v-if="post.category" :to="`/category/${post.category.slug}`" class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-semibold text-white mb-4" :style="{ background: post.category.color || '#3B82F6' }">
          {{ post.category.icon }} {{ post.category.name }}
        </RouterLink>
        <h1 class="text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight mb-6" :class="layout.variant === 'b' ? 'text-slate-100' : 'text-gray-900'" style="font-family:'Playfair Display',serif">{{ post.title }}</h1>
        <div class="flex flex-wrap items-center gap-4 text-sm" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-500'">
          <div class="flex items-center gap-2">
            <div class="w-9 h-9 rounded-full flex items-center justify-center" :class="layout.variant === 'b' ? 'bg-violet-700' : 'bg-primary-600'"><span class="text-white font-bold">{{ (post.authorName||'A').charAt(0) }}</span></div>
            <div><div class="font-semibold" :class="layout.variant === 'b' ? 'text-slate-200' : 'text-gray-800'">{{ post.authorName }}</div></div>
          </div>
          <span>·</span>
          <span>{{ formatDate(post.createdAt) }}</span>
          <span>·</span>
          <span>{{ post.readTime }} min read</span>
          <span>·</span>
          <span class="flex items-center gap-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
            {{ post.views }} views
          </span>
        </div>
      </div>

      <!-- Mobile TTS player — above hero image -->
      <div class="sm:hidden mb-6">
        <div v-if="!playerOpen">
          <button @click="openPlayer"
            class="flex items-center gap-2 px-4 py-2.5 text-white rounded-xl text-sm font-semibold transition-colors w-full justify-center"
            :class="layout.variant === 'b' ? 'bg-violet-600 hover:bg-violet-700' : 'bg-primary-600 hover:bg-primary-700'">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0014 7.97v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg>
            Listen to this article
          </button>
        </div>
        <div v-else class="rounded-2xl shadow-lg p-4" :class="layout.variant === 'b' ? 'bg-[#0f0f1e] border border-[#1e1e3a]' : 'bg-white border border-gray-100'">
          <!-- Header row -->
          <div class="flex items-center gap-2 mb-3">
            <div class="flex items-end gap-0.5 h-5 flex-shrink-0" aria-hidden="true">
              <span v-for="i in 4" :key="i" class="w-1 rounded-full"
                :class="[ttsState === 'playing' ? 'tts-bar' : 'h-1 opacity-40', layout.variant === 'b' ? 'bg-violet-500' : 'bg-primary-500']"
                :style="ttsState === 'playing' ? `animation-delay:${i * 80}ms` : ''"></span>
            </div>
            <p class="text-sm font-semibold truncate flex-1" :class="layout.variant === 'b' ? 'text-slate-200' : 'text-gray-800'">{{ post.title }}</p>
            <span v-if="ttsTotalChunks" class="text-xs flex-shrink-0" :class="layout.variant === 'b' ? 'text-slate-500' : 'text-gray-400'">{{ ttsChunkIdx + 1 }}/{{ ttsTotalChunks }}</span>
            <button @click="closePlayer" class="flex-shrink-0 ml-1" :class="layout.variant === 'b' ? 'text-slate-500 hover:text-slate-300' : 'text-gray-400 hover:text-gray-600'">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <!-- Seek slider -->
          <input type="range" min="0" max="100"
            :value="Math.round(ttsProgress * 100)"
            :disabled="ttsState === 'loading'"
            class="tts-slider w-full mb-3"
            @change="seekTo($event.target.value / 100)" />
          <!-- Controls -->
          <div class="flex items-center gap-2">
            <!-- Stop -->
            <button @click="stopPlayback" :disabled="ttsState === 'idle' || ttsState === 'loading'"
              class="flex items-center justify-center w-8 h-8 rounded-lg transition-colors"
              :class="ttsState === 'idle' || ttsState === 'loading'
                ? (layout.variant === 'b' ? 'text-slate-700 cursor-not-allowed' : 'text-gray-300 cursor-not-allowed')
                : (layout.variant === 'b' ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-800' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100')"
              title="Stop">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
            </button>
            <!-- Play / Pause -->
            <button @click="ttsState === 'loading' ? null : togglePlayPause()"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex-1 justify-center"
              :class="ttsState === 'loading'
                ? (layout.variant === 'b' ? 'bg-slate-800 text-slate-500 cursor-wait' : 'bg-gray-100 text-gray-400 cursor-wait')
                : (layout.variant === 'b' ? 'bg-violet-600 text-white hover:bg-violet-700' : 'bg-primary-600 text-white hover:bg-primary-700')">
              <svg v-if="ttsState === 'loading'" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
              <svg v-else-if="ttsState === 'playing'" class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/></svg>
              <svg v-else class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
              {{ ttsState === 'loading' ? 'Loading…' : ttsState === 'playing' ? 'Pause' : 'Resume' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Featured Image -->
      <div v-if="post.featuredImage" class="rounded-3xl overflow-hidden aspect-[16/7] mb-10">
        <img :src="post.featuredImage" :alt="post.title" class="w-full h-full object-cover" />
      </div>

      <!-- Content -->
      <div class="prose prose-lg max-w-none prose-headings:font-bold prose-img:rounded-2xl post-content"
        :class="layout.variant === 'b' ? 'prose-invert prose-a:text-violet-400' : 'prose-gray prose-headings:text-gray-900 prose-a:text-primary-600'"
        v-html="post.content" style="font-family:'Inter',sans-serif"></div>

      <!-- Tags -->
      <div v-if="post.tags?.length" class="flex flex-wrap gap-2 mt-10 pt-8" :class="layout.variant === 'b' ? 'border-t border-[#1e1e3a]' : 'border-t border-gray-100'">
        <span v-for="tag in post.tags" :key="tag.id" class="px-3 py-1 rounded-full text-sm font-medium transition-colors cursor-pointer"
          :class="layout.variant === 'b' ? 'bg-slate-800 text-slate-300 hover:bg-violet-900 hover:text-violet-300' : 'bg-gray-100 text-gray-600 hover:bg-primary-100 hover:text-primary-700'"
        >#{{ tag.name }}</span>
      </div>

      <!-- Photo Gallery -->
      <div v-if="getGallery().length" class="mt-12">
        <h3 class="text-xl font-bold mb-4" :class="layout.variant === 'b' ? 'text-slate-100' : 'text-gray-900'" style="font-family:'Playfair Display',serif">Photo Gallery</h3>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div v-for="(img, idx) in getGallery()" :key="idx" class="aspect-square rounded-xl overflow-hidden cursor-pointer group" @click="galleryOpen = true; galleryIndex = idx">
            <img :src="img" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
          </div>
        </div>
      </div>

      <!-- Share -->
      <div class="mt-12 p-6 rounded-2xl" :class="layout.variant === 'b' ? 'bg-[#0f0f1e] border border-[#1e1e3a]' : 'bg-gray-50'">
        <p class="text-sm font-semibold mb-3" :class="layout.variant === 'b' ? 'text-slate-300' : 'text-gray-700'">Share this article</p>
        <div class="flex gap-3">
          <button class="flex items-center gap-2 px-4 py-2 text-white rounded-lg text-sm font-medium transition-colors" :class="layout.variant === 'b' ? 'bg-slate-800 hover:bg-slate-700' : 'bg-gray-900 hover:bg-gray-700'">𝕏 Twitter</button>
          <button class="flex items-center gap-2 px-4 py-2 text-white rounded-lg text-sm font-medium transition-colors" :class="layout.variant === 'b' ? 'bg-violet-700 hover:bg-violet-800' : 'bg-primary-700 hover:bg-primary-800'">in LinkedIn</button>
          <button @click="navigator.clipboard.writeText(window.location.href)" class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors" :class="layout.variant === 'b' ? 'bg-slate-800 text-slate-300 hover:bg-slate-700' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'">🔗 Copy Link</button>
        </div>
      </div>
    </article>

    <!-- Related Posts -->
    <section v-if="relatedPosts.length" class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
      <h2 class="text-2xl font-bold mb-6" :class="layout.variant === 'b' ? 'text-slate-100' : 'text-gray-900'" style="font-family:'Playfair Display',serif">Related Posts</h2>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <PostCard v-for="p in relatedPosts" :key="p.id" :post="p" />
      </div>
    </section>

    <!-- Comments -->
    <section class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
      <h2 class="text-2xl font-bold mb-6" :class="layout.variant === 'b' ? 'text-slate-100' : 'text-gray-900'" style="font-family:'Playfair Display',serif">{{ comments.length }} Comments</h2>

      <div class="space-y-4 mb-10">
        <div v-for="c in comments" :key="c.id" class="rounded-2xl p-5" :class="layout.variant === 'b' ? 'bg-[#0f0f1e] border border-[#1e1e3a]' : 'bg-gray-50'">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-8 h-8 rounded-full flex items-center justify-center" :class="layout.variant === 'b' ? 'bg-violet-900' : 'bg-primary-100'">
              <span class="font-bold text-sm" :class="layout.variant === 'b' ? 'text-violet-400' : 'text-primary-600'">{{ c.authorName.charAt(0) }}</span>
            </div>
            <div>
              <div class="font-semibold text-sm" :class="layout.variant === 'b' ? 'text-slate-200' : 'text-gray-800'">{{ c.authorName }}</div>
              <div class="text-xs" :class="layout.variant === 'b' ? 'text-slate-500' : 'text-gray-400'">{{ format(new Date(c.createdAt), 'MMM d, yyyy') }}</div>
            </div>
          </div>
          <p class="text-sm" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-600'">{{ c.content }}</p>
        </div>
      </div>

      <div v-if="commentSubmitted" class="bg-green-50 border border-green-200 rounded-2xl p-5 text-green-700 text-sm">
        Your comment has been submitted and is awaiting approval. Thank you!
      </div>

      <form v-else @submit.prevent="submitComment" class="rounded-2xl p-6" :class="layout.variant === 'b' ? 'bg-[#0f0f1e] border border-[#1e1e3a]' : 'bg-gray-50'">
        <h3 class="font-bold mb-4" :class="layout.variant === 'b' ? 'text-slate-100' : 'text-gray-900'">Leave a Comment</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <input v-model="commentForm.authorName" type="text" placeholder="Your Name *" required class="px-4 py-3 rounded-xl border text-sm focus:outline-none"
            :class="layout.variant === 'b' ? 'bg-[#13132a] border-[#1e1e3a] text-slate-200 placeholder-slate-500 focus:border-violet-500' : 'bg-white border-gray-200 focus:border-primary-400'" />
          <input v-model="commentForm.authorEmail" type="email" placeholder="Your Email" class="px-4 py-3 rounded-xl border text-sm focus:outline-none"
            :class="layout.variant === 'b' ? 'bg-[#13132a] border-[#1e1e3a] text-slate-200 placeholder-slate-500 focus:border-violet-500' : 'bg-white border-gray-200 focus:border-primary-400'" />
        </div>
        <textarea v-model="commentForm.content" rows="4" placeholder="Write your comment..." required class="w-full px-4 py-3 rounded-xl border text-sm focus:outline-none resize-none mb-4"
          :class="layout.variant === 'b' ? 'bg-[#13132a] border-[#1e1e3a] text-slate-200 placeholder-slate-500 focus:border-violet-500' : 'bg-white border-gray-200 focus:border-primary-400'"></textarea>
        <button type="submit" class="text-white px-6 py-3 rounded-xl text-sm font-semibold transition-colors"
          :class="layout.variant === 'b' ? 'bg-violet-600 hover:bg-violet-700' : 'bg-primary-600 hover:bg-primary-700'">Post Comment</button>
      </form>
    </section>

    <!-- Gallery Lightbox -->
    <div v-if="galleryOpen" class="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4" @click.self="galleryOpen=false">
      <button @click="galleryOpen=false" class="absolute top-4 right-4 text-white text-3xl">&times;</button>
      <button @click="galleryIndex = (galleryIndex - 1 + getGallery().length) % getGallery().length" class="absolute left-4 text-white text-3xl p-2">&#8249;</button>
      <img :src="getGallery()[galleryIndex]" class="max-h-[90vh] max-w-full rounded-2xl object-contain" />
      <button @click="galleryIndex = (galleryIndex + 1) % getGallery().length" class="absolute right-4 text-white text-3xl p-2">&#8250;</button>
    </div>

    <!-- Desktop TTS sliding panel — fixed right side, hidden on mobile -->
    <Teleport to="body">
      <div v-if="post" class="hidden sm:flex fixed right-0 top-1/2 -translate-y-1/2 z-50 items-stretch drop-shadow-2xl">
        <!-- Always-visible tab -->
        <button @click="playerOpen ? closePlayer() : openPlayer()"
          class="flex flex-col items-center justify-center gap-2 w-10 rounded-l-2xl py-5 transition-colors text-white"
          :class="layout.variant === 'b'
            ? (playerOpen ? 'bg-violet-700' : 'bg-violet-600 hover:bg-violet-700')
            : (playerOpen ? 'bg-primary-700' : 'bg-primary-600 hover:bg-primary-700')">
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
          <div class="w-[288px] h-full flex flex-col p-5 gap-4"
            :class="layout.variant === 'b' ? 'bg-[#0f0f1e] border-l border-[#1e1e3a]' : 'bg-white border-l border-gray-100'">

            <!-- Header -->
            <div class="flex items-start justify-between gap-2">
              <div>
                <p class="text-xs font-semibold uppercase tracking-wider mb-0.5" :class="layout.variant === 'b' ? 'text-violet-400' : 'text-primary-600'">Now reading</p>
                <p class="text-sm font-bold leading-snug line-clamp-2" :class="layout.variant === 'b' ? 'text-slate-100' : 'text-gray-900'">{{ post.title }}</p>
              </div>
              <button @click="closePlayer" class="flex-shrink-0 mt-0.5" :class="layout.variant === 'b' ? 'text-slate-600 hover:text-slate-300' : 'text-gray-300 hover:text-gray-600'" title="Close">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>

            <!-- Waveform animation -->
            <div class="flex items-end justify-center gap-1 h-10" aria-hidden="true">
              <span v-for="i in 12" :key="i" class="w-1.5 rounded-full"
                :class="[ttsState === 'playing' ? 'tts-bar' : 'h-1.5 opacity-30', layout.variant === 'b' ? 'bg-violet-400' : 'bg-primary-400']"
                :style="ttsState === 'playing' ? `animation-delay:${i * 60}ms` : ''"></span>
            </div>

            <!-- Seek slider -->
            <div>
              <input type="range" min="0" max="100"
                :value="Math.round(ttsProgress * 100)"
                :disabled="ttsState === 'loading' || ttsState === 'idle'"
                class="tts-slider w-full"
                @change="seekTo($event.target.value / 100)" />
              <div class="flex justify-between mt-1.5 text-xs" :class="layout.variant === 'b' ? 'text-slate-500' : 'text-gray-400'">
                <span v-if="ttsTotalChunks">Segment {{ ttsChunkIdx + 1 }} / {{ ttsTotalChunks }}</span>
                <span v-else>—</span>
                <span>{{ Math.round(ttsProgress * 100) }}%</span>
              </div>
            </div>

            <!-- Controls: Stop + Play/Pause -->
            <div class="flex items-center justify-center gap-3">
              <!-- Stop button -->
              <button @click="stopPlayback"
                :disabled="ttsState === 'idle' || ttsState === 'loading'"
                class="flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all"
                :class="ttsState === 'idle' || ttsState === 'loading'
                  ? (layout.variant === 'b' ? 'border-slate-800 text-slate-700 cursor-not-allowed' : 'border-gray-200 text-gray-300 cursor-not-allowed')
                  : (layout.variant === 'b' ? 'border-slate-600 text-slate-400 hover:border-slate-400 hover:text-slate-200' : 'border-gray-300 text-gray-600 hover:border-gray-500 hover:text-gray-800')"
                title="Stop (return to beginning)">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="4" y="4" width="16" height="16" rx="2"/>
                </svg>
              </button>

              <!-- Play / Pause button -->
              <button @click="ttsState === 'loading' ? null : togglePlayPause()"
                class="flex items-center justify-center w-14 h-14 rounded-full transition-all"
                :class="ttsState === 'loading'
                  ? (layout.variant === 'b' ? 'bg-slate-800 text-slate-500 cursor-wait' : 'bg-gray-100 text-gray-400 cursor-wait')
                  : (layout.variant === 'b' ? 'bg-violet-600 text-white hover:bg-violet-700 hover:scale-105 active:scale-95' : 'bg-primary-600 text-white hover:bg-primary-700 hover:scale-105 active:scale-95')">
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

            <p class="text-xs text-center" :class="layout.variant === 'b' ? 'text-slate-600' : 'text-gray-400'">Powered by local AI</p>
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

/* Range slider — cross-browser consistent styling */
.tts-slider {
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 9999px;
  background: #e5e7eb;
  outline: none;
  cursor: pointer;
  background-image: v-bind("'linear-gradient(' + ttsTrackColor + ', ' + ttsTrackColor + ')'");
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
  background: v-bind(ttsThumbColor);
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
  background: v-bind(ttsThumbColor);
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0,0,0,.3);
}
.tts-slider::-moz-range-progress {
  background: v-bind(ttsTrackColor);
  height: 6px;
  border-radius: 9999px;
}
</style>
