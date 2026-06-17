<template>
  <button
    v-if="supported"
    @click="toggle"
    :title="subscribed ? 'Turn off notifications' : 'Turn on notifications'"
    :aria-label="subscribed ? 'Unsubscribe from push notifications' : 'Subscribe to push notifications'"
    :aria-pressed="subscribed"
    class="relative p-2 rounded-lg transition-colors flex-shrink-0"
    :class="layout.variant === 'b'
      ? (subscribed ? 'text-violet-400 bg-violet-950 hover:bg-violet-900' : 'text-slate-400 hover:text-violet-400 hover:bg-slate-900')
      : (subscribed ? 'text-primary-600 bg-primary-50 hover:bg-primary-100' : 'text-gray-500 hover:text-primary-600 hover:bg-gray-50')"
  >
    <!-- Bell icon — subscribed -->
    <svg v-if="subscribed" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5S10.5 3.17 10.5 4v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/>
    </svg>
    <!-- Bell-off icon — not subscribed -->
    <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
      <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
    </svg>

    <!-- Loading spinner overlay -->
    <span v-if="loading" class="absolute inset-0 flex items-center justify-center rounded-lg"
      :class="layout.variant === 'b' ? 'bg-slate-900/70' : 'bg-white/70'">
      <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
    </span>
  </button>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'
import { useLayoutStore } from '../stores/layout'

const layout = useLayoutStore()

const supported = ref(false)
const subscribed = ref(false)
const loading = ref(false)

const STORAGE_KEY = 'push_subscribed'

onMounted(async () => {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return
  supported.value = true
  subscribed.value = localStorage.getItem(STORAGE_KEY) === '1'
})

async function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)))
}

async function toggle() {
  if (loading.value) return
  loading.value = true
  try {
    if (subscribed.value) {
      await doUnsubscribe()
    } else {
      await doSubscribe()
    }
  } catch (err) {
    console.error('[push]', err)
  } finally {
    loading.value = false
  }
}

async function doSubscribe() {
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return

  const { data } = await api.get('/push/vapid-key')
  if (!data.publicKey) return

  const registration = await navigator.serviceWorker.ready
  const applicationServerKey = await urlBase64ToUint8Array(data.publicKey)

  const sub = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey,
  })

  await api.post('/push/subscribe', sub.toJSON())
  subscribed.value = true
  localStorage.setItem(STORAGE_KEY, '1')
}

async function doUnsubscribe() {
  const registration = await navigator.serviceWorker.ready
  const sub = await registration.pushManager.getSubscription()
  if (sub) {
    await api.delete('/push/unsubscribe', { data: { endpoint: sub.endpoint } })
    await sub.unsubscribe()
  }
  subscribed.value = false
  localStorage.removeItem(STORAGE_KEY)
}
</script>
