<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import LogoMark from '../../components/LogoMark.vue'

const auth = useAuthStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    router.push('/admin/dashboard')
  } catch (e) {
    error.value = e.response?.data?.message || 'Invalid credentials'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-[#0f0c29] via-[#1e1b4b] to-[#302b63] flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="flex justify-center mb-4">
          <LogoMark :size="56" />
        </div>
        <h1 class="text-2xl font-bold text-white tracking-tight" style="font-family:'Playfair Display',serif">Meridian Admin</h1>
        <p class="text-violet-300 text-sm mt-1">Sign in to manage your content</p>
      </div>

      <div class="bg-white rounded-3xl p-8 shadow-2xl">
        <form @submit.prevent="handleLogin" class="space-y-5">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Email</label>
            <input v-model="email" type="email" required
              class="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100 transition-all"
              placeholder="admin@myblogs.com" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1.5">Password</label>
            <input v-model="password" type="password" required
              class="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100 transition-all" />
          </div>
          <div v-if="error" class="bg-red-50 text-red-600 px-4 py-3 rounded-xl text-sm">{{ error }}</div>
          <button type="submit" :disabled="loading"
            class="w-full bg-violet-600 hover:bg-violet-700 text-white font-semibold py-3 rounded-xl transition-colors disabled:opacity-60">
            {{ loading ? 'Signing in…' : 'Sign In' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
