import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(email, password) {
    const res = await api.post('/auth/login', { email, password })
    token.value = res.data.access_token
    user.value = res.data.user
    localStorage.setItem('token', token.value)
    localStorage.setItem('user', JSON.stringify(user.value))
    api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    return res.data
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    delete api.defaults.headers.common['Authorization']
  }

  function init() {
    if (token.value) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    }
  }

  return { token, user, isLoggedIn, isAdmin, login, logout, init }
})
