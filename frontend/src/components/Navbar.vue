<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useBlogStore } from '../stores/blog'
import { useLayoutStore } from '../stores/layout'
import LogoMark from './LogoMark.vue'

const blog = useBlogStore()
const layout = useLayoutStore()
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

const isB = () => layout.variant === 'b'
</script>

<template>
  <!-- Layout A: Holiday banner -->
  <template v-if="layout.variant === 'a'">
    <!-- HOLIDAY-BANNER-START -->
<div role="banner" aria-label="World celebrations announcement" class="bg-gradient-to-r from-primary-700 to-primary-600 text-white text-center text-sm py-1.5 font-medium">🎉 Join global celebrations this June!</div>
<!-- HOLIDAY-BANNER-END -->
  </template>
  <!-- Layout B: Holiday banner -->
  <template v-else>
    <!-- HOLIDAY-BANNER-B-START -->
<div role="banner" aria-label="World celebrations announcement" class="bg-[#0d0d1a] border-b border-[#43cfd8]/20 text-[#43cfd8] text-center text-sm py-1.5">Celebrate with the world this June!</div>
<!-- HOLIDAY-BANNER-B-END -->
  </template>

  <nav :class="layout.variant === 'b'
    ? 'lb-nav bg-[#111d35] border-b border-[#2d3f5f] sticky top-0 z-50'
    : 'bg-white border-b border-gray-100 sticky top-0 z-50 shadow-sm'">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-16 items-center gap-6">

        <!-- Logo -->
        <RouterLink to="/" class="flex items-center gap-2.5 flex-shrink-0">
          <LogoMark :size="36" />
          <span
            class="text-xl font-bold tracking-tight"
            :class="layout.variant === 'b' ? 'text-white' : 'text-gray-900'"
            style="font-family: 'Playfair Display', serif"
          >Meridian</span>
        </RouterLink>

        <!-- Desktop nav links -->
        <div class="hidden md:flex items-center gap-1 flex-1">
          <RouterLink to="/"
            class="px-3 py-2 text-sm font-medium transition-colors rounded-lg"
            :class="layout.variant === 'b'
              ? (route.path === '/' ? 'text-violet-400 bg-violet-950' : 'text-slate-400 hover:text-violet-400 hover:bg-slate-900')
              : (route.path === '/' ? 'text-primary-600 bg-primary-50' : 'text-gray-600 hover:text-primary-600 hover:bg-gray-50')"
          >Home</RouterLink>
          <RouterLink to="/blog"
            class="px-3 py-2 text-sm font-medium transition-colors rounded-lg"
            :class="layout.variant === 'b'
              ? (route.path === '/blog' ? 'text-violet-400 bg-violet-950' : 'text-slate-400 hover:text-violet-400 hover:bg-slate-900')
              : (route.path === '/blog' ? 'text-primary-600 bg-primary-50' : 'text-gray-600 hover:text-primary-600 hover:bg-gray-50')"
          >All Posts</RouterLink>

          <RouterLink to="/about"
            class="px-3 py-2 text-sm font-medium transition-colors rounded-lg"
            :class="layout.variant === 'b'
              ? (route.path === '/about' ? 'text-violet-400 bg-violet-950' : 'text-slate-400 hover:text-violet-400 hover:bg-slate-900')
              : (route.path === '/about' ? 'text-primary-600 bg-primary-50' : 'text-gray-600 hover:text-primary-600 hover:bg-gray-50')"
          >About</RouterLink>

          <!-- Topics dropdown -->
          <div class="relative" ref="topicsRef">
            <button
              @click="topicsOpen = !topicsOpen"
              aria-haspopup="true"
              :aria-expanded="topicsOpen.toString()"
              aria-controls="topics-dropdown"
              class="flex items-center gap-1 px-3 py-2 text-sm font-medium transition-colors rounded-lg"
              :class="layout.variant === 'b'
                ? (topicsOpen ? 'text-violet-400 bg-violet-950' : 'text-slate-400 hover:text-violet-400 hover:bg-slate-900')
                : (topicsOpen ? 'text-primary-600 bg-primary-50' : 'text-gray-600 hover:text-primary-600 hover:bg-gray-50')"
            >
              Topics
              <svg class="w-4 h-4 transition-transform" :class="{ 'rotate-180': topicsOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>
            <div v-if="topicsOpen"
              id="topics-dropdown"
              role="menu"
              class="absolute top-full left-0 mt-2 w-56 rounded-xl shadow-lg py-2 z-50"
              :class="layout.variant === 'b' ? 'bg-[#162236] border border-[#2d3f5f]' : 'bg-white border border-gray-100'"
            >
              <RouterLink
                v-for="cat in blog.categories" :key="cat.id"
                :to="`/category/${cat.slug}`"
                @click="topicsOpen = false"
                role="menuitem"
                class="flex items-center gap-3 px-4 py-2.5 text-sm transition-colors"
                :class="layout.variant === 'b'
                  ? 'text-slate-300 hover:bg-slate-900 hover:text-violet-400'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-primary-600'"
              >
                <span class="text-base w-5 text-center">{{ cat.icon }}</span>
                {{ cat.name }}
              </RouterLink>
            </div>
          </div>
        </div>

        <!-- Search -->
        <form @submit="submitSearch" class="hidden md:flex items-center flex-shrink-0">
          <div class="relative">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none"
              :class="layout.variant === 'b' ? 'text-slate-500' : 'text-gray-400'"
              fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
            <input
              v-model="searchQuery" type="text" placeholder="Search…" aria-label="Search posts"
              class="pl-9 pr-4 py-2 text-sm rounded-lg focus:outline-none w-44 focus:w-56 transition-all duration-200"
              :class="layout.variant === 'b'
                ? 'bg-slate-900 border border-slate-700 text-slate-200 placeholder-slate-500 focus:border-violet-500 focus:ring-1 focus:ring-violet-500'
                : 'border border-gray-200 bg-gray-50 focus:border-primary-400 focus:ring-1 focus:ring-primary-400'"
            />
          </div>
        </form>

        <RouterLink to="/admin"
          class="hidden md:block px-4 py-2 rounded-full text-sm font-medium transition-colors flex-shrink-0"
          :class="layout.variant === 'b'
            ? 'bg-violet-600 text-white hover:bg-violet-700'
            : 'bg-primary-600 text-white hover:bg-primary-700'"
        >Admin</RouterLink>

        <!-- Mobile toggle -->
        <button @click="mobileOpen = !mobileOpen" class="md:hidden p-2 rounded-md"
          :aria-expanded="mobileOpen.toString()"
          aria-label="Toggle navigation"
          :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-600'">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path v-if="!mobileOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
            <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Mobile menu -->
      <div v-if="mobileOpen"
        class="md:hidden py-4 border-t space-y-1"
        :class="layout.variant === 'b' ? 'border-slate-800' : 'border-gray-100'"
      >
        <RouterLink to="/" @click="mobileOpen=false"
          class="block px-4 py-2.5 font-medium rounded-lg"
          :class="layout.variant === 'b' ? 'text-slate-300 hover:text-violet-400 hover:bg-slate-900' : 'text-gray-700 hover:text-primary-600 hover:bg-gray-50'"
        >Home</RouterLink>
        <RouterLink to="/blog" @click="mobileOpen=false"
          class="block px-4 py-2.5 font-medium rounded-lg"
          :class="layout.variant === 'b' ? 'text-slate-300 hover:text-violet-400 hover:bg-slate-900' : 'text-gray-700 hover:text-primary-600 hover:bg-gray-50'"
        >All Posts</RouterLink>
        <RouterLink to="/about" @click="mobileOpen=false"
          class="block px-4 py-2.5 font-medium rounded-lg"
          :class="layout.variant === 'b' ? 'text-slate-300 hover:text-violet-400 hover:bg-slate-900' : 'text-gray-700 hover:text-primary-600 hover:bg-gray-50'"
        >About</RouterLink>
        <div class="px-4 pt-2 pb-1 text-xs font-bold uppercase tracking-wider"
          :class="layout.variant === 'b' ? 'text-slate-600' : 'text-gray-400'">Topics</div>
        <RouterLink v-for="cat in blog.categories" :key="cat.id"
          :to="`/category/${cat.slug}`" @click="mobileOpen=false"
          class="flex items-center gap-2 px-4 py-2.5 font-medium rounded-lg"
          :class="layout.variant === 'b' ? 'text-slate-300 hover:text-violet-400 hover:bg-slate-900' : 'text-gray-700 hover:text-primary-600 hover:bg-gray-50'"
        >{{ cat.icon }} {{ cat.name }}</RouterLink>
        <div class="border-t mt-2 pt-2" :class="layout.variant === 'b' ? 'border-slate-800' : 'border-gray-100'">
          <RouterLink to="/admin" @click="mobileOpen=false"
            class="block px-4 py-2.5 font-medium rounded-lg"
            :class="layout.variant === 'b' ? 'text-violet-400 hover:bg-slate-900' : 'text-primary-600 hover:bg-primary-50'"
          >Admin Panel</RouterLink>
        </div>
      </div>
    </div>
  </nav>
</template>
