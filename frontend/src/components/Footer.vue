<script setup>
import { RouterLink } from 'vue-router'
import { useBlogStore } from '../stores/blog'
import LogoMark from './LogoMark.vue'
const blog = useBlogStore()
</script>

<template>
  <footer class="bg-gray-900 text-gray-400 mt-24">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-12">
        <div class="md:col-span-2">
          <div class="flex items-center gap-2.5 mb-4">
            <LogoMark :size="36" />
            <span class="text-2xl font-bold text-white tracking-tight" style="font-family: 'Playfair Display', serif">Meridian</span>
          </div>
          <p class="text-gray-400 leading-relaxed text-sm max-w-xs">Where ideas converge. Thoughtful writing on technology, science, history, and the ideas that shape our world.</p>
          <div class="flex gap-4 mt-6">
            <a href="#" class="w-9 h-9 bg-gray-800 rounded-full flex items-center justify-center hover:bg-violet-600 transition-colors text-sm">𝕏</a>
            <a href="#" class="w-9 h-9 bg-gray-800 rounded-full flex items-center justify-center hover:bg-violet-600 transition-colors text-sm">in</a>
            <a href="#" class="w-9 h-9 bg-gray-800 rounded-full flex items-center justify-center hover:bg-violet-600 transition-colors text-sm">📷</a>
          </div>
        </div>

        <div>
          <h4 class="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Topics</h4>
          <ul class="space-y-2">
            <li v-for="cat in blog.categories" :key="cat.id">
              <RouterLink :to="`/category/${cat.slug}`" class="text-gray-400 hover:text-white text-sm transition-colors flex items-center gap-2">
                <span>{{ cat.icon }}</span> {{ cat.name }}
              </RouterLink>
            </li>
            <li><RouterLink to="/blog" class="text-gray-400 hover:text-white text-sm transition-colors">All Posts</RouterLink></li>
          </ul>
        </div>

        <div>
          <h4 class="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Quick Links</h4>
          <ul class="space-y-2">
            <li><RouterLink to="/" class="text-gray-400 hover:text-white text-sm transition-colors">Home</RouterLink></li>
            <li><RouterLink to="/search" class="text-gray-400 hover:text-white text-sm transition-colors">Search</RouterLink></li>
            <li><RouterLink to="/admin" class="text-gray-400 hover:text-white text-sm transition-colors">Admin Panel</RouterLink></li>
          </ul>
        </div>
      </div>
      <div class="border-t border-gray-800 mt-12 pt-8 text-center text-sm">
        <!-- HOLIDAY-FOOTER-START -->
        <p class="text-primary-400 mb-2">Wishing our readers a meaningful Juneteenth ✊</p>
        <!-- HOLIDAY-FOOTER-END -->
        <p>&copy; {{ new Date().getFullYear() }} Meridian. Built with Vue.js &amp; NestJS.</p>
      </div>
    </div>
  </footer>
</template>
