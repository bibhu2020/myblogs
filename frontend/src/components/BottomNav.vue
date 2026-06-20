<script setup>
import { useRoute, RouterLink } from 'vue-router'
import { useLayoutStore } from '../stores/layout'

const route = useRoute()
const layout = useLayoutStore()

function isActive(to, exact = false) {
  return exact ? route.path === to : route.path === to || route.path.startsWith(to + '/')
}
</script>

<template>
  <!-- Mobile-only bottom navigation bar — hidden on sm+ (desktop has top nav) -->
  <nav
    class="sm:hidden fixed bottom-0 inset-x-0 z-40 h-16 flex"
    :class="layout.variant === 'b'
      ? 'bg-[#111d35] border-t border-[#2d3f5f] shadow-[0_-2px_12px_rgba(0,0,0,0.4)]'
      : 'bg-white border-t border-gray-200 shadow-[0_-2px_12px_rgba(0,0,0,0.07)]'"
    aria-label="Main navigation"
  >
    <!-- Home -->
    <RouterLink to="/"
      class="flex flex-col items-center justify-center flex-1 gap-0.5 min-w-0 transition-colors"
      :class="isActive('/', true)
        ? (layout.variant === 'b' ? 'text-violet-400' : 'text-primary-600')
        : (layout.variant === 'b' ? 'text-slate-500' : 'text-gray-400')"
      aria-label="Home"
    >
      <svg class="w-[22px] h-[22px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
      </svg>
      <span class="text-[10px] font-medium leading-none truncate w-full text-center px-0.5">Home</span>
    </RouterLink>

    <!-- Posts -->
    <RouterLink to="/blog"
      class="flex flex-col items-center justify-center flex-1 gap-0.5 min-w-0 transition-colors"
      :class="isActive('/blog')
        ? (layout.variant === 'b' ? 'text-violet-400' : 'text-primary-600')
        : (layout.variant === 'b' ? 'text-slate-500' : 'text-gray-400')"
      aria-label="Posts"
    >
      <svg class="w-[22px] h-[22px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414A1 1 0 0121 9.586V19a2 2 0 01-2 2z"/>
      </svg>
      <span class="text-[10px] font-medium leading-none truncate w-full text-center px-0.5">Posts</span>
    </RouterLink>

    <!-- News -->
    <RouterLink to="/news"
      class="flex flex-col items-center justify-center flex-1 gap-0.5 min-w-0 transition-colors"
      :class="isActive('/news')
        ? (layout.variant === 'b' ? 'text-violet-400' : 'text-primary-600')
        : (layout.variant === 'b' ? 'text-slate-500' : 'text-gray-400')"
      aria-label="News"
    >
      <svg class="w-[22px] h-[22px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"/>
      </svg>
      <span class="text-[10px] font-medium leading-none truncate w-full text-center px-0.5">News</span>
    </RouterLink>

    <!-- Story -->
    <RouterLink to="/story"
      class="flex flex-col items-center justify-center flex-1 gap-0.5 min-w-0 transition-colors"
      :class="isActive('/story')
        ? (layout.variant === 'b' ? 'text-violet-400' : 'text-primary-600')
        : (layout.variant === 'b' ? 'text-slate-500' : 'text-gray-400')"
      aria-label="Story"
    >
      <svg class="w-[22px] h-[22px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
      </svg>
      <span class="text-[10px] font-medium leading-none truncate w-full text-center px-0.5">Story</span>
    </RouterLink>

    <!-- Music -->
    <RouterLink to="/music"
      class="flex flex-col items-center justify-center flex-1 gap-0.5 min-w-0 transition-colors"
      :class="isActive('/music')
        ? (layout.variant === 'b' ? 'text-violet-400' : 'text-primary-600')
        : (layout.variant === 'b' ? 'text-slate-500' : 'text-gray-400')"
      aria-label="Music"
    >
      <svg class="w-[22px] h-[22px] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
      </svg>
      <span class="text-[10px] font-medium leading-none truncate w-full text-center px-0.5">Music</span>
    </RouterLink>
  </nav>
</template>
