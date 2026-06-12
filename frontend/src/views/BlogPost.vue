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

    <Footer />
  </div>
</template>
