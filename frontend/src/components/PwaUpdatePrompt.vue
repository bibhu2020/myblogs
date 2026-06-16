<template>
  <Transition name="slide-up">
    <div
      v-if="needRefresh"
      class="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl border border-white/10 bg-indigo-950/95 backdrop-blur text-white text-sm"
    >
      <span>A new version is available.</span>
      <button
        @click="updateSW()"
        class="px-3 py-1 rounded-lg bg-violet-500 hover:bg-violet-400 font-medium transition-colors"
      >
        Update
      </button>
      <button @click="close()" class="text-white/50 hover:text-white transition-colors">
        ✕
      </button>
    </div>
  </Transition>
</template>

<script setup>
import { useRegisterSW } from 'virtual:pwa-register/vue'

const { needRefresh, updateServiceWorker } = useRegisterSW()

function updateSW() {
  updateServiceWorker(true)
}

function close() {
  needRefresh.value = false
}
</script>

<style scoped>
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateX(-50%) translateY(100%);
  opacity: 0;
}
</style>
