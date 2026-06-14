<script setup>
import { onMounted, ref, nextTick } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import api from '../api'
import { format } from 'date-fns'
import hljs from 'highlight.js'

const route = useRoute()
const story = ref(null)
const error = ref(null)

const GENRE_ICONS = {
  Adventure: '🏕️', Fantasy: '🧙', Mystery: '🔍', Fable: '🦁',
  'Science Fiction': '🚀', 'Historical Fiction': '🏛️', Mythology: '⚡',
}

onMounted(async () => {
  try {
    const res = await api.get(`/stories/${route.params.slug}`)
    story.value = res.data
    await nextTick()
    document.querySelectorAll('.story-content pre code').forEach(el => hljs.highlightElement(el))
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

    <article v-else class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">

      <!-- Breadcrumb -->
      <nav class="flex items-center gap-2 text-sm text-gray-400 mb-6">
        <RouterLink to="/" class="hover:text-indigo-600 transition-colors">Home</RouterLink>
        <span>›</span>
        <RouterLink to="/story" class="hover:text-indigo-600 transition-colors">Stories</RouterLink>
        <span>›</span>
        <span class="text-gray-600 truncate max-w-xs">{{ story.title }}</span>
      </nav>

      <!-- Genre + age badge -->
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
      <div class="flex items-center gap-3 text-sm text-gray-400 mb-8 border-b border-gray-100 pb-6">
        <span>By <strong class="text-gray-600">{{ story.authorName || 'Meridian Storyteller' }}</strong></span>
        <span>·</span>
        <span>{{ format(new Date(story.createdAt), 'MMMM d, yyyy') }}</span>
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

    <Footer />
  </div>
</template>
