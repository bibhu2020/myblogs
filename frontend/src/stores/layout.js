import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useLayoutStore = defineStore('layout', () => {
  const KEY = 'meridian_ab_variant'
  let stored = localStorage.getItem(KEY)
  if (stored !== 'a' && stored !== 'b') {
    stored = Math.random() < 0.5 ? 'a' : 'b'
    localStorage.setItem(KEY, stored)
  }
  const variant = ref(stored)
  return { variant }
})
