<script setup>
import { onMounted, ref } from 'vue'
import api from '../../api'

const media = ref([])
const uploading = ref(false)
const uploadError = ref('')
const selected = ref(null)
const fileInput = ref(null)

onMounted(loadMedia)

async function loadMedia() {
  const res = await api.get('/media')
  media.value = res.data
}

async function upload(event) {
  const file = event.target.files[0]
  if (!file) return
  uploading.value = true
  uploadError.value = ''
  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('alt', file.name)
    await api.post('/media/upload', fd)
    await loadMedia()
  } catch (e) {
    uploadError.value = e.response?.data?.message || 'Upload failed. Please try again.'
  } finally {
    uploading.value = false
    fileInput.value.value = ''
  }
}

async function deleteMedia(id) {
  if (!confirm('Delete this file?')) return
  await api.delete(`/media/${id}`)
  selected.value = null
  await loadMedia()
}

function copyUrl(url) {
  navigator.clipboard.writeText(url)
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Media Library</h1>
        <p class="text-sm text-gray-500 mt-1">{{ media.length }} files</p>
      </div>
      <div class="flex flex-col items-end gap-2">
        <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="upload" />
        <button @click="fileInput.click()" :disabled="uploading" class="bg-primary-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors disabled:opacity-60">
          {{ uploading ? 'Uploading…' : '+ Upload Image' }}
        </button>
        <p v-if="uploadError" class="text-xs text-red-500">{{ uploadError }}</p>
      </div>
    </div>

    <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
      <div v-for="item in media" :key="item.id" @click="selected = item"
        class="aspect-square rounded-xl overflow-hidden cursor-pointer border-2 transition-all hover:opacity-80"
        :class="selected?.id === item.id ? 'border-primary-500' : 'border-transparent'">
        <img :src="item.url" :alt="item.alt" class="w-full h-full object-cover" />
      </div>
    </div>

    <!-- Selected file detail -->
    <div v-if="selected" class="fixed right-6 top-24 w-72 bg-white rounded-2xl shadow-xl border border-gray-200 p-5 z-30">
      <button @click="selected=null" class="absolute top-3 right-3 text-gray-400 hover:text-gray-600">&times;</button>
      <img :src="selected.url" :alt="selected.alt" class="w-full aspect-square object-cover rounded-xl mb-3" />
      <p class="text-sm font-medium text-gray-900 truncate">{{ selected.originalName }}</p>
      <p class="text-xs text-gray-400 mt-0.5">{{ Math.round(selected.size / 1024) }} KB</p>
      <div class="mt-3 flex gap-2">
        <button @click="copyUrl(selected.url)" class="flex-1 text-xs bg-gray-100 text-gray-700 py-2 rounded-lg hover:bg-gray-200 transition-colors">Copy URL</button>
        <button @click="deleteMedia(selected.id)" class="text-xs bg-red-50 text-red-600 py-2 px-3 rounded-lg hover:bg-red-100 transition-colors">Delete</button>
      </div>
    </div>
  </div>
</template>
