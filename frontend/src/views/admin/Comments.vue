<script setup>
import { onMounted, ref } from 'vue'
import api from '../../api'
import { format } from 'date-fns'

const comments = ref([])
onMounted(load)

async function load() {
  const res = await api.get('/comments')
  comments.value = res.data
}

async function approve(id) {
  await api.put(`/comments/${id}/approve`)
  const c = comments.value.find(c => c.id === id)
  if (c) c.approved = true
}

async function remove(id) {
  if (!confirm('Delete comment?')) return
  await api.delete(`/comments/${id}`)
  comments.value = comments.value.filter(c => c.id !== id)
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Comments</h1>
      <p class="text-sm text-gray-500 mt-1">{{ comments.filter(c=>!c.approved).length }} pending approval</p>
    </div>

    <div class="space-y-3">
      <div v-for="comment in comments" :key="comment.id" class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-2">
              <div class="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0"><span class="text-primary-600 font-bold text-sm">{{ comment.authorName.charAt(0) }}</span></div>
              <div>
                <span class="font-semibold text-gray-900 text-sm">{{ comment.authorName }}</span>
                <span class="text-gray-400 text-xs ml-2">{{ format(new Date(comment.createdAt), 'MMM d, yyyy') }}</span>
              </div>
              <span :class="comment.approved ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'" class="px-2 py-0.5 rounded-full text-xs font-semibold">{{ comment.approved ? 'Approved' : 'Pending' }}</span>
            </div>
            <p class="text-gray-600 text-sm ml-11">{{ comment.content }}</p>
            <p v-if="comment.post" class="text-xs text-primary-600 ml-11 mt-1">On: {{ comment.post.title }}</p>
          </div>
          <div class="flex gap-2 flex-shrink-0">
            <button v-if="!comment.approved" @click="approve(comment.id)" class="text-xs bg-green-100 text-green-700 px-3 py-1.5 rounded-lg hover:bg-green-200 transition-colors font-medium">Approve</button>
            <button @click="remove(comment.id)" class="text-xs bg-red-50 text-red-600 px-3 py-1.5 rounded-lg hover:bg-red-100 transition-colors font-medium">Delete</button>
          </div>
        </div>
      </div>
      <div v-if="!comments.length" class="text-center py-12 text-gray-400">No comments yet</div>
    </div>
  </div>
</template>
