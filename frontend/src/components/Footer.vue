<script setup>
import { RouterLink } from 'vue-router'
import { useBlogStore } from '../stores/blog'
import { useLayoutStore } from '../stores/layout'
import LogoMark from './LogoMark.vue'
const blog = useBlogStore()
const layout = useLayoutStore()
</script>

<template>
  <footer :class="layout.variant === 'b' ? 'bg-[#090f1d] text-slate-400 mt-24' : 'bg-primary-900 text-primary-200 mt-24'">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-12">
        <div class="md:col-span-2">
          <div class="flex items-center gap-2.5 mb-4">
            <LogoMark :size="36" />
            <span class="text-2xl font-bold text-white tracking-tight" style="font-family: 'Playfair Display', serif">Meridian</span>
          </div>
          <p class="leading-relaxed text-sm max-w-xs" :class="layout.variant === 'b' ? 'text-slate-400' : 'text-primary-200'">Where ideas converge. Thoughtful writing on technology, science, history, and the ideas that shape our world.</p>
          <div class="flex gap-4 mt-6">
            <a href="#" class="w-9 h-9 rounded-full flex items-center justify-center hover:bg-violet-600 transition-colors text-sm" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-800'" aria-label="Follow Meridian on Twitter (𝕏)">𝕏</a>
            <a href="#" class="w-9 h-9 rounded-full flex items-center justify-center hover:bg-violet-600 transition-colors text-sm" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-800'" aria-label="Follow Meridian on LinkedIn">in</a>
            <a href="#" class="w-9 h-9 rounded-full flex items-center justify-center hover:bg-violet-600 transition-colors text-sm" :class="layout.variant === 'b' ? 'bg-slate-800' : 'bg-gray-800'" aria-label="Follow Meridian on Instagram">📷</a>
          </div>
        </div>

        <div>
          <h3 class="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Topics</h3>
          <ul class="space-y-2">
            <li v-for="cat in blog.categories" :key="cat.id">
              <RouterLink :to="`/category/${cat.slug}`" class="text-sm transition-colors flex items-center gap-2" :class="layout.variant === 'b' ? 'text-slate-400 hover:text-violet-400' : 'text-primary-200 hover:text-white'">
                <span>{{ cat.icon }}</span> {{ cat.name }}
              </RouterLink>
            </li>
            <li><RouterLink to="/blog" class="text-sm transition-colors" :class="layout.variant === 'b' ? 'text-slate-400 hover:text-violet-400' : 'text-primary-200 hover:text-white'">All Posts</RouterLink></li>
          </ul>
        </div>

        <div>
          <h3 class="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Quick Links</h3>
          <ul class="space-y-2">
            <li><RouterLink to="/" class="text-sm transition-colors" :class="layout.variant === 'b' ? 'text-slate-400 hover:text-violet-400' : 'text-primary-200 hover:text-white'">Home</RouterLink></li>
            <li><RouterLink to="/search" class="text-sm transition-colors" :class="layout.variant === 'b' ? 'text-slate-400 hover:text-violet-400' : 'text-primary-200 hover:text-white'">Search</RouterLink></li>
            <li><RouterLink to="/about" class="text-sm transition-colors" :class="layout.variant === 'b' ? 'text-slate-400 hover:text-violet-400' : 'text-primary-200 hover:text-white'">About</RouterLink></li>
            <li><RouterLink to="/admin" class="text-sm transition-colors" :class="layout.variant === 'b' ? 'text-slate-400 hover:text-violet-400' : 'text-primary-200 hover:text-white'">Admin Panel</RouterLink></li>
          </ul>
        </div>
      </div>
      <div class="mt-12 pt-8 text-center text-sm" :class="layout.variant === 'b' ? 'border-t border-slate-800' : 'border-t border-primary-800'">
        <!-- HOLIDAY-FOOTER-START -->
<p class="mb-2" :class="layout.variant === 'b' ? 'text-slate-500' : 'text-primary-300'">Celebrate the joy of sports and unity! 🎊</p>
<!-- HOLIDAY-FOOTER-END -->
        <p>&copy; {{ new Date().getFullYear() }} Meridian. Built with Vue.js &amp; NestJS.</p>
      </div>
    </div>
  </footer>
</template>
