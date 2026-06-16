import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useBlogStore } from './blog'

vi.mock('../api', () => ({
  default: { get: vi.fn() },
}))

import api from '../api'

describe('useBlogStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initializes with empty state', () => {
    const store = useBlogStore()
    expect(store.posts).toEqual([])
    expect(store.categories).toEqual([])
    expect(store.tags).toEqual([])
    expect(store.featured).toEqual([])
    expect(store.recent).toEqual([])
    expect(store.currentPost).toBeNull()
    expect(store.loading).toBe(false)
  })

  describe('fetchPosts', () => {
    it('populates posts and pagination', async () => {
      api.get.mockResolvedValue({
        data: { posts: [{ id: 1, title: 'Hello' }], total: 1, page: 1, pages: 1 },
      })
      const store = useBlogStore()
      await store.fetchPosts()
      expect(store.posts).toHaveLength(1)
      expect(store.posts[0].title).toBe('Hello')
      expect(store.pagination).toEqual({ total: 1, page: 1, pages: 1 })
    })

    it('sets loading to false after fetch', async () => {
      api.get.mockResolvedValue({ data: { posts: [], total: 0, page: 1, pages: 0 } })
      const store = useBlogStore()
      await store.fetchPosts()
      expect(store.loading).toBe(false)
    })

    it('passes query params to the API', async () => {
      api.get.mockResolvedValue({ data: { posts: [], total: 0, page: 1, pages: 0 } })
      const store = useBlogStore()
      await store.fetchPosts({ category: 'tech', page: 2 })
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining('category=tech'))
      expect(api.get).toHaveBeenCalledWith(expect.stringContaining('page=2'))
    })
  })

  describe('fetchFeatured', () => {
    it('populates featured posts', async () => {
      api.get.mockResolvedValue({ data: [{ id: 1 }, { id: 2 }] })
      const store = useBlogStore()
      await store.fetchFeatured()
      expect(store.featured).toHaveLength(2)
    })
  })

  describe('fetchRecent', () => {
    it('populates recent posts', async () => {
      api.get.mockResolvedValue({ data: [{ id: 3 }, { id: 4 }, { id: 5 }] })
      const store = useBlogStore()
      await store.fetchRecent()
      expect(store.recent).toHaveLength(3)
    })
  })

  describe('fetchPost', () => {
    it('sets currentPost', async () => {
      api.get.mockResolvedValue({ data: { id: 1, slug: 'hello-world', title: 'Hello World' } })
      const store = useBlogStore()
      const result = await store.fetchPost('hello-world')
      expect(store.currentPost.slug).toBe('hello-world')
      expect(result.title).toBe('Hello World')
      expect(store.loading).toBe(false)
    })

    it('calls the correct endpoint', async () => {
      api.get.mockResolvedValue({ data: { id: 1, slug: 'my-post' } })
      const store = useBlogStore()
      await store.fetchPost('my-post')
      expect(api.get).toHaveBeenCalledWith('/posts/my-post')
    })
  })

  describe('fetchCategories', () => {
    it('populates categories', async () => {
      api.get.mockResolvedValue({ data: [{ id: 1, name: 'Tech' }, { id: 2, name: 'Science' }] })
      const store = useBlogStore()
      await store.fetchCategories()
      expect(store.categories).toHaveLength(2)
      expect(store.categories[0].name).toBe('Tech')
    })
  })

  describe('fetchTags', () => {
    it('populates tags', async () => {
      api.get.mockResolvedValue({ data: [{ id: 1, name: 'JavaScript' }] })
      const store = useBlogStore()
      await store.fetchTags()
      expect(store.tags).toHaveLength(1)
      expect(store.tags[0].name).toBe('JavaScript')
    })
  })
})
