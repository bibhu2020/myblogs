<script setup>
import { ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import LogoMark from '../../components/LogoMark.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const sidebarOpen = ref(false)

function logout() {
  auth.logout()
  router.push('/admin/login')
}

const navItems = [
  { path: '/admin/dashboard', label: 'Dashboard', icon: '🏠' },
  { path: '/admin/posts', label: 'Posts', icon: '📝' },
  { path: '/admin/media', label: 'Media Library', icon: '🖼️' },
  { path: '/admin/categories', label: 'Categories', icon: '🏷️' },
  { path: '/admin/comments', label: 'Comments', icon: '💬' },
  { path: '/admin/users', label: 'Users', icon: '👥' },
  { path: '/admin/agent-runs', label: 'Agent Runs', icon: '🤖' },
  { path: '/admin/stories', label: 'Stories', icon: '📖' },
]
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex">
    <!-- Sidebar -->
    <aside class="hidden lg:flex w-64 bg-gray-900 flex-col fixed h-full z-40">
      <div class="p-6 border-b border-gray-800">
        <RouterLink to="/" class="flex items-center gap-2.5">
          <LogoMark :size="32" />
          <span class="text-white font-bold text-lg tracking-tight" style="font-family:'Playfair Display',serif">Meridian</span>
        </RouterLink>
        <p class="text-gray-500 text-xs mt-1">Admin Panel</p>
      </div>
      <nav class="flex-1 p-4 space-y-1">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors"
          :class="route.path === item.path ? 'bg-primary-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'"
        >
          <span>{{ item.icon }}</span> {{ item.label }}
        </RouterLink>
      </nav>
      <div class="p-4 border-t border-gray-800">
        <div class="flex items-center gap-3 px-4 py-3 mb-2">
          <div class="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center"><span class="text-white font-bold text-sm">{{ (auth.user?.name||'A').charAt(0) }}</span></div>
          <div class="flex-1 min-w-0">
            <div class="text-white text-sm font-medium truncate">{{ auth.user?.name }}</div>
            <div class="text-gray-500 text-xs capitalize">{{ auth.user?.role }}</div>
          </div>
        </div>
        <button @click="logout" class="w-full flex items-center gap-3 px-4 py-2.5 text-gray-400 hover:text-red-400 hover:bg-gray-800 rounded-xl text-sm font-medium transition-colors">
          <span>🚪</span> Sign Out
        </button>
        <RouterLink to="/" class="flex items-center gap-3 px-4 py-2.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-xl text-sm font-medium transition-colors mt-1">
          <span>🌐</span> View Site
        </RouterLink>
      </div>
    </aside>

    <!-- Mobile sidebar -->
    <div v-if="sidebarOpen" class="lg:hidden fixed inset-0 z-50 flex">
      <div class="fixed inset-0 bg-black/50" @click="sidebarOpen=false"></div>
      <aside class="relative w-64 bg-gray-900 flex flex-col h-full">
        <div class="p-6 border-b border-gray-800 flex items-center justify-between">
          <span class="text-white font-bold">Meridian Admin</span>
          <button @click="sidebarOpen=false" class="text-gray-400">&times;</button>
        </div>
        <nav class="flex-1 p-4 space-y-1">
          <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" @click="sidebarOpen=false" class="flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors" :class="route.path === item.path ? 'bg-primary-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'">
            <span>{{ item.icon }}</span> {{ item.label }}
          </RouterLink>
        </nav>
      </aside>
    </div>

    <!-- Main -->
    <div class="flex-1 lg:ml-64 flex flex-col">
      <header class="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 z-30">
        <button @click="sidebarOpen=true" class="lg:hidden p-2 rounded-md text-gray-500">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
        </button>
        <div class="flex items-center gap-3 ml-auto">
          <span class="text-sm text-gray-500">Welcome, <strong>{{ auth.user?.name }}</strong></span>
          <RouterLink to="/admin/posts/new" class="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors">+ New Post</RouterLink>
        </div>
      </header>
      <main class="flex-1 p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>
