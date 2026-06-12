<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../../api'
import { format } from 'date-fns'

const posts = ref([])
const pagination = ref({ total: 0, pages: 1, page: 1 })
const loading = ref(false)
const statusFilter = ref('')
const page = ref(1)

onMounted(loadPosts)

async function loadPosts() {
  loading.value = true
  const params = new URLSearchParams({ page: page.value, limit: 15, ...(statusFilter.value ? { status: statusFilter.value } : {}) }).toString()
  const res = await api.get(`/posts/admin?${params}`)
  posts.value = res.data.posts
  pagination.value = res.data
  loading.value = false
}

async function deletePost(id) {
  if (!confirm('Delete this post?')) return
  await api.delete(`/posts/${id}`)
  await loadPosts()
}

async function toggleStatus(post) {
  const newStatus = post.status === 'published' ? 'draft' : 'published'
  await api.put(`/posts/${post.id}`, { status: newStatus })
  post.status = newStatus
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Posts</h1>
        <p class="text-sm text-gray-500 mt-1">{{ pagination.total }} total posts</p>
      </div>
      <RouterLink to="/admin/posts/new" class="bg-primary-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors">+ New Post</RouterLink>
    </div>

    <!-- Filters -->
    <div class="flex gap-2 mb-5">
      <button @click="statusFilter=''; page=1; loadPosts()" :class="!statusFilter ? 'bg-primary-600 text-white' : 'bg-white text-gray-600 border border-gray-200'" class="px-4 py-2 rounded-xl text-sm font-medium transition-colors">All</button>
      <button @click="statusFilter='published'; page=1; loadPosts()" :class="statusFilter==='published' ? 'bg-primary-600 text-white' : 'bg-white text-gray-600 border border-gray-200'" class="px-4 py-2 rounded-xl text-sm font-medium transition-colors">Published</button>
      <button @click="statusFilter='draft'; page=1; loadPosts()" :class="statusFilter==='draft' ? 'bg-primary-600 text-white' : 'bg-white text-gray-600 border border-gray-200'" class="px-4 py-2 rounded-xl text-sm font-medium transition-colors">Drafts</button>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading...</div>
      <table v-else class="w-full">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Post</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider hidden sm:table-cell">Category</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Status</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider hidden lg:table-cell">Views</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider hidden lg:table-cell">Date</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="post in posts" :key="post.id" class="hover:bg-gray-50 transition-colors">
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100">
                  <img v-if="post.featuredImage" :src="post.featuredImage" :alt="post.title || 'Post featured image'" class="w-full h-full object-cover" />
                  <div v-else class="w-full h-full flex items-center justify-center text-lg">{{ post.category?.icon || '📝' }}</div>
                </div>
                <div class="min-w-0">
                  <div class="font-medium text-gray-900 text-sm truncate max-w-xs">{{ post.title }}</div>
                  <div class="text-xs text-gray-400">{{ post.authorName }}</div>
                </div>
              </div>
            </td>
            <td class="px-6 py-4 hidden sm:table-cell">
              <span v-if="post.category" class="text-xs font-medium text-gray-600">{{ post.category.icon }} {{ post.category.name }}</span>
            </td>
            <td class="px-6 py-4 hidden md:table-cell">
              <button @click="toggleStatus(post)" :class="post.status === 'published' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'" class="px-3 py-1 rounded-full text-xs font-semibold capitalize hover:opacity-80 transition-opacity">
                {{ post.status }}
              </button>
            </td>
            <td class="px-6 py-4 text-sm text-gray-500 hidden lg:table-cell">{{ post.views }}</td>
            <td class="px-6 py-4 text-xs text-gray-400 hidden lg:table-cell">{{ format(new Date(post.createdAt), 'MMM d, yyyy') }}</td>
            <td class="px-6 py-4">
              <div class="flex items-center gap-2">
                <RouterLink :to="`/admin/posts/${post.id}/edit`" class="text-xs text-primary-600 hover:underline font-medium">Edit</RouterLink>
                <RouterLink :to="`/blog/${post.slug}`" target="_blank" class="text-xs text-gray-400 hover:text-gray-600">View</RouterLink>
                <button @click="deletePost(post.id)" class="text-xs text-red-500 hover:text-red-700">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="pagination.pages > 1" class="px-6 py-4 border-t border-gray-100 flex gap-2">
        <button v-for="p in pagination.pages" :key="p" @click="page = p; loadPosts()" :class="p === pagination.page ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600'" class="w-8 h-8 rounded-lg text-sm font-medium transition-colors">{{ p }}</button>
      </div>
    </div>
  </div>
</template>
