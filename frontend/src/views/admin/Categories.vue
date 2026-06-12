<script setup>
import { onMounted, ref } from 'vue'
import api from '../../api'

const categories = ref([])
const form = ref({ name: '', description: '', color: '#3B82F6', icon: '📁' })
const editing = ref(null)
const showForm = ref(false)

onMounted(load)
async function load() {
  const res = await api.get('/categories')
  categories.value = res.data
}

async function save() {
  if (editing.value) {
    await api.put(`/categories/${editing.value}`, form.value)
  } else {
    await api.post('/categories', form.value)
  }
  form.value = { name: '', description: '', color: '#3B82F6', icon: '📁' }
  editing.value = null
  showForm.value = false
  await load()
}

function edit(cat) {
  form.value = { name: cat.name, description: cat.description || '', color: cat.color || '#3B82F6', icon: cat.icon || '📁' }
  editing.value = cat.id
  showForm.value = true
}

async function remove(id) {
  if (!confirm('Delete category?')) return
  await api.delete(`/categories/${id}`)
  await load()
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Categories</h1>
      <button @click="showForm=!showForm; editing=null; form={name:'',description:'',color:'#3B82F6',icon:'📁'}" class="bg-primary-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors">+ New Category</button>
    </div>

    <div v-if="showForm" class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-6">
      <h3 class="font-semibold text-gray-900 mb-4">{{ editing ? 'Edit Category' : 'New Category' }}</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <input v-model="form.name" type="text" placeholder="Category Name" required class="px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400" />
        <input v-model="form.icon" type="text" placeholder="Icon (emoji)" class="px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400" />
        <input v-model="form.description" type="text" placeholder="Description" class="px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400" />
        <div class="flex items-center gap-3">
          <label class="text-sm text-gray-600">Color:</label>
          <input v-model="form.color" type="color" class="w-10 h-10 rounded-lg border border-gray-200 cursor-pointer" />
          <span class="text-sm text-gray-500">{{ form.color }}</span>
        </div>
      </div>
      <div class="flex gap-3 mt-4">
        <button @click="save" class="bg-primary-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors">Save</button>
        <button @click="showForm=false" class="px-5 py-2.5 border border-gray-200 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors">Cancel</button>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="cat in categories" :key="cat.id" class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center text-2xl" :style="{ background: cat.color + '20' }">{{ cat.icon }}</div>
            <div>
              <div class="font-semibold text-gray-900">{{ cat.name }}</div>
              <div class="text-xs text-gray-400">{{ cat.slug }}</div>
            </div>
          </div>
          <div class="w-3 h-3 rounded-full" :style="{ background: cat.color }"></div>
        </div>
        <p v-if="cat.description" class="text-sm text-gray-500 mb-4">{{ cat.description }}</p>
        <div class="flex gap-2">
          <button @click="edit(cat)" class="text-xs text-primary-600 hover:underline">Edit</button>
          <button @click="remove(cat.id)" class="text-xs text-red-500 hover:underline">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>
