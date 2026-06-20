<script setup>
import { ref } from 'vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()

const pwForm = ref({ currentPassword: '', newPassword: '', confirm: '' })
const pwStatus = ref('')   // '' | 'success' | 'error'
const pwMessage = ref('')
const pwLoading = ref(false)

const nameForm = ref({ name: auth.user?.name || '' })
const nameStatus = ref('')
const nameMessage = ref('')
const nameLoading = ref(false)

async function changePassword() {
  pwStatus.value = ''
  if (!pwForm.value.currentPassword || !pwForm.value.newPassword) {
    pwStatus.value = 'error'; pwMessage.value = 'All fields are required.'; return
  }
  if (pwForm.value.newPassword !== pwForm.value.confirm) {
    pwStatus.value = 'error'; pwMessage.value = 'New passwords do not match.'; return
  }
  if (pwForm.value.newPassword.length < 8) {
    pwStatus.value = 'error'; pwMessage.value = 'New password must be at least 8 characters.'; return
  }
  pwLoading.value = true
  try {
    // Verify current password by attempting login
    await api.post('/auth/login', { email: auth.user?.email, password: pwForm.value.currentPassword })
    // Current password is correct — update to new password
    await api.put(`/users/${auth.user?.id}`, { password: pwForm.value.newPassword })
    pwStatus.value = 'success'
    pwMessage.value = 'Password changed successfully.'
    pwForm.value = { currentPassword: '', newPassword: '', confirm: '' }
  } catch (e) {
    pwStatus.value = 'error'
    pwMessage.value = e.response?.status === 401
      ? 'Current password is incorrect.'
      : (e.response?.data?.message || 'Failed to change password.')
  } finally {
    pwLoading.value = false
  }
}

async function updateName() {
  nameStatus.value = ''
  if (!nameForm.value.name.trim()) {
    nameStatus.value = 'error'; nameMessage.value = 'Name cannot be empty.'; return
  }
  nameLoading.value = true
  try {
    const res = await api.put(`/users/${auth.user?.id}`, { name: nameForm.value.name.trim() })
    auth.user.name = res.data.name
    localStorage.setItem('user', JSON.stringify(auth.user))
    nameStatus.value = 'success'
    nameMessage.value = 'Name updated.'
  } catch (e) {
    nameStatus.value = 'error'
    nameMessage.value = e.response?.data?.message || 'Failed to update name.'
  } finally {
    nameLoading.value = false
  }
}
</script>

<template>
  <div class="max-w-lg">
    <h1 class="text-2xl font-bold text-gray-900 mb-6" style="font-family:'Playfair Display',serif">My Profile</h1>

    <!-- Account info -->
    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-6">
      <div class="flex items-center gap-4 mb-6">
        <div class="w-14 h-14 bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0">
          <span class="text-white font-bold text-xl">{{ (auth.user?.name || 'A').charAt(0) }}</span>
        </div>
        <div>
          <div class="font-semibold text-gray-900">{{ auth.user?.name }}</div>
          <div class="text-sm text-gray-500">{{ auth.user?.email }}</div>
          <span class="inline-block mt-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-700 capitalize">{{ auth.user?.role }}</span>
        </div>
      </div>

      <!-- Update display name -->
      <h2 class="text-sm font-semibold text-gray-700 mb-3">Display Name</h2>
      <div class="flex gap-3">
        <input
          v-model="nameForm.name" type="text" placeholder="Your name"
          class="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400"
        />
        <button
          @click="updateName" :disabled="nameLoading"
          class="px-5 py-2.5 bg-primary-600 text-white rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors disabled:opacity-50"
        >{{ nameLoading ? 'Saving…' : 'Save' }}</button>
      </div>
      <p v-if="nameMessage" class="mt-2 text-sm" :class="nameStatus === 'success' ? 'text-green-600' : 'text-red-600'">{{ nameMessage }}</p>
    </div>

    <!-- Change password -->
    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
      <h2 class="text-sm font-semibold text-gray-700 mb-4">Change Password</h2>
      <div class="space-y-3">
        <div>
          <label class="block text-xs text-gray-500 mb-1">Current password</label>
          <input
            v-model="pwForm.currentPassword" type="password" placeholder="Enter current password"
            class="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400"
            @keyup.enter="changePassword"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">New password <span class="text-gray-400">(min 8 characters)</span></label>
          <input
            v-model="pwForm.newPassword" type="password" placeholder="Enter new password"
            class="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400"
            @keyup.enter="changePassword"
          />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Confirm new password</label>
          <input
            v-model="pwForm.confirm" type="password" placeholder="Re-enter new password"
            class="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-primary-400"
            @keyup.enter="changePassword"
          />
        </div>
      </div>

      <div v-if="pwMessage" class="mt-3 px-4 py-3 rounded-xl text-sm" :class="pwStatus === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'">
        {{ pwMessage }}
      </div>

      <button
        @click="changePassword" :disabled="pwLoading"
        class="mt-4 w-full py-2.5 bg-primary-600 text-white rounded-xl text-sm font-semibold hover:bg-primary-700 transition-colors disabled:opacity-50"
      >{{ pwLoading ? 'Changing…' : 'Change Password' }}</button>
    </div>
  </div>
</template>
