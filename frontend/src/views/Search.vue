<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useBlogStore } from '../stores/blog'
import { useLayoutStore } from '../stores/layout'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import { format } from 'date-fns'
import api from '../api'

const blog = useBlogStore()
const layout = useLayoutStore()
const route = useRoute()
const router = useRouter()

const query = ref(route.query.s || '')
const activeCategorySlug = ref(route.query.category || '')
const results = ref([])
const total = ref(0)
const loading = ref(false)
const searched = ref(false)

function formatDate(d) {
  return format(new Date(d), 'MMM d, yyyy')
}

function stripHtml(html) {
  return html?.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim() || ''
}

async function doSearch() {
  if (!query.value.trim() && !activeCategorySlug.value) {
    results.value = []
    searched.value = false
    return
  }
  loading.value = true
  const params = { limit: 50 }
  if (query.value.trim()) params.search = query.value.trim()
  if (activeCategorySlug.value) params.category = activeCategorySlug.value
  const res = await blog.fetchPosts(params)
  results.value = res.posts || []
  total.value = res.total || 0
  searched.value = true
  loading.value = false
}

let timer
watch(query, () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    router.replace({ query: { ...(query.value ? { s: query.value } : {}), ...(activeCategorySlug.value ? { category: activeCategorySlug.value } : {}) } })
    doSearch()
  }, 350)
})

watch(activeCategorySlug, () => {
  router.replace({ query: { ...(query.value ? { s: query.value } : {}), ...(activeCategorySlug.value ? { category: activeCategorySlug.value } : {}) } })
  doSearch()
})

onMounted(async () => {
  await blog.fetchCategories()
  if (query.value || activeCategorySlug.value) doSearch()
})

function toggleCategory(slug) {
  activeCategorySlug.value = activeCategorySlug.value === slug ? '' : slug
}

function getCategoryForSlug(slug) {
  return blog.categories.find(c => c.slug === slug)
}

function submitSearch(e) {
  e.preventDefault()
  clearTimeout(timer)
  router.replace({ query: { ...(query.value ? { s: query.value } : {}), ...(activeCategorySlug.value ? { category: activeCategorySlug.value } : {}) } })
  doSearch()
}
</script>

