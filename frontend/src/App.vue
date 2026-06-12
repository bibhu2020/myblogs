<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'
import { useLayoutStore } from './stores/layout'

const auth = useAuthStore()
const layout = useLayoutStore()
onMounted(() => auth.init())
</script>

<template>
  <div :data-layout="layout.variant" class="contents">
    <RouterView />
  </div>
</template>
