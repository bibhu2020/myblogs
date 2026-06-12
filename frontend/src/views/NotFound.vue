<script setup>
import { RouterLink } from 'vue-router'
import Navbar from '../components/Navbar.vue'
</script>
<template>
  <div class="min-h-screen bg-white">
    <Navbar />
    <div class="max-w-2xl mx-auto px-4 py-32 text-center">
      <div class="text-8xl mb-6">404</div>
      <h1 class="text-3xl font-bold text-gray-900 mb-4" style="font-family:'Playfair Display',serif">Page Not Found</h1>
      <p class="text-gray-500 mb-8">The page you're looking for doesn't exist or has been moved.</p>
      <RouterLink to="/" class="bg-primary-600 text-white px-8 py-3 rounded-full font-medium hover:bg-primary-700 transition-colors">Go Home</RouterLink>
    </div>
  </div>
</template>
