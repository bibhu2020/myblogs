<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { useLayoutStore } from './stores/layout'
import PwaUpdatePrompt from './components/PwaUpdatePrompt.vue'
import BottomNav from './components/BottomNav.vue'

const auth = useAuthStore()
const layout = useLayoutStore()
const route = useRoute()
onMounted(() => auth.init())

const showBottomNav = computed(() => !route.path.startsWith('/admin'))
</script>

<template>
  <a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[9999] focus:px-4 focus:py-2 focus:bg-primary-600 focus:text-white focus:rounded-md focus:text-sm focus:font-medium">Skip to content</a>
  <div :data-layout="layout.variant" class="contents">
    <RouterView />
  </div>
  <BottomNav v-if="showBottomNav" />
  <PwaUpdatePrompt />
</template>
