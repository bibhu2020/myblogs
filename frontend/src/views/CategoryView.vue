<script setup>
import { onMounted, ref, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useBlogStore } from '../stores/blog'
import { useLayoutStore } from '../stores/layout'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import PostCard from '../components/PostCard.vue'

const blog = useBlogStore()
const layout = useLayoutStore()
const route = useRoute()
const page = ref(1)
const category = computed(() => blog.categories.find(c => c.slug === route.params.slug))

onMounted(async () => {
  await blog.fetchCategories()
  await loadPosts()
})

async function loadPosts() {
  await blog.fetchPosts({ category: route.params.slug, page: page.value, limit: 12 })
}

watch(() => route.params.slug, () => { page.value = 1; loadPosts() })
watch(page, loadPosts)
</script>

<template>
  <div :class="layout.variant === 'b' ? 'min-h-screen bg-[#0f172a]' : 'min-h-screen bg-white'">
    <Navbar />
    <main id="main-content" tabindex="-1" class="outline-none">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div class="flex items-center gap-4 mb-10">
        <div v-if="category" class="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl" :style="{ background: (category.color || '#3B82F6') + '20' }">{{ category.icon }}</div>
        <div>
          <h1 class="text-4xl font-bold" :class="layout.variant === 'b' ? 'text-slate-100' : 'text-gray-900'" style="font-family:'Playfair Display',serif">{{ category?.name || route.params.slug }}</h1>
          <p class="mt-1" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-500'">{{ category?.description }} · {{ blog.pagination.total }} articles</p>
        </div>
      </div>

      <div v-if="blog.loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="animate-pulse">
          <div class="rounded-2xl aspect-[16/10] mb-4" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
          <div class="h-4 rounded mb-2" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
          <div class="h-4 rounded w-2/3" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
        </div>
      </div>
      <div v-else>
        <div v-if="!blog.posts.length" class="text-center py-24" :class="layout.variant === 'b' ? 'text-slate-500' : 'text-gray-400'">
          <div class="text-6xl mb-4">📭</div>
          <p class="text-xl font-medium">No posts in this category yet</p>
        </div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <PostCard v-for="post in blog.posts" :key="post.id" :post="post" />
        </div>
        <div v-if="blog.pagination.pages > 1" class="flex justify-center gap-2 mt-12">
          <button v-for="p in blog.pagination.pages" :key="p" @click="page = p" class="w-10 h-10 rounded-full text-sm font-medium transition-colors"
            :class="p === page
              ? (layout.variant === 'b' ? 'bg-violet-600 text-white' : 'bg-primary-600 text-white')
              : (layout.variant === 'b' ? 'bg-slate-800 text-slate-300 hover:bg-slate-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200')"
          >{{ p }}</button>
        </div>
      </div>
    </div>
    <Footer />
      </main>
  </div>
</template>