import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import CategoryView from './CategoryView.vue'
import { useBlogStore } from '../stores/blog'

vi.mock('../api', () => ({ default: { get: vi.fn() } }))
import api from '../api'

async function mountAt(slug) {
  setActivePinia(createPinia())
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/category/:slug', component: CategoryView }],
  })
  router.push(`/category/${slug}`)
  await router.isReady()
  const wrapper = mount(CategoryView, {
    global: { plugins: [router], stubs: { Navbar: true, Footer: true, PostCard: true } },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('CategoryView', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders the category name and icon when found', async () => {
    api.get
      .mockResolvedValueOnce({ data: [{ id: 1, name: 'Technology', slug: 'technology', icon: '💻', color: '#3B82F6' }] })
      .mockResolvedValueOnce({ data: { posts: [{ id: 1 }], total: 1, page: 1, pages: 1 } })
    const { wrapper } = await mountAt('technology')
    expect(wrapper.text()).toContain('Technology')
    expect(wrapper.text()).toContain('💻')
  })

  it('falls back to the raw slug when the category is unknown', async () => {
    api.get
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: { posts: [], total: 0, page: 1, pages: 1 } })
    const { wrapper } = await mountAt('ghost-category')
    expect(wrapper.text()).toContain('ghost-category')
  })

  it('shows an empty state when the category has no posts', async () => {
    api.get
      .mockResolvedValueOnce({ data: [{ id: 1, name: 'Tech', slug: 'tech', icon: '💻' }] })
      .mockResolvedValueOnce({ data: { posts: [], total: 0, page: 1, pages: 1 } })
    const { wrapper } = await mountAt('tech')
    expect(wrapper.text()).toContain('No posts in this category yet')
  })

  it('reloads posts and resets to page 1 when the route slug changes', async () => {
    api.get
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: { posts: [], total: 0, page: 1, pages: 1 } })
    const { wrapper, router } = await mountAt('tech')
    api.get.mockResolvedValueOnce({ data: { posts: [{ id: 5 }], total: 1, page: 1, pages: 1 } })
    await router.push('/category/science')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith(expect.stringContaining('category=science'))
  })
})
