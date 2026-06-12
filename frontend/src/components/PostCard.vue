<script setup>
import { RouterLink } from 'vue-router'
import { format } from 'date-fns'

const props = defineProps({
  post: Object,
  featured: { type: Boolean, default: false }
})

function formatDate(d) {
  return format(new Date(d), 'MMM d, yyyy')
}
</script>

<template>
  <RouterLink :to="`/blog/${post.slug}`" class="group block">
    <article :class="featured ? 'flex flex-col' : 'flex flex-col'">
      <div class="relative overflow-hidden rounded-2xl bg-gray-100" :class="featured ? 'aspect-[16/9]' : 'aspect-[16/10]'">
        <img
          v-if="post.featuredImage"
          :src="post.featuredImage.startsWith('http') ? post.featuredImage : post.featuredImage"
          :alt="post.title"
          class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          loading="lazy"
        />
        <div v-else class="w-full h-full bg-gradient-to-br from-primary-100 to-purple-100 flex items-center justify-center">
          <span class="text-4xl">{{ post.category?.icon || '📝' }}</span>
        </div>
        <div v-if="post.category" class="absolute top-3 left-3">
          <span class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold text-white shadow-sm" :style="{ background: post.category.color || '#3B82F6' }">
            {{ post.category.icon }} {{ post.category.name }}
          </span>
        </div>
      </div>

      <div class="mt-4 flex-1 flex flex-col">
        <div class="flex items-center gap-2 text-xs text-gray-500 mb-2">
          <span>{{ formatDate(post.createdAt) }}</span>
          <span>·</span>
          <span>{{ post.readTime || 5 }} min read</span>
          <span v-if="post.views" class="ml-auto flex items-center gap-1">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
            {{ post.views }}
          </span>
        </div>

        <h3 class="font-bold text-gray-900 group-hover:text-primary-600 transition-colors line-clamp-2 mb-2" :class="featured ? 'text-xl' : 'text-lg'" style="font-family: 'Playfair Display', serif">
          {{ post.title }}
        </h3>

        <p v-if="post.excerpt" class="text-gray-500 text-sm leading-relaxed line-clamp-2 flex-1">
          {{ post.excerpt }}
        </p>

        <div class="flex items-center gap-2 mt-3">
          <div class="w-6 h-6 bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0">
            <span class="text-white text-xs font-bold">{{ (post.authorName || 'A').charAt(0) }}</span>
          </div>
          <span class="text-xs font-medium text-gray-700">{{ post.authorName }}</span>
        </div>
      </div>
    </article>
  </RouterLink>
</template>
