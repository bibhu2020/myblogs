import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('../api', () => ({
  default: { get: vi.fn() },
}))

import api from '../api'
import { useStoryStore } from './story'

describe('useStoryStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initializes with empty state', () => {
    const store = useStoryStore()
    expect(store.stories).toEqual([])
    expect(store.recentStories).toEqual([])
    expect(store.loading).toBe(false)
  })

  describe('fetchStories', () => {
    it('populates stories and pagination, resetting loading afterward', async () => {
      api.get.mockResolvedValue({
        data: { stories: [{ id: 1 }], total: 1, page: 1, limit: 12, pages: 1 },
      })
      const store = useStoryStore()
      await store.fetchStories()
      expect(store.stories).toHaveLength(1)
      expect(store.pagination).toEqual({ total: 1, page: 1, limit: 12, pages: 1 })
      expect(store.loading).toBe(false)
    })

    it('resets loading to false even when the request fails', async () => {
      api.get.mockRejectedValue(new Error('network error'))
      const store = useStoryStore()
      await expect(store.fetchStories()).rejects.toThrow('network error')
      expect(store.loading).toBe(false)
    })

    it('merges custom params with the defaults', async () => {
      api.get.mockResolvedValue({ data: { stories: [], total: 0, page: 2, limit: 5, pages: 0 } })
      const store = useStoryStore()
      await store.fetchStories({ page: 2, limit: 5 })
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining('page=2'))
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining('limit=5'))
    })
  })

  describe('fetchRecentStories', () => {
    it('populates recentStories', async () => {
      api.get.mockResolvedValue({ data: [{ id: 1 }, { id: 2 }] })
      const store = useStoryStore()
      await store.fetchRecentStories()
      expect(store.recentStories).toHaveLength(2)
    })
  })
})
