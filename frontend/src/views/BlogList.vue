<script setup>
import { onMounted, ref, watch } from 'vue'
import { useBlogStore } from '../stores/blog'
import { useLayoutStore } from '../stores/layout'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import PostCard from '../components/PostCard.vue'

const blog = useBlogStore()
const layout = useLayoutStore()
const page = ref(1)

onMounted(async () => {
  await blog.fetchCategories()
  await loadPosts()
})

async function loadPosts() {
  await blog.fetchPosts({ page: page.value, limit: 12 })
}

watch(page, loadPosts)
</script>

<template>
  <div :class="layout.variant === 'b' ? 'min-h-screen bg-[#0f172a]' : 'min-h-screen bg-white'">
    <Navbar />
    <main id="main-content" tabindex="-1" class="outline-none">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div class="mb-10">
        <h1 class="text-4xl font-bold mb-3" :class="layout.variant === 'b' ? 'text-slate-100' : 'text-gray-900'" style="font-family:'Playfair Display',serif">All Posts</h1>
        <p :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-500'">{{ blog.pagination.total }} articles on technology, travel, and more</p>
      </div>

      <div v-if="blog.loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="animate-pulse">
          <div class="rounded-2xl aspect-[16/10] mb-4" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
          <div class="h-4 rounded mb-2" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
          <div class="h-4 rounded w-2/3" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-200'"></div>
        </div>
      </div>

      <div v-else>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <PostCard v-for="post in blog.posts" :key="post.id" :post="post" />
        </div>

        <!-- Pagination -->
        <div v-if="blog.pagination.pages > 1" class="flex justify-center gap-2 mt-12">
          <button
            v-for="p in blog.pagination.pages"
            :key="p"
            @click="page = p"
            class="w-10 h-10 rounded-full text-sm font-medium transition-colors"
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