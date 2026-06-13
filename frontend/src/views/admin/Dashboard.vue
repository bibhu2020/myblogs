<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../../api'

const stats = ref({ total: 0, published: 0, drafts: 0, pending: 0, totalViews: 0 })
const recentPosts = ref([])
const categories = ref([])

onMounted(async () => {
  const [statsRes, postsRes, catsRes] = await Promise.all([
    api.get('/posts/stats'),
    api.get('/posts/admin?limit=5'),
    api.get('/categories'),
  ])
  stats.value = statsRes.data
  recentPosts.value = postsRes.data.posts
  categories.value = catsRes.data
})
</script>

<template>
  <div>
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Dashboard</h1>
      <p class="text-gray-500 text-sm mt-1">Your content overview at a glance</p>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
        <div class="text-3xl font-bold text-gray-900 mb-1">{{ stats.total }}</div>
        <div class="text-sm text-gray-500">Total Posts</div>
        <div class="w-8 h-1 bg-primary-500 rounded-full mt-3"></div>
      </div>
      <div class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
        <div class="text-3xl font-bold text-green-600 mb-1">{{ stats.published }}</div>
        <div class="text-sm text-gray-500">Published</div>
        <div class="w-8 h-1 bg-green-500 rounded-full mt-3"></div>
      </div>
      <RouterLink to="/admin/posts" class="block bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:border-amber-200 transition-colors" :class="stats.pending > 0 ? 'border-amber-200 bg-amber-50/30' : ''">
        <div class="flex items-start justify-between">
          <div>
            <div class="text-3xl font-bold mb-1" :class="stats.pending > 0 ? 'text-amber-600' : 'text-gray-400'">{{ stats.pending || 0 }}</div>
            <div class="text-sm text-gray-500">Pending Approval</div>
          </div>
          <span v-if="stats.pending > 0" class="text-lg">⏸️</span>
        </div>
        <div class="w-8 h-1 rounded-full mt-3" :class="stats.pending > 0 ? 'bg-amber-500' : 'bg-gray-200'"></div>
      </RouterLink>
      <div class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
        <div class="text-3xl font-bold text-purple-600 mb-1">{{ Number(stats.totalViews || 0).toLocaleString() }}</div>
        <div class="text-sm text-gray-500">Total Views</div>
        <div class="w-8 h-1 bg-purple-500 rounded-full mt-3"></div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Recent Posts -->
      <div class="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div class="flex items-center justify-between mb-5">
          <h2 class="font-bold text-gray-900">Recent Posts</h2>
          <RouterLink to="/admin/posts" class="text-sm text-primary-600 hover:underline">View all</RouterLink>
        </div>
        <div class="space-y-3">
          <div v-for="post in recentPosts" :key="post.id" class="flex items-center gap-4 p-3 rounded-xl hover:bg-gray-50 transition-colors">
            <div class="w-12 h-12 rounded-xl overflow-hidden flex-shrink-0 bg-gray-100">
              <img v-if="post.featuredImage" :src="post.featuredImage" :alt="post.title || 'Post featured image'" class="w-full h-full object-cover" />
              <div v-else class="w-full h-full flex items-center justify-center text-xl">{{ post.category?.icon || '📝' }}</div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-medium text-gray-900 text-sm truncate">{{ post.title }}</div>
              <div class="text-xs text-gray-400 mt-0.5 flex items-center gap-2">
                <span :class="post.status === 'published' ? 'text-green-600' : 'text-yellow-600'" class="font-medium capitalize">{{ post.status }}</span>
                <span>·</span>
                <span>{{ post.views }} views</span>
              </div>
            </div>
            <RouterLink :to="`/admin/posts/${post.id}/edit`" class="text-xs text-primary-600 hover:underline flex-shrink-0">Edit</RouterLink>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="space-y-4">
        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h2 class="font-bold text-gray-900 mb-4">Quick Actions</h2>
          <div class="space-y-2">
            <RouterLink to="/admin/posts/new" class="flex items-center gap-3 w-full px-4 py-3 bg-primary-600 text-white rounded-xl text-sm font-medium hover:bg-primary-700 transition-colors">
              <span>✏️</span> Write New Post
            </RouterLink>
            <RouterLink to="/admin/media" class="flex items-center gap-3 w-full px-4 py-3 bg-gray-100 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-200 transition-colors">
              <span>🖼️</span> Upload Media
            </RouterLink>
            <RouterLink to="/admin/users" class="flex items-center gap-3 w-full px-4 py-3 bg-gray-100 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-200 transition-colors">
              <span>👤</span> Add Guest User
            </RouterLink>
          </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h2 class="font-bold text-gray-900 mb-4">Categories</h2>
          <div class="space-y-2">
            <div v-for="cat in categories" :key="cat.id" class="flex items-center gap-2 text-sm">
              <span>{{ cat.icon }}</span>
              <span class="text-gray-700 font-medium">{{ cat.name }}</span>
              <span class="ml-auto text-gray-400 text-xs">{{ cat.slug }}</span>
            </div>
          </div>
          <RouterLink to="/admin/categories" class="text-xs text-primary-600 hover:underline mt-3 block">Manage categories →</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>