<template>
  <div :class="layout.variant === 'b' ? 'min-h-screen bg-[#0f172a]' : 'min-h-screen bg-gray-50'">
    <Navbar />
    <main id="main-content" tabindex="-1" class="outline-none">

    <!-- Search Header -->
    <div :class="layout.variant === 'b' ? 'bg-[#111d35] border-b border-[#2d3f5f]' : 'bg-white border-b border-gray-200'">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <h1 class="text-3xl font-bold mb-6" :class="layout.variant === 'b' ? 'text-slate-100' : 'text-gray-900'" style="font-family:'Playfair Display',serif">
          Search Articles
        </h1>
        <form @submit="submitSearch" class="relative max-w-3xl">
          <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 pointer-events-none" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-500'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
          <input
            v-model="query"
            type="text"
            placeholder="Search by topic, keyword, or author…"
            aria-label="Search posts by topic, keyword, or author"
            class="w-full pl-12 pr-32 py-3.5 text-base rounded-lg focus:outline-none shadow-sm"
            :class="layout.variant === 'b'
              ? 'bg-[#1c2d44] border border-[#2d3f5f] text-slate-200 placeholder-slate-500 focus:ring-2 focus:ring-violet-500 focus:border-transparent'
              : 'border border-gray-300 bg-white focus:ring-2 focus:ring-primary-500 focus:border-transparent'"
            autofocus
          />
          <button type="submit" class="absolute right-2 top-1/2 -translate-y-1/2 px-5 py-2 text-white text-sm font-semibold rounded-md transition-colors"
            :class="layout.variant === 'b' ? 'bg-violet-600 hover:bg-violet-700' : 'bg-primary-600 hover:bg-primary-700'">
            Search
          </button>
        </form>
      </div>
    </div>

    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="flex gap-8 items-start">

        <!-- Sidebar Filters -->
        <aside class="hidden lg:block w-60 flex-shrink-0">
          <div class="rounded-xl shadow-sm p-5 sticky top-24" :class="layout.variant === 'b' ? 'bg-[#162236] border border-[#2d3f5f]' : 'bg-white border border-gray-200'">
            <h2 class="text-xs font-bold uppercase tracking-widest mb-4" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-500'">Filter by Topic</h2>
            <ul class="space-y-1">
              <li>
                <button
                  @click="toggleCategory('')"
                  class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left"
                  :class="activeCategorySlug === ''
                    ? (layout.variant === 'b' ? 'bg-violet-950 text-violet-400' : 'bg-primary-50 text-primary-700')
                    : (layout.variant === 'b' ? 'text-slate-400 hover:bg-slate-900 hover:text-violet-400' : 'text-gray-700 hover:bg-gray-50')"
                >
                  <span class="text-base">🌐</span>
                  <span>All Topics</span>
                  <span v-if="activeCategorySlug === '' && searched" class="ml-auto text-xs font-semibold rounded-full px-2 py-0.5"
                    :class="layout.variant === 'b' ? 'text-violet-400 bg-violet-950' : 'text-primary-600 bg-primary-100'">{{ total }}</span>
                </button>
              </li>
              <li v-for="cat in blog.categories" :key="cat.id">
                <button
                  @click="toggleCategory(cat.slug)"
                  class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left"
                  :class="activeCategorySlug === cat.slug
                    ? (layout.variant === 'b' ? 'bg-violet-950 text-violet-400' : 'bg-primary-50 text-primary-700')
                    : (layout.variant === 'b' ? 'text-slate-400 hover:bg-slate-900 hover:text-violet-400' : 'text-gray-700 hover:bg-gray-50')"
                >
                  <span class="text-base">{{ cat.icon }}</span>
                  <span>{{ cat.name }}</span>
                  <span
                    v-if="activeCategorySlug === cat.slug && searched"
                    class="ml-auto text-xs font-semibold rounded-full px-2 py-0.5"
                    :class="layout.variant === 'b' ? 'text-violet-400 bg-violet-950' : 'text-primary-600 bg-primary-100'"
                  >{{ total }}</span>
                </button>
              </li>
            </ul>
          </div>
        </aside>

        <!-- Main Results -->
        <div class="flex-1 min-w-0">

          <!-- Result count -->
          <div v-if="searched" class="mb-5 flex items-center justify-between">
            <p class="text-sm" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-600'">
              <span v-if="loading">Searching…</span>
              <span v-else>
                <span class="font-semibold" :class="layout.variant === 'b' ? 'text-slate-200' : 'text-gray-900'">{{ total }}</span>
                result{{ total !== 1 ? 's' : '' }}
                <span v-if="query"> for <span class="font-semibold" :class="layout.variant === 'b' ? 'text-slate-200' : 'text-gray-900'">"{{ query }}"</span></span>
                <span v-if="activeCategorySlug"> in <span class="font-semibold" :style="{ color: getCategoryForSlug(activeCategorySlug)?.color }">{{ getCategoryForSlug(activeCategorySlug)?.icon }} {{ getCategoryForSlug(activeCategorySlug)?.name }}</span></span>
              </span>
            </p>
          </div>

          <!-- Loading skeleton -->
          <div v-if="loading" class="space-y-4">
            <div v-for="n in 3" :key="n" class="rounded-xl shadow-sm p-5 flex gap-5 animate-pulse" :class="layout.variant === 'b' ? 'bg-[#162236] border border-[#2d3f5f]' : 'bg-white border border-gray-200'">
              <div class="w-44 h-28 rounded-lg flex-shrink-0" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
              <div class="flex-1 space-y-3">
                <div class="h-3 rounded w-24" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
                <div class="h-5 rounded w-3/4" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
                <div class="h-3 rounded w-full" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
                <div class="h-3 rounded w-5/6" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
                <div class="h-3 rounded w-32" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
              </div>
            </div>
          </div>

          <!-- Results list -->
          <div v-else-if="results.length" class="space-y-4">
            <RouterLink
              v-for="post in results"
              :key="post.id"
              :to="`/blog/${post.slug}`"
              class="group flex gap-5 rounded-xl shadow-sm transition-all duration-200 p-5 overflow-hidden"
              :class="layout.variant === 'b'
                ? 'bg-[#162236] border border-[#2d3f5f] hover:border-violet-600 hover:bg-[#1c2d44]'
                : 'bg-white border border-gray-200 hover:shadow-md hover:border-primary-200'"
            >
              <!-- Thumbnail -->
              <div class="w-44 h-32 flex-shrink-0 rounded-lg overflow-hidden" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-100'">
                <img
                  v-if="post.featuredImage"
                  :src="post.featuredImage"
                  :alt="post.title"
                  class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  loading="lazy"
                />
                <div v-else class="w-full h-full flex items-center justify-center"
                  :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gradient-to-br from-primary-50 to-indigo-100'">
                  <span class="text-4xl">{{ post.category?.icon || '📝' }}</span>
                </div>
              </div>

              <!-- Content -->
              <div class="flex-1 min-w-0 flex flex-col justify-between py-0.5">
                <div>
                  <!-- Category badge -->
                  <div class="flex items-center gap-2 mb-2">
                    <span
                      v-if="post.category"
                      class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold text-white"
                      :style="{ background: post.category.color || '#3B82F6' }"
                    >
                      {{ post.category.icon }} {{ post.category.name }}
                    </span>
                  </div>

                  <!-- Title -->
                  <h3
                    class="text-lg font-bold transition-colors line-clamp-2 mb-2 leading-snug"
                    :class="layout.variant === 'b' ? 'text-slate-100 group-hover:text-violet-300' : 'text-gray-900 group-hover:text-primary-600'"
                    style="font-family:'Playfair Display',serif"
                  >
                    {{ post.title }}
                  </h3>

                  <!-- Excerpt -->
                  <p class="text-sm leading-relaxed line-clamp-2" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-500'">
                    {{ post.excerpt || stripHtml(post.content) }}
                  </p>
                </div>

                <!-- Meta -->
                <div class="flex items-center gap-3 mt-3 text-xs" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-500'">
                  <div class="flex items-center gap-1.5">
                    <div class="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0" :class="layout.variant === 'b' ? 'bg-violet-700' : 'bg-primary-600'">
                      <span class="text-white font-bold text-[10px]">{{ (post.authorName || 'A').charAt(0) }}</span>
                    </div>
                    <span class="font-medium" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-600'">{{ post.authorName }}</span>
                  </div>
                  <span :class="layout.variant === 'b' ? 'text-slate-500' : 'text-gray-300'">·</span>
                  <span>{{ formatDate(post.createdAt) }}</span>
                  <span :class="layout.variant === 'b' ? 'text-slate-500' : 'text-gray-300'">·</span>
                  <span>{{ post.readTime || 5 }} min read</span>
                  <span v-if="post.views" :class="layout.variant === 'b' ? 'text-slate-500' : 'text-gray-300'">·</span>
                  <span v-if="post.views" class="flex items-center gap-1">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                    </svg>
                    {{ post.views.toLocaleString() }}
                  </span>
                </div>
              </div>
            </RouterLink>
          </div>

          <!-- No results -->
          <div v-else-if="searched && !loading" class="rounded-xl shadow-sm py-20 text-center" :class="layout.variant === 'b' ? 'bg-[#162236] border border-[#2d3f5f]' : 'bg-white border border-gray-200'">
            <div class="text-5xl mb-4">🔍</div>
            <p class="text-lg font-semibold mb-1" :class="layout.variant === 'b' ? 'text-slate-200' : 'text-gray-800'">No results found</p>
            <p class="text-sm" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-500'">
              <span v-if="query">Try different keywords for <span class="font-medium">"{{ query }}"</span></span>
              <span v-else>No posts in this category yet</span>
            </p>
          </div>

          <!-- Empty state (not yet searched) -->
          <div v-else class="rounded-xl shadow-sm py-20 text-center" :class="layout.variant === 'b' ? 'bg-[#162236] border border-[#2d3f5f]' : 'bg-white border border-gray-200'">
            <div class="text-5xl mb-4">✍️</div>
            <p class="text-base font-semibold mb-1" :class="layout.variant === 'b' ? 'text-slate-200' : 'text-gray-700'">Start typing to search</p>
            <p class="text-sm" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-500'">Search across all articles, or filter by topic on the left</p>

            <!-- Quick category browse -->
            <div class="flex flex-wrap justify-center gap-2 mt-6">
              <button
                v-for="cat in blog.categories"
                :key="cat.id"
                @click="toggleCategory(cat.slug)"
                class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium text-white shadow-sm hover:opacity-90 transition-opacity"
                :style="{ background: cat.color }"
              >
                {{ cat.icon }} {{ cat.name }}
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>

    <Footer />
      </main>
  </div>
</template>