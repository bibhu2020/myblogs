<script setup>
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useStoryStore } from '../stores/story'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import { format } from 'date-fns'

const store = useStoryStore()
const page = ref(1)
const genre = ref('')

const GENRES = [
  { value: '', label: 'All Stories', icon: '📚' },
  { value: 'Adventure', label: 'Adventure', icon: '🏕️' },
  { value: 'Fantasy', label: 'Fantasy', icon: '🧙' },
  { value: 'Mystery', label: 'Mystery', icon: '🔍' },
  { value: 'Fable', label: 'Fable', icon: '🦁' },
  { value: 'Science Fiction', label: 'Sci-Fi', icon: '🚀' },
  { value: 'Historical Fiction', label: 'Historical', icon: '🏛️' },
  { value: 'Mythology', label: 'Mythology', icon: '⚡' },
]

const GENRE_COLORS = {
  'Adventure': 'bg-orange-100 text-orange-700',
  'Fantasy': 'bg-purple-100 text-purple-700',
  'Mystery': 'bg-blue-100 text-blue-700',
  'Fable': 'bg-green-100 text-green-700',
  'Science Fiction': 'bg-cyan-100 text-cyan-700',
  'Historical Fiction': 'bg-amber-100 text-amber-700',
  'Mythology': 'bg-yellow-100 text-yellow-700',
}

function genreColor(g) {
  return GENRE_COLORS[g] || 'bg-gray-100 text-gray-700'
}

onMounted(() => loadStories())

async function loadStories() {
  await store.fetchStories({ page: page.value, limit: 12, ...(genre.value ? { genre: genre.value } : {}) })
}

watch(page, loadStories)

function setGenre(g) {
  genre.value = g
  page.value = 1
  loadStories()
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-b from-indigo-50 to-white">
    <Navbar />

    <!-- Hero banner -->
    <div class="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500 text-white">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14 text-center">
        <div class="text-5xl mb-4">📖</div>
        <h1 class="text-4xl sm:text-5xl font-bold mb-3" style="font-family:'Playfair Display',serif">Story Corner</h1>
        <p class="text-indigo-100 text-lg max-w-xl mx-auto">Magical stories for curious minds, ages 8–15. Each tale is a 20-minute adventure!</p>
      </div>
    </div>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">

      <!-- Genre filter -->
      <div class="flex flex-wrap gap-2 mb-8 justify-center">
        <button
          v-for="g in GENRES" :key="g.value"
          @click="setGenre(g.value)"
          :class="genre === g.value
            ? 'bg-indigo-600 text-white shadow-md scale-105'
            : 'bg-white text-gray-600 border border-gray-200 hover:border-indigo-300 hover:text-indigo-600'"
          class="px-4 py-2 rounded-full text-sm font-medium transition-all duration-150 flex items-center gap-1.5"
        >
          <span>{{ g.icon }}</span> {{ g.label }}
        </button>
      </div>

      <!-- Loading skeleton -->
      <div v-if="store.loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="animate-pulse rounded-2xl overflow-hidden shadow-sm bg-white">
          <div class="aspect-[4/3] bg-indigo-100"></div>
          <div class="p-5 space-y-3">
            <div class="h-5 bg-gray-200 rounded w-3/4"></div>
            <div class="h-4 bg-gray-100 rounded w-full"></div>
            <div class="h-4 bg-gray-100 rounded w-2/3"></div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else-if="store.stories.length === 0" class="text-center py-20">
        <div class="text-6xl mb-4">📭</div>
        <h2 class="text-xl font-semibold text-gray-600">No stories yet</h2>
        <p class="text-gray-400 mt-2">The story agent is writing something magical — check back soon!</p>
      </div>

      <!-- Story cards grid -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <RouterLink
          v-for="story in store.stories"
          :key="story.id"
          :to="`/story/${story.slug}`"
          class="group bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 hover:-translate-y-1 border border-gray-100"
        >
          <!-- Cover image -->
          <div class="aspect-[4/3] overflow-hidden bg-gradient-to-br from-indigo-100 to-purple-100 relative">
            <img
              v-if="story.featuredImage"
              :src="story.featuredImage"
              :alt="story.title"
              class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
            <div v-else class="w-full h-full flex items-center justify-center text-6xl">
              {{ { Adventure: '🏕️', Fantasy: '🧙', Mystery: '🔍', Fable: '🦁', 'Science Fiction': '🚀', 'Historical Fiction': '🏛️', Mythology: '⚡' }[story.genre] || '📖' }}
            </div>
            <!-- Genre badge -->
            <span v-if="story.genre"
              class="absolute top-3 left-3 px-2.5 py-1 rounded-full text-xs font-semibold"
              :class="genreColor(story.genre)"
            >{{ story.genre }}</span>
            <!-- Read time badge -->
            <span class="absolute top-3 right-3 px-2.5 py-1 rounded-full text-xs font-semibold bg-white/90 text-gray-700">
              ⏱ {{ story.readTime || '20' }} min
            </span>
          </div>

          <!-- Card content -->
          <div class="p-5">
            <div class="flex items-center gap-1.5 text-xs text-indigo-500 font-medium mb-2">
              <span>👦👧 Ages {{ story.ageGroup || '8–15' }}</span>
              <span class="text-gray-300">·</span>
              <span>{{ format(new Date(story.createdAt), 'MMM d, yyyy') }}</span>
            </div>
            <h2 class="text-lg font-bold text-gray-900 mb-2 group-hover:text-indigo-600 transition-colors leading-snug" style="font-family:'Playfair Display',serif">
              {{ story.title }}
            </h2>
            <p class="text-gray-500 text-sm line-clamp-3 leading-relaxed">{{ story.excerpt }}</p>
            <div class="mt-4 flex items-center text-indigo-600 text-sm font-medium">
              Read the story
              <svg class="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
            </div>
          </div>
        </RouterLink>
      </div>

      <!-- Pagination -->
      <div v-if="store.pagination.pages > 1" class="flex justify-center gap-2 mt-12">
        <button
          v-for="p in store.pagination.pages" :key="p"
          @click="page = p"
          class="w-10 h-10 rounded-full text-sm font-medium transition-colors"
          :class="p === page ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:border-indigo-300'"
        >{{ p }}</button>
      </div>
    </main>

    <Footer />
  </div>
</template>
