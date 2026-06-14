import { defineStore } from 'pinia'
import api from '../api'

export const useStoryStore = defineStore('story', {
  state: () => ({
    stories: [],
    recentStories: [],
    pagination: { total: 0, page: 1, limit: 12, pages: 1 },
    loading: false,
  }),
  actions: {
    async fetchStories(params = {}) {
      this.loading = true
      try {
        const query = new URLSearchParams({ page: 1, limit: 12, ...params }).toString()
        const res = await api.get(`/stories?${query}`)
        this.stories = res.data.stories
        this.pagination = { total: res.data.total, page: res.data.page, limit: res.data.limit, pages: res.data.pages }
      } finally {
        this.loading = false
      }
    },
    async fetchRecentStories() {
      const res = await api.get('/stories/recent')
      this.recentStories = res.data
    },
  },
})
