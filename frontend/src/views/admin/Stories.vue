<script setup>
import { onMounted, ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../../api'
import { format } from 'date-fns'

const stories = ref([])
const pagination = ref({ total: 0, pages: 1, page: 1 })
const loading = ref(false)
const actionLoading = ref(null)
const statusFilter = ref('pending')
const page = ref(1)
const stats = ref({ pending: 0 })

onMounted(async () => {
  await Promise.all([loadStories(), loadStats()])
})

async function loadStats() {
  try {
    const res = await api.get('/stories/stats')
    stats.value = res.data
  } catch { /* non-critical */ }
}

async function loadStories() {
  loading.value = true
  const params = new URLSearchParams({
    page: page.value,
    limit: 15,
    ...(statusFilter.value ? { status: statusFilter.value } : {}),
  }).toString()
  const res = await api.get(`/stories/admin?${params}`)
  stories.value = res.data.stories
  pagination.value = res.data
  loading.value = false
}

function setFilter(f) {
  statusFilter.value = f
  page.value = 1
  loadStories()
}

async function approveStory(story) {
  if (!confirm(`Approve and publish "${story.title}"?`)) return
  actionLoading.value = story.id
  try {
    await api.patch(`/stories/${story.id}/approve`)
    stats.value.pending = Math.max(0, (stats.value.pending || 0) - 1)
    await loadStories()
  } catch (e) {
    alert('Approval failed: ' + (e.response?.data?.message || e.message))
  } finally {
    actionLoading.value = null
  }
}

async function rejectStory(story) {
  if (!confirm(`Reject and permanently delete "${story.title}"?`)) return
  actionLoading.value = story.id
  try {
    await api.patch(`/stories/${story.id}/reject`)
    stats.value.pending = Math.max(0, (stats.value.pending || 0) - 1)
    await loadStories()
  } catch (e) {
    alert('Rejection failed: ' + (e.response?.data?.message || e.message))
  } finally {
    actionLoading.value = null
  }
}

async function deleteStory(id) {
  if (!confirm('Delete this story?')) return
  await api.delete(`/stories/${id}`)
  await loadStories()
}

async function toggleStatus(story) {
  if (story.status === 'pending') return
  const newStatus = story.status === 'published' ? 'draft' : 'published'
  await api.put(`/stories/${story.id}`, { status: newStatus })
  story.status = newStatus
}

const pendingCount = computed(() => stats.value.pending || 0)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">📖 Stories</h1>
        <p class="text-sm text-gray-500 mt-1">{{ pagination.total }} stories in this view</p>
      </div>
      <RouterLink to="/admin/stories/new" class="bg-indigo-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-colors">+ New Story</RouterLink>
    </div>

    <!-- Pending approval alert -->
    <div v-if="pendingCount > 0 && statusFilter !== 'pending'" class="mb-4 flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
      <span class="text-amber-500 text-xl">⏸️</span>
      <div class="flex-1">
        <span class="font-semibold text-amber-800">{{ pendingCount }} story{{ pendingCount > 1 ? 'ies' : '' }} awaiting approval</span>
        <span class="text-amber-600 text-sm ml-2">— AI-generated stories need review before going live</span>
      </div>
      <button @click="setFilter('pending')" class="text-sm font-semibold text-amber-700 bg-amber-100 hover:bg-amber-200 px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap">
        Review now →
      </button>
    </div>

    <!-- Filter tabs -->
    <div class="flex gap-2 mb-5 flex-wrap">
      <button @click="setFilter('')" :class="statusFilter==='' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border border-gray-200'" class="px-4 py-2 rounded-xl text-sm font-medium transition-colors">All</button>

      <button @click="setFilter('pending')"
        :class="statusFilter==='pending' ? 'bg-amber-500 text-white shadow-sm' : 'bg-white text-gray-600 border border-gray-200'"
        class="px-4 py-2 rounded-xl text-sm font-medium transition-colors flex items-center gap-1.5">
        ⏸️ Pending
        <span v-if="pendingCount > 0" :class="statusFilter==='pending' ? 'bg-white text-amber-600' : 'bg-amber-500 text-white'" class="text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center leading-none">
          {{ pendingCount }}
        </span>
      </button>

      <button @click="setFilter('published')" :class="statusFilter==='published' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border border-gray-200'" class="px-4 py-2 rounded-xl text-sm font-medium transition-colors">Published</button>
      <button @click="setFilter('draft')" :class="statusFilter==='draft' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border border-gray-200'" class="px-4 py-2 rounded-xl text-sm font-medium transition-colors">Drafts</button>
    </div>

    <!-- Pending help text -->
    <div v-if="statusFilter === 'pending' && stories.length > 0" class="mb-4 bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 text-sm text-amber-700">
      <strong>These stories were generated by the Story Agent and are not yet visible to readers.</strong>
      Use the Preview link to read the full content before deciding.
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading...</div>

      <div v-else-if="stories.length === 0" class="p-12 text-center text-gray-400">
        <div class="text-4xl mb-3">{{ statusFilter === 'pending' ? '✅' : '📭' }}</div>
        <div class="font-medium text-gray-500">
          {{ statusFilter === 'pending' ? 'No stories pending approval!' : 'No stories found' }}
        </div>
        <div class="text-sm mt-1">{{ statusFilter === 'pending' ? 'The story agent runs weekly.' : 'Try a different filter.' }}</div>
      </div>

      <div v-else class="overflow-x-auto"><table class="w-full">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Story</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider hidden sm:table-cell">Genre</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Status</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider hidden lg:table-cell">Read</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider hidden lg:table-cell">Date</th>
            <th class="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="story in stories" :key="story.id"
            :class="story.status === 'pending' ? 'bg-amber-50/30 hover:bg-amber-50/60' : 'hover:bg-gray-50'"
            class="transition-colors">
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 bg-indigo-100 relative">
                  <img v-if="story.featuredImage" :src="story.featuredImage" :alt="story.title" class="w-full h-full object-cover" />
                  <div v-else class="w-full h-full flex items-center justify-center text-lg">📖</div>
                  <div v-if="story.status === 'pending'" class="absolute -top-1 -right-1 w-4 h-4 bg-amber-400 rounded-full flex items-center justify-center" title="AI-generated, awaiting approval">
                    <span class="text-[9px]">🤖</span>
                  </div>
                </div>
                <div class="min-w-0">
                  <div class="font-medium text-gray-900 text-sm truncate max-w-xs">{{ story.title }}</div>
                  <div class="text-xs text-gray-400">{{ story.authorName }}</div>
                </div>
              </div>
            </td>
            <td class="px-6 py-4 hidden sm:table-cell">
              <div class="flex flex-wrap gap-1">
                <span v-if="story.category" class="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">{{ story.category }}</span>
                <span v-if="story.genre" class="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">{{ story.genre }}</span>
              </div>
            </td>
            <td class="px-6 py-4 hidden md:table-cell">
              <span v-if="story.status === 'pending'" class="px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-700 inline-flex items-center gap-1">⏸ Pending</span>
              <button v-else @click="toggleStatus(story)"
                :class="story.status === 'published' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'"
                class="px-3 py-1 rounded-full text-xs font-semibold capitalize hover:opacity-80 transition-opacity">
                {{ story.status }}
              </button>
            </td>
            <td class="px-6 py-4 text-sm text-gray-500 hidden lg:table-cell">{{ story.readTime || '—' }} min</td>
            <td class="px-6 py-4 text-xs text-gray-400 hidden lg:table-cell">{{ format(new Date(story.createdAt), 'MMM d, yyyy') }}</td>
            <td class="px-6 py-4">
              <div v-if="story.status === 'pending'" class="flex items-center gap-2 flex-wrap">
                <RouterLink :to="`/admin/stories/${story.id}/edit`" class="text-xs text-gray-500 hover:text-gray-700 underline">Preview</RouterLink>
                <button @click="approveStory(story)" :disabled="actionLoading === story.id"
                  class="text-xs font-semibold text-white bg-green-500 hover:bg-green-600 disabled:opacity-40 px-3 py-1 rounded-lg transition-colors">
                  <span v-if="actionLoading === story.id">…</span>
                  <span v-else>✓ Approve</span>
                </button>
                <button @click="rejectStory(story)" :disabled="actionLoading === story.id"
                  class="text-xs font-semibold text-white bg-red-500 hover:bg-red-600 disabled:opacity-40 px-3 py-1 rounded-lg transition-colors">
                  <span v-if="actionLoading === story.id">…</span>
                  <span v-else>✕ Reject</span>
                </button>
              </div>
              <div v-else class="flex items-center gap-2">
                <RouterLink :to="`/admin/stories/${story.id}/edit`" class="text-xs text-indigo-600 hover:underline font-medium">Edit</RouterLink>
                <RouterLink :to="`/story/${story.slug}`" target="_blank" class="text-xs text-gray-400 hover:text-gray-600">View</RouterLink>
                <button @click="deleteStory(story.id)" class="text-xs text-red-500 hover:text-red-700">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table></div>

      <div v-if="pagination.pages > 1" class="px-6 py-4 border-t border-gray-100 flex gap-2 flex-wrap">
        <button v-for="p in pagination.pages" :key="p" @click="page = p; loadStories()"
          :class="p === pagination.page ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'"
          class="w-8 h-8 rounded-lg text-sm font-medium transition-colors">{{ p }}</button>
      </div>
    </div>
  </div>
</template>
