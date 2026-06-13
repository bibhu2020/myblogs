<script setup>
import { onMounted, ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../../api'
import { format } from 'date-fns'

const posts = ref([])
const pagination = ref({ total: 0, pages: 1, page: 1 })
const loading = ref(false)
const actionLoading = ref(null)   // post id currently being approved/rejected
const statusFilter = ref('pending') // default to pending so new agent posts surface first
const page = ref(1)
const stats = ref({ pending: 0 })

onMounted(async () => {
  await Promise.all([loadPosts(), loadStats()])
})

async function loadStats() {
  try {
    const res = await api.get('/posts/stats')
    stats.value = res.data
  } catch { /* non-critical */ }
}

async function loadPosts() {
  loading.value = true
  const params = new URLSearchParams({
    page: page.value,
    limit: 15,
    ...(statusFilter.value ? { status: statusFilter.value } : {}),
  }).toString()
  const res = await api.get(`/posts/admin?${params}`)
  posts.value = res.data.posts
  pagination.value = res.data
  loading.value = false
}

function setFilter(f) {
  statusFilter.value = f
  page.value = 1
  loadPosts()
}

async function approvePost(post) {
  if (!confirm(`Approve and publish "${post.title}"?`)) return
  actionLoading.value = post.id
  try {
    await api.patch(`/posts/${post.id}/approve`)
    stats.value.pending = Math.max(0, (stats.value.pending || 0) - 1)
    stats.value.published = (stats.value.published || 0) + 1
    await loadPosts()
  } catch (e) {
    alert('Approval failed: ' + (e.response?.data?.message || e.message))
  } finally {
    actionLoading.value = null
  }
}

async function rejectPost(post) {
  if (!confirm(`Reject and permanently delete "${post.title}"?`)) return
  actionLoading.value = post.id
  try {
    await api.patch(`/posts/${post.id}/reject`)
    stats.value.pending = Math.max(0, (stats.value.pending || 0) - 1)
    await loadPosts()
  } catch (e) {
    alert('Rejection failed: ' + (e.response?.data?.message || e.message))
  } finally {
    actionLoading.value = null
  }
}

async function deletePost(id) {
  if (!confirm('Delete this post?')) return
  await api.delete(`/posts/${id}`)
  await loadPosts()
}

async function toggleStatus(post) {
  if (post.status === 'pending') return   // use approve/reject buttons instead
  const newStatus = post.status === 'published' ? 'draft' : 'published'
  await api.put(`/posts/${post.id}`, { status: newStatus })
  post.status = newStatus
}

const pendingCount = computed(() => stats.value.pending || 0)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Posts</h1>
        <p class="text-sm text-gray-500 mt-1">{{ pagination.total }} posts in this view</p>
      </div>
      <RouterLink to="/admin/posts/new" class="bg-primary-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors">+ New Post</RouterLink>
    </div>

    <!-- Pending Approval Alert Banner (shown when not already on Pending tab) -->
    <div v-if="pendingCount > 0 && statusFilter !== 'pending'" class="mb-4 flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
      <span class="text-amber-500 text-xl">⏸️</span>
      <div class="flex-1">
        <span class="font-semibold text-amber-800">{{ pendingCount }} post{{ pendingCount > 1 ? 's' : '' }} awaiting your approval</span>
        <span class="text-amber-600 text-sm ml-2">— AI-generated content needs review before going live</span>
      </div>
      <button @click="setFilter('pending')" class="text-sm font-semibold text-amber-700 bg-amber-100 hover:bg-amber-200 px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap">
        Review now →
      </button>
    </div>

    <!-- Filter Tabs -->
    <div class="flex gap-2 mb-5 flex-wrap">
      <button @click="setFilter('')"
        :class="statusFilter==='' ? 'bg-primary-600 text-white' : 'bg-white text-gray-600 border border-gray-200'"
        class="px-4 py-2 rounded-xl text-sm font-medium transition-colors">All</button>

      <button @click="setFilter('pending')"
        :class="statusFilter==='pending' ? 'bg-amber-500 text-white shadow-sm' : 'bg-white text-gray-600 border border-gray-200'"
        class="px-4 py-2 rounded-xl text-sm font-medium transition-colors flex items-center gap-1.5">
        ⏸️ Pending Approval
        <span v-if="pendingCount > 0"
          :class="statusFilter==='pending' ? 'bg-white text-amber-600' : 'bg-amber-500 text-white'"
          class="text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center leading-none">
          {{ pendingCount }}
        </span>
      </button>

      <button @click="setFilter('published')"
        :class="statusFilter==='published' ? 'bg-primary-600 text-white' : 'bg-white text-gray-600 border border-gray-200'"
        class="px-4 py-2 rounded-xl text-sm font-medium transition-colors">Published</button>

      <button @click="setFilter('draft')"
        :class="statusFilter==='draft' ? 'bg-primary-600 text-white' : 'bg-white text-gray-600 border border-gray-200'"
        class="px-4 py-2 rounded-xl text-sm font-medium transition-colors">Drafts</button>
    </div>

    <!-- Help text when on Pending tab -->
    <div v-if="statusFilter === 'pending' && posts.length > 0" class="mb-4 bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 text-sm text-amber-700">
      <strong>These posts were generated by the AI agent and are not yet visible to readers.</strong>
      Use the Preview link to read the full content before deciding.
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading...</div>

      <div v-else-if="posts.length === 0" class="p-12 text-center text-gray-400">
        <div class="text-4xl mb-3">{{ statusFilter === 'pending' ? '✅' : '📭' }}</div>
        <div class="font-medium text-gray-500">
          {{ statusFilter === 'pending' ? 'No posts pending approval — inbox zero!' : 'No posts found' }}
        </div>
        <div class="text-sm mt-1">{{ statusFilter === 'pending' ? 'Run the post agent to generate new content.' : 'Try a different filter.' }}</div>
      </div>

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
          <tr v-for="post in posts" :key="post.id"
            :class="post.status === 'pending' ? 'bg-amber-50/30 hover:bg-amber-50/60' : 'hover:bg-gray-50'"
            class="transition-colors">
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100 relative">
                  <img v-if="post.featuredImage" :src="post.featuredImage" :alt="post.title || 'Post image'" class="w-full h-full object-cover" />
                  <div v-else class="w-full h-full flex items-center justify-center text-lg">{{ post.category?.icon || '📝' }}</div>
                  <!-- AI badge for pending posts -->
                  <div v-if="post.status === 'pending'"
                    class="absolute -top-1 -right-1 w-4 h-4 bg-amber-400 rounded-full flex items-center justify-center"
                    title="AI-generated, awaiting approval">
                    <span class="text-[9px]">🤖</span>
                  </div>
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
              <span v-if="post.status === 'pending'"
                class="px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-700 inline-flex items-center gap-1">
                ⏸ Pending
              </span>
              <button v-else @click="toggleStatus(post)"
                :class="post.status === 'published' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'"
                class="px-3 py-1 rounded-full text-xs font-semibold capitalize hover:opacity-80 transition-opacity">
                {{ post.status }}
              </button>
            </td>
            <td class="px-6 py-4 text-sm text-gray-500 hidden lg:table-cell">{{ post.views }}</td>
            <td class="px-6 py-4 text-xs text-gray-400 hidden lg:table-cell">{{ format(new Date(post.createdAt), 'MMM d, yyyy') }}</td>
            <td class="px-6 py-4">
              <!-- Pending posts: Preview + Approve + Reject -->
              <div v-if="post.status === 'pending'" class="flex items-center gap-2 flex-wrap">
                <RouterLink :to="`/admin/posts/${post.id}/edit`"
                  class="text-xs text-gray-500 hover:text-gray-700 underline">Preview</RouterLink>
                <button @click="approvePost(post)"
                  :disabled="actionLoading === post.id"
                  class="text-xs font-semibold text-white bg-green-500 hover:bg-green-600 disabled:opacity-40 px-3 py-1 rounded-lg transition-colors flex items-center gap-1">
                  <span v-if="actionLoading === post.id">…</span>
                  <span v-else>✓ Approve</span>
                </button>
                <button @click="rejectPost(post)"
                  :disabled="actionLoading === post.id"
                  class="text-xs font-semibold text-white bg-red-500 hover:bg-red-600 disabled:opacity-40 px-3 py-1 rounded-lg transition-colors flex items-center gap-1">
                  <span v-if="actionLoading === post.id">…</span>
                  <span v-else>✕ Reject</span>
                </button>
              </div>
              <!-- Published/Draft posts: normal actions -->
              <div v-else class="flex items-center gap-2">
                <RouterLink :to="`/admin/posts/${post.id}/edit`" class="text-xs text-primary-600 hover:underline font-medium">Edit</RouterLink>
                <RouterLink :to="`/blog/${post.slug}`" target="_blank" class="text-xs text-gray-400 hover:text-gray-600">View</RouterLink>
                <button @click="deletePost(post.id)" class="text-xs text-red-500 hover:text-red-700">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="pagination.pages > 1" class="px-6 py-4 border-t border-gray-100 flex gap-2 flex-wrap">
        <button v-for="p in pagination.pages" :key="p" @click="page = p; loadPosts()"
          :class="p === pagination.page ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600'"
          class="w-8 h-8 rounded-lg text-sm font-medium transition-colors">{{ p }}</button>
      </div>
    </div>
  </div>
</template>
