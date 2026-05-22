<script setup>
import { onMounted, ref } from 'vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const users = ref([])
const showForm = ref(false)
const form = ref({ name: '', email: '', password: '', role: 'guest', bio: '' })
const message = ref('')

onMounted(load)
async function load() {
  const res = await api.get('/users')
  users.value = res.data
}

async function save() {
  try {
    await api.post('/users', form.value)
    form.value = { name: '', email: '', password: '', role: 'guest', bio: '' }
    showForm.value = false
    message.value = 'User created successfully!'
    await load()
  } catch (e) {
    message.value = e.response?.data?.message || 'Error creating user'
  }
}

async function toggleActive(user) {
  await api.put(`/users/${user.id}`, { isActive: !user.isActive })
  user.isActive = !user.isActive
}

async function remove(id) {
  if (!confirm('Delete user?')) return
  await api.delete(`/users/${id}`)
  await load()
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900" style="font-family:'Playfair Display',serif">Users</h1>
      <button @click="showForm=!showForm" class="bg-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-blue-700 transition-colors">+ Create Guest User</button>
    </div>

    <div v-if="message" class="mb-4 px-4 py-3 rounded-xl text-sm" :class="message.includes('Error') || message.includes('error') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'">{{ message }}</div>

    <div v-if="showForm" class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-6">
      <h3 class="font-semibold text-gray-900 mb-4">Create New User</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <input v-model="form.name" type="text" placeholder="Full Name *" required class="px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-400" />
        <input v-model="form.email" type="email" placeholder="Email *" required class="px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-400" />
        <input v-model="form.password" type="password" placeholder="Password *" required class="px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-400" />
        <select v-model="form.role" class="px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-400 bg-white">
          <option value="guest">Guest Author</option>
          <option value="admin">Admin</option>
        </select>
        <textarea v-model="form.bio" rows="2" placeholder="Bio (optional)" class="sm:col-span-2 px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-400 resize-none"></textarea>
      </div>
      <div class="flex gap-3 mt-4">
        <button @click="save" class="bg-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-blue-700 transition-colors">Create User</button>
        <button @click="showForm=false" class="px-5 py-2.5 border border-gray-200 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors">Cancel</button>
      </div>
    </div>

    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <table class="w-full">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">User</th>
            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden sm:table-cell">Role</th>
            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Status</th>
            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="user in users" :key="user.id" class="hover:bg-gray-50">
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <div class="w-9 h-9 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <span class="text-blue-600 font-bold text-sm">{{ user.name.charAt(0) }}</span>
                </div>
                <div>
                  <div class="font-medium text-gray-900 text-sm">{{ user.name }}</div>
                  <div class="text-xs text-gray-400">{{ user.email }}</div>
                </div>
              </div>
            </td>
            <td class="px-6 py-4 hidden sm:table-cell">
              <span :class="user.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'" class="px-2.5 py-1 rounded-full text-xs font-semibold capitalize">{{ user.role }}</span>
            </td>
            <td class="px-6 py-4 hidden md:table-cell">
              <button @click="toggleActive(user)" :class="user.isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'" class="px-2.5 py-1 rounded-full text-xs font-semibold hover:opacity-80 transition-opacity">
                {{ user.isActive ? 'Active' : 'Inactive' }}
              </button>
            </td>
            <td class="px-6 py-4">
              <button v-if="user.id !== auth.user?.id" @click="remove(user.id)" class="text-xs text-red-500 hover:text-red-700">Delete</button>
              <span v-else class="text-xs text-gray-400">You</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
