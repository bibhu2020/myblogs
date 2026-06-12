<script setup>
import { RouterLink } from 'vue-router'
import Navbar from '../components/Navbar.vue'
import { useLayoutStore } from '../stores/layout'
const layout = useLayoutStore()
</script>
<template>
  <div :class="layout.variant === 'b' ? 'min-h-screen bg-[#0f172a]' : 'min-h-screen bg-white'">
    <Navbar />
    <div class="max-w-2xl mx-auto px-4 py-32 text-center">
      <div class="text-8xl mb-6" :class="layout.variant === 'b' ? 'text-slate-300' : ''">404</div>
      <h1 class="text-3xl font-bold mb-4" :class="layout.variant === 'b' ? 'text-slate-100' : 'text-gray-900'" style="font-family:'Playfair Display',serif">Page Not Found</h1>
      <p class="mb-8" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-gray-500'">The page you're looking for doesn't exist or has been moved.</p>
      <RouterLink to="/" class="px-8 py-3 rounded-full font-medium transition-colors" :class="layout.variant === 'b' ? 'bg-violet-600 text-white hover:bg-violet-700' : 'bg-primary-600 text-white hover:bg-primary-700'">Go Home</RouterLink>
    </div>
  </div>
</template>
