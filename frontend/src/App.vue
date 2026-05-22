<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'
const auth = useAuthStore()
onMounted(() => auth.init())
</script>
<template>
  <RouterView />
</template>
