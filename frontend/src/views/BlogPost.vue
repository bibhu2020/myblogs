<script setup>
import { onMounted, ref, nextTick } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useBlogStore } from '../stores/blog'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import PostCard from '../components/PostCard.vue'
import api from '../api'
import { format } from 'date-fns'
import hljs from 'highlight.js'

const blog = useBlogStore()
const route = useRoute()
const post = ref(null)
const relatedPosts = ref([])
const comments = ref([])
const commentForm = ref({ authorName: '', authorEmail: '', content: '' })
const commentSubmitted = ref(false)
const galleryOpen = ref(false)
const galleryIndex = ref(0)

// ── TTS player ────────────────────────────────────────────────────────────────
const ttsState       = ref('idle')  // idle | loading | playing | paused
const ttsProgress    = ref(0)       // 0–1 across all chunks
const ttsCurrentTime = ref(0)
const ttsDuration    = ref(0)
const playerOpen     = ref(false)
let ttsAudio     = null
let blobUrl      = null
let playbackLive = false  // set false to abort the chunk loop

function formatTime(s) {
  if (!s || isNaN(s)) return '0:00'
  return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`
}

// Split HTML into sentence-boundary text chunks (~500 chars each)
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

// Play a single blob; resolves when the chunk ends or is interrupted
function playChunk(blob, chunkIdx, total) {
  return new Promise(resolve => {
    const url = URL.createObjectURL(blob)
    blobUrl  = url
    ttsAudio = new Audio(url)

    ttsAudio.onloadedmetadata = () => { ttsDuration.value = ttsAudio.duration }
    ttsAudio.ontimeupdate = () => {
      if (!ttsAudio.duration) return
      ttsProgress.value    = (chunkIdx + ttsAudio.currentTime / ttsAudio.duration) / total
      ttsCurrentTime.value = ttsAudio.currentTime
    }
    ttsAudio.onended  = () => { URL.revokeObjectURL(url); blobUrl = null; resolve() }
    ttsAudio.onerror  = () => { URL.revokeObjectURL(url); blobUrl = null; resolve() }
    ttsAudio.play().catch(() => resolve())
  })
}

async function openPlayer() {
  playerOpen.value = true
  if (ttsState.value !== 'idle') return

  ttsState.value = 'loading'
  ttsProgress.value = 0
  playbackLive = true

  const chunks = splitChunks(post.value.content)
  if (!chunks.length) { ttsState.value = 'idle'; return }

  // Kick off ALL chunk fetches concurrently so later chunks are pre-fetched
  const fetches = chunks.map(text =>
    api.post('/tts', { text }, { responseType: 'blob' })
      .then(r => r.data)
      .catch(() => null)
  )

  for (let i = 0; i < fetches.length; i++) {
    if (!playbackLive) break
    const blob = await fetches[i]
    if (!blob || !playbackLive) break
    if (i === 0) ttsState.value = 'playing'
    await playChunk(blob, i, fetches.length)
  }

  if (playbackLive) { ttsState.value = 'idle'; ttsProgress.value = 0 }
  playbackLive = false
}

function togglePlayPause() {
  if (!ttsAudio) return
  if (ttsState.value === 'playing') { ttsAudio.pause(); ttsState.value = 'paused' }
  else if (ttsState.value === 'paused') { ttsAudio.play(); ttsState.value = 'playing' }
}

function seek(e) {
  if (!ttsAudio || !ttsDuration.value) return
  const r = e.currentTarget.getBoundingClientRect()
  ttsAudio.currentTime = ((e.clientX - r.left) / r.width) * ttsDuration.value
}

function closePlayer() {
  playbackLive = false
  ttsAudio?.pause()
  if (blobUrl) { URL.revokeObjectURL(blobUrl); blobUrl = null }
  ttsAudio = null
  ttsState.value = 'idle'
  ttsProgress.value = 0
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
  <div class="min-h-screen bg-white">
    <Navbar />

    <div v-if="blog.loading" class="max-w-4xl mx-auto px-4 py-12 animate-pulse">
      <div class="h-8 bg-gray-200 rounded mb-4 w-3/4"></div>
      <div class="bg-gray-200 rounded-2xl aspect-[16/7] mb-8"></div>
    </div>

    <article v-else-if="post" class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <!-- Category & meta -->
      <div class="mb-6">
        <RouterLink v-if="post.category" :to="`/category/${post.category.slug}`" class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-semibold text-white mb-4" :style="{ background: post.category.color || '#3B82F6' }">
          {{ post.category.icon }} {{ post.category.name }}
        </RouterLink>
        <h1 class="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 leading-tight mb-6" style="font-family:'Playfair Display',serif">{{ post.title }}</h1>
        <div class="flex flex-wrap items-center gap-4 text-sm text-gray-500">
          <div class="flex items-center gap-2">
            <div class="w-9 h-9 bg-primary-600 rounded-full flex items-center justify-center"><span class="text-white font-bold">{{ (post.authorName||'A').charAt(0) }}</span></div>
            <div><div class="font-semibold text-gray-800">{{ post.authorName }}</div></div>
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
            class="flex items-center gap-2 px-4 py-2.5 bg-primary-600 text-white rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors w-full justify-center">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M6 9v6l5-3-5-3z" fill="currentColor" stroke="none"/></svg>
            Listen to this article
          </button>
        </div>
        <div v-else class="bg-white rounded-2xl shadow-lg border border-gray-100 p-4">
          <div class="flex items-center gap-3 mb-3">
            <div class="flex items-end gap-0.5 h-6" aria-hidden="true">
              <span v-for="i in 4" :key="i" class="w-1 bg-primary-500 rounded-full"
                :class="ttsState === 'playing' ? 'tts-bar' : 'h-1'"
                :style="ttsState === 'playing' ? `animation-delay:${i * 80}ms` : ''"></span>
            </div>
            <p class="text-sm font-semibold text-gray-800 truncate flex-1">{{ post.title }}</p>
            <button @click="closePlayer" class="text-gray-400 hover:text-gray-600 flex-shrink-0">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <!-- progress bar -->
          <div class="h-1.5 bg-gray-200 rounded-full cursor-pointer mb-2" @click="seek">
            <div class="h-full bg-primary-500 rounded-full transition-all" :style="{ width: ttsProgress * 100 + '%' }"></div>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-xs text-gray-400">{{ formatTime(ttsCurrentTime) }} / {{ formatTime(ttsDuration) }}</span>
            <button @click="ttsState === 'loading' ? null : togglePlayPause()"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
              :class="ttsState === 'loading' ? 'bg-gray-100 text-gray-400' : 'bg-primary-600 text-white hover:bg-primary-700'">
              <svg v-if="ttsState === 'loading'" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
              <svg v-else-if="ttsState === 'playing'" class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/></svg>
              <svg v-else class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
              {{ ttsState === 'loading' ? 'Loading…' : ttsState === 'playing' ? 'Pause' : 'Play' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Featured Image -->
      <div v-if="post.featuredImage" class="rounded-3xl overflow-hidden aspect-[16/7] mb-10">
        <img :src="post.featuredImage" :alt="post.title" class="w-full h-full object-cover" />
      </div>

      <!-- Content -->
      <div class="prose prose-lg prose-gray max-w-none prose-headings:font-bold prose-headings:text-gray-900 prose-a:text-primary-600 prose-img:rounded-2xl post-content" v-html="post.content" style="font-family:'Inter',sans-serif"></div>

      <!-- Tags -->
      <div v-if="post.tags?.length" class="flex flex-wrap gap-2 mt-10 pt-8 border-t border-gray-100">
        <span v-for="tag in post.tags" :key="tag.id" class="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm font-medium hover:bg-primary-100 hover:text-primary-700 transition-colors cursor-pointer">#{{ tag.name }}</span>
      </div>

      <!-- Photo Gallery -->
      <div v-if="getGallery().length" class="mt-12">
        <h3 class="text-xl font-bold text-gray-900 mb-4" style="font-family:'Playfair Display',serif">Photo Gallery</h3>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div v-for="(img, idx) in getGallery()" :key="idx" class="aspect-square rounded-xl overflow-hidden cursor-pointer group" @click="galleryOpen = true; galleryIndex = idx">
            <img :src="img" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
          </div>
        </div>
      </div>

      <!-- Share -->
      <div class="mt-12 p-6 bg-gray-50 rounded-2xl">
        <p class="text-sm font-semibold text-gray-700 mb-3">Share this article</p>
        <div class="flex gap-3">
          <button class="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-700 transition-colors">𝕏 Twitter</button>
          <button class="flex items-center gap-2 px-4 py-2 bg-primary-700 text-white rounded-lg text-sm font-medium hover:bg-primary-800 transition-colors">in LinkedIn</button>
          <button @click="navigator.clipboard.writeText(window.location.href)" class="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-300 transition-colors">🔗 Copy Link</button>
        </div>
      </div>
    </article>

    <!-- Related Posts -->
    <section v-if="relatedPosts.length" class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
      <h2 class="text-2xl font-bold text-gray-900 mb-6" style="font-family:'Playfair Display',serif">Related Posts</h2>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <PostCard v-for="p in relatedPosts" :key="p.id" :post="p" />
      </div>
    </section>

    <!-- Comments -->
    <section class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
      <h2 class="text-2xl font-bold text-gray-900 mb-6" style="font-family:'Playfair Display',serif">{{ comments.length }} Comments</h2>

      <div class="space-y-4 mb-10">
        <div v-for="c in comments" :key="c.id" class="bg-gray-50 rounded-2xl p-5">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center"><span class="text-primary-600 font-bold text-sm">{{ c.authorName.charAt(0) }}</span></div>
            <div><div class="font-semibold text-gray-800 text-sm">{{ c.authorName }}</div><div class="text-xs text-gray-400">{{ format(new Date(c.createdAt), 'MMM d, yyyy') }}</div></div>
          </div>
          <p class="text-gray-600 text-sm">{{ c.content }}</p>
        </div>
      </div>

      <div v-if="commentSubmitted" class="bg-green-50 border border-green-200 rounded-2xl p-5 text-green-700 text-sm">
        Your comment has been submitted and is awaiting approval. Thank you!
      </div>

      <form v-else @submit.prevent="submitComment" class="bg-gray-50 rounded-2xl p-6">
        <h3 class="font-bold text-gray-900 mb-4">Leave a Comment</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <input v-model="commentForm.authorName" type="text" placeholder="Your Name *" required class="px-4 py-3 bg-white rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-primary-400" />
          <input v-model="commentForm.authorEmail" type="email" placeholder="Your Email" class="px-4 py-3 bg-white rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-primary-400" />
        </div>
        <textarea v-model="commentForm.content" rows="4" placeholder="Write your comment..." required class="w-full px-4 py-3 bg-white rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-primary-400 resize-none mb-4"></textarea>
        <button type="submit" class="bg-primary-600 text-white px-6 py-3 rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors">Post Comment</button>
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
          class="flex flex-col items-center justify-center gap-2 w-10 rounded-l-2xl py-5 transition-colors"
          :class="playerOpen ? 'bg-primary-700 text-white' : 'bg-primary-600 text-white hover:bg-primary-700'">
          <svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0014 7.97v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
          </svg>
          <span class="text-[10px] font-bold tracking-wider" style="writing-mode:vertical-lr;transform:rotate(180deg)">
            {{ playerOpen ? 'CLOSE' : 'LISTEN' }}
          </span>
        </button>

        <!-- Sliding player panel -->
        <div class="overflow-hidden transition-all duration-300 ease-in-out"
          :style="playerOpen ? 'width:280px' : 'width:0'">
          <div class="w-[280px] h-full bg-white border-l border-gray-100 flex flex-col p-5 gap-4">
            <!-- Header -->
            <div class="flex items-start justify-between gap-2">
              <div>
                <p class="text-xs font-semibold text-primary-600 uppercase tracking-wider mb-0.5">Now reading</p>
                <p class="text-sm font-bold text-gray-900 leading-snug line-clamp-2">{{ post.title }}</p>
              </div>
              <button @click="closePlayer" class="text-gray-300 hover:text-gray-500 flex-shrink-0 mt-0.5">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>

            <!-- Waveform animation -->
            <div class="flex items-end justify-center gap-1 h-10" aria-hidden="true">
              <span v-for="i in 12" :key="i" class="w-1.5 bg-primary-400 rounded-full"
                :class="ttsState === 'playing' ? 'tts-bar' : 'h-1.5 opacity-30'"
                :style="ttsState === 'playing' ? `animation-delay:${i * 60}ms` : ''"></span>
            </div>

            <!-- Progress bar -->
            <div>
              <div class="h-1.5 bg-gray-100 rounded-full cursor-pointer" @click="seek">
                <div class="h-full bg-primary-500 rounded-full transition-all" :style="{ width: ttsProgress * 100 + '%' }"></div>
              </div>
              <div class="flex justify-between mt-1.5 text-xs text-gray-400">
                <span>{{ formatTime(ttsCurrentTime) }}</span>
                <span>{{ formatTime(ttsDuration) }}</span>
              </div>
            </div>

            <!-- Controls -->
            <div class="flex items-center justify-center">
              <button @click="ttsState === 'loading' ? null : togglePlayPause()"
                class="flex items-center justify-center w-12 h-12 rounded-full transition-all"
                :class="ttsState === 'loading' ? 'bg-gray-100 text-gray-400 cursor-wait' : 'bg-primary-600 text-white hover:bg-primary-700 hover:scale-105'">
                <svg v-if="ttsState === 'loading'" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                <svg v-else-if="ttsState === 'playing'" class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
                </svg>
                <svg v-else class="w-5 h-5 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
              </button>
            </div>

            <p class="text-xs text-gray-400 text-center">Powered by OpenAI TTS</p>
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
</style>
