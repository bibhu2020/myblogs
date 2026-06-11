<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useBlogStore } from '../stores/blog'
import LogoMark from './LogoMark.vue'

const blog = useBlogStore()
const route = useRoute()
const router = useRouter()
const mobileOpen = ref(false)
const topicsOpen = ref(false)
const searchQuery = ref('')
const topicsRef = ref(null)

onMounted(() => {
  blog.fetchCategories()
  document.addEventListener('click', onClickOutside)
})
onUnmounted(() => document.removeEventListener('click', onClickOutside))

function onClickOutside(e) {
  if (topicsRef.value && !topicsRef.value.contains(e.target)) topicsOpen.value = false
}

function submitSearch(e) {
  e.preventDefault()
  if (!searchQuery.value.trim()) return
  router.push({ path: '/search', query: { s: searchQuery.value.trim() } })
  searchQuery.value = ''
}
</script>

<template>
  <!-- HOLIDAY-BANNER-START -->
  <div class="bg-primary-600 text-white text-center text-sm py-1">Happy Father's Day &amp; Summer Solstice! ☀️</div>
  <!-- HOLIDAY-BANNER-END -->
  <nav class="bg-white border-b border-gray-100 sticky top-0 z-50 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-16 items-center gap-6">

        <!-- Logo -->
        <RouterLink to="/" class="flex items-center gap-2.5 flex-shrink-0">
          <LogoMark :size="36" />
          <span class="text-xl font-bold text-gray-900 tracking-tight" style="font-family: 'Playfair Display', serif">Meridian</span>
        </RouterLink>

        <!-- Desktop nav -->
        <div class="hidden md:flex items-center gap-1 flex-1">
          <RouterLink to="/" class="px-3 py-2 text-gray-600 hover:text-blue-600 text-sm font-medium transition-colors rounded-lg hover:bg-gray-50" :class="{ 'text-blue-600 bg-blue-50': route.path === '/' }">Home</RouterLink>
          <RouterLink to="/blog" class="px-3 py-2 text-gray-600 hover:text-blue-600 text-sm font-medium transition-colors rounded-lg hover:bg-gray-50" :class="{ 'text-blue-600 bg-blue-50': route.path === '/blog' }">All Posts</RouterLink>

          <!-- Topics dropdown -->
          <div class="relative" ref="topicsRef">
            <button
              @click="topicsOpen = !topicsOpen"
              class="flex items-center gap-1 px-3 py-2 text-sm font-medium transition-colors rounded-lg hover:bg-gray-50"
              :class="topicsOpen ? 'text-blue-600 bg-blue-50' : 'text-gray-600 hover:text-blue-600'"
            >
              Topics
              <svg class="w-4 h-4 transition-transform" :class="{ 'rotate-180': topicsOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>

            <div
              v-if="topicsOpen"
              class="absolute top-full left-0 mt-2 w-56 bg-white rounded-xl shadow-lg border border-gray-100 py-2 z-50"
            >
              <RouterLink
                v-for="cat in blog.categories"
                :key="cat.id"
                :to="`/category/${cat.slug}`"
                @click="topicsOpen = false"
                class="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 hover:text-blue-600 transition-colors"
                :class="{ 'text-blue-600 bg-blue-50 font-medium': route.params.slug === cat.slug }"
              >
                <span class="text-base w-5 text-center">{{ cat.icon }}</span>
                {{ cat.name }}
              </RouterLink>
            </div>
          </div>
        </div>

        <!-- Search bar (desktop) -->
        <form @submit="submitSearch" class="hidden md:flex items-center flex-shrink-0">
          <div class="relative">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search…"
              class="pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 bg-gray-50 w-44 focus:w-56 transition-all duration-200"
            />
          </div>
        </form>

        <RouterLink to="/admin" class="hidden md:block bg-blue-600 text-white px-4 py-2 rounded-full text-sm font-medium hover:bg-blue-700 transition-colors flex-shrink-0">Admin</RouterLink>

        <!-- Mobile menu button -->
        <button @click="mobileOpen = !mobileOpen" class="md:hidden p-2 rounded-md text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path v-if="!mobileOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
            <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Mobile menu -->
      <div v-if="mobileOpen" class="md:hidden py-4 border-t border-gray-100 space-y-1">
        <RouterLink to="/" @click="mobileOpen=false" class="block px-4 py-2.5 text-gray-700 hover:text-blue-600 font-medium rounded-lg hover:bg-gray-50">Home</RouterLink>
        <RouterLink to="/blog" @click="mobileOpen=false" class="block px-4 py-2.5 text-gray-700 hover:text-blue-600 font-medium rounded-lg hover:bg-gray-50">All Posts</RouterLink>
        <div class="px-4 pt-2 pb-1 text-xs font-bold text-gray-400 uppercase tracking-wider">Topics</div>
        <RouterLink v-for="cat in blog.categories" :key="cat.id" :to="`/category/${cat.slug}`" @click="mobileOpen=false" class="flex items-center gap-2 px-4 py-2.5 text-gray-700 hover:text-blue-600 font-medium rounded-lg hover:bg-gray-50">{{ cat.icon }} {{ cat.name }}</RouterLink>
        <div class="border-t border-gray-100 mt-2 pt-2">
          <RouterLink to="/search" @click="mobileOpen=false" class="block px-4 py-2.5 text-gray-700 hover:text-blue-600 font-medium rounded-lg hover:bg-gray-50">🔍 Search</RouterLink>
          <RouterLink to="/admin" @click="mobileOpen=false" class="block px-4 py-2.5 text-blue-600 font-medium rounded-lg hover:bg-blue-50">Admin Panel</RouterLink>
        </div>
      </div>
    </div>
  </nav>
</template>
